"""DATUM gateway data collection via HTTP API and journalctl."""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DatumJob:
    """Active DATUM stratum job / block template snapshot."""

    available: bool = False
    job_id: str = "—"
    height: str = "—"
    coinbase_value_btc: str = "—"
    prev_block_hash: str = "—"
    target: str = "—"
    witness_commitment: str = "—"
    difficulty: str = "—"
    version: str = "—"
    bits: str = "—"
    time_info: str = "—"
    limits: str = "—"
    size: str = "—"
    weight: str = "—"
    sigops: str = "—"
    tx_count: str = "—"
    coinbase_outputs: int = 0


@dataclass
class DatumStatus:
    available: bool = False
    gateway_state: str = "Unavailable"
    workers: int = 0
    worker_names: list[str] = field(default_factory=list)
    hashrate: str = "—"
    shares_accepted: str = "—"
    shares_rejected: str = "—"
    pool_host: str = "—"
    miner_tag: str = "—"
    job_height: str = "—"
    uptime: str = "—"
    last_events: list[str] = field(default_factory=list)
    setup_hint: str = ""
    source: str = ""


SETUP_HINT = """DATUM not detected. To enable:
  1. Install datum_gateway (OCEAN-xyz/datum_gateway)
  2. sudo systemctl enable --now datum
  3. In bitcoin.conf: blocknotify=killall -USR1 datum_gateway
  4. API on :7152, miners on stratum :23334
  5. Set DATUM_API_URL=http://127.0.0.1:7152 if using another port"""


def _find_config() -> dict:
    candidates = [
        os.environ.get("DATUM_CONFIG"),
        "/etc/datum/datum_gateway_config.json",
        str(Path.home() / "datum_gateway_config.json"),
        str(Path.home() / "datum_gateway" / "doc" / "example_datum_gateway_config.json"),
    ]
    for path in candidates:
        if path and Path(path).is_file():
            try:
                return json.loads(Path(path).read_text())
            except (json.JSONDecodeError, OSError):
                continue
    return {}


def _api_base() -> str:
    return os.environ.get("DATUM_API_URL", "http://127.0.0.1:7152").rstrip("/")


def _fetch_html(path: str = "/") -> str | None:
    url = f"{_api_base()}{path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "oraculovision/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def _extract_table_value(html: str, label: str) -> str | None:
    pattern = rf'<td class="label">{re.escape(label)}:</td>\s*<td[^>]*>(.*?)</td>'
    match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
    if not match:
        return None
    value = re.sub(r"<[^>]+>", "", match.group(1)).strip()
    return value or None


_JOB_LABELS = {
    "job_id": "Job ID",
    "height": "Block Height",
    "coinbase_value_btc": "Block Value",
    "prev_block_hash": "Previous Block",
    "target": "Block Target",
    "witness_commitment": "Witness Commitment",
    "difficulty": "Block Difficulty",
    "version": "Version",
    "bits": "Bits",
    "time_info": "Time",
    "limits": "Limits",
    "size": "Size",
    "weight": "Weight",
    "sigops": "Sigops",
    "tx_count": "Txn Count",
}


def _parse_homepage(html: str) -> dict[str, str]:
    labels = {
        "shares_accepted": "Shares Accepted",
        "shares_rejected": "Shares Rejected",
        "gateway_state": "Status",
        "pool_host": "Pool Host",
        "miner_tag": "Secondary/Miner Tag",
        "hashrate": "Estimated Hashrate",
        "workers": "Total Connections",
        "subscriptions": "Total Work Subscriptions",
        "job_height": "Block Height",
        "uptime": "Process uptime",
    }
    result: dict[str, str] = {}
    for key, label in labels.items():
        val = _extract_table_value(html, label)
        if val:
            result[key] = val
    return result


def parse_datum_job(html: str) -> DatumJob:
    """Parse the Current Stratum Job table from DATUM homepage HTML."""
    job = DatumJob()
    if not html:
        return job

    parsed: dict[str, str] = {}
    for key, label in _JOB_LABELS.items():
        val = _extract_table_value(html, label)
        if val:
            parsed[key] = val

    if not parsed:
        return job

    job.available = True
    for key, value in parsed.items():
        setattr(job, key, value)
    return job


def _count_coinbaser_outputs(html: str) -> int:
    if not html:
        return 0
    rows = re.findall(
        r"<TR><TD>[\d.]+\s*BTC</TD><TD>[^<]+</TD></TR>",
        html,
        re.IGNORECASE,
    )
    return len(rows)


def fetch_datum_job() -> DatumJob:
    """Fetch active DATUM job details from the gateway HTTP API."""
    html = _fetch_html("/")
    job = parse_datum_job(html or "")
    if not job.available:
        return job

    coinbaser_html = _fetch_html("/coinbaser")
    job.coinbase_outputs = _count_coinbaser_outputs(coinbaser_html or "")
    return job


def _count_clients(html: str) -> tuple[int, list[str]]:
    names: list[str] = []
    # Client rows often have worker names in table cells
    for match in re.finditer(r"<td[^>]*>([^<]{2,64})</td>", html):
        text = match.group(1).strip()
        if text and not text.startswith("Stratum") and text not in (
            "User", "Difficulty", "Hashrate", "Shares", "Connected",
        ):
            if re.match(r"^[\w.\-/]+$", text):
                names.append(text)
    unique = list(dict.fromkeys(names))[:20]
    return len(unique), unique


def _fetch_journal() -> list[str]:
    units = ["datum", "datum_gateway", "datum-gateway"]
    for unit in units:
        try:
            result = subprocess.run(
                ["journalctl", "-u", unit, "-n", "200", "--no-pager", "-o", "cat"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().splitlines()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return []


def _extract_events(lines: list[str]) -> list[str]:
    keywords = re.compile(
        r"worker|hashrate|share|stratum|accepted|rejected|block|connected|disconnect",
        re.I,
    )
    events = [ln.strip() for ln in lines if keywords.search(ln)]
    return events[-8:]


def fetch_datum_status() -> DatumStatus:
    status = DatumStatus(setup_hint=SETUP_HINT)
    _find_config()  # reserved for future port override

    html = _fetch_html("/")
    if html:
        parsed = _parse_homepage(html)
        status.available = True
        status.source = "http"
        status.gateway_state = parsed.get("gateway_state", "Running")
        status.shares_accepted = parsed.get("shares_accepted", "—")
        status.shares_rejected = parsed.get("shares_rejected", "—")
        status.pool_host = parsed.get("pool_host", "—")
        status.miner_tag = parsed.get("miner_tag", "—").strip('"')
        status.hashrate = parsed.get("hashrate", "—")
        status.job_height = parsed.get("job_height", "—")
        status.uptime = parsed.get("uptime", "—")
        try:
            status.workers = int(re.search(r"\d+", parsed.get("workers", "0") or "0").group())
        except (AttributeError, ValueError):
            status.workers = 0

        clients_html = _fetch_html("/clients")
        if clients_html:
            count, names = _count_clients(clients_html)
            if count:
                status.workers = max(status.workers, count)
                status.worker_names = names

    lines = _fetch_journal()
    if lines:
        events = _extract_events(lines)
        status.last_events = events
        if not status.available:
            status.source = "journalctl"
            status.setup_hint = ""
            # Parse recent log lines for stats
            for line in reversed(lines):
                if "hashrate" in line.lower() and status.hashrate == "—":
                    m = re.search(r"([\d.]+)\s*(Th|Gh|Mh|H)/s", line, re.I)
                    if m:
                        status.hashrate = f"{m.group(1)} {m.group(2)}/s"
                if "share" in line.lower():
                    if "accept" in line.lower():
                        status.shares_accepted = line[-40:]
                    elif "reject" in line.lower():
                        status.shares_rejected = line[-40:]
            if events:
                status.available = True
                status.gateway_state = "Log activity detected"

    if not status.available:
        status.gateway_state = "Not Running"
    elif not status.setup_hint:
        status.setup_hint = ""

    return status