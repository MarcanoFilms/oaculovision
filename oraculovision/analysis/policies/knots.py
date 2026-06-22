"""Fetch and normalize Knots policy information from RPC."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from oraculovision.node.client import NodeClient


@dataclass
class PolicyEntry:
    key: str
    value: str
    source: str


@dataclass
class KnotsPolicySnapshot:
    """Normalized view of node policy settings."""

    entries: list[PolicyEntry] = field(default_factory=list)
    knots_detected: bool = False
    client_name: str = ""
    client_version: str = ""
    subversion: str = ""
    error: str | None = None

    def lines(self) -> list[str]:
        if self.error:
            return [self.error]
        out = []
        if self.client_name:
            out.append(f"Client: {self.client_name} {self.client_version}")
        if self.subversion:
            out.append(f"Subversion: {self.subversion}")
        for entry in self.entries:
            out.append(f"{entry.key}: {entry.value}  [{entry.source}]")
        return out


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.8f}".rstrip("0").rstrip(".")
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def fetch_knots_policies(client: NodeClient) -> KnotsPolicySnapshot:
    """Collect policy-relevant fields from standard Knots/Core RPCs."""
    snapshot = KnotsPolicySnapshot()

    try:
        network = client.get_network_info()
        mempool = client.get_mempool_info()
        chain = client.get_blockchain_info()
        node_info = client.get_node_info()
    except Exception as exc:
        snapshot.error = str(exc)
        return snapshot

    subversion = str(network.get("subversion", ""))
    snapshot.subversion = subversion
    snapshot.knots_detected = "knots" in subversion.lower()
    snapshot.client_name = "Bitcoin Knots" if snapshot.knots_detected else "Bitcoin Core"

    # getnetworkinfo version is compact int
    ver = int(network.get("version", 0))
    major = ver // 10_000
    minor = (ver % 10_000) // 100
    build = ver % 100
    snapshot.client_version = f"{major}.{minor}.{build}"

    entries: list[PolicyEntry] = []

    def add(key: str, value: Any, source: str) -> None:
        entries.append(PolicyEntry(key=key, value=_fmt(value), source=source))

    add("mempool max (MB)", mempool.get("maxmempool", "?"), "getmempoolinfo")
    add("mempool min fee (BTC/kvB)", mempool.get("mempoolminfee", "?"), "getmempoolinfo")
    add("mempool usage (MB)", round(mempool.get("usage", 0) / 1_000_000, 2), "getmempoolinfo")
    add("mempool tx count", mempool.get("size", "?"), "getmempoolinfo")
    add("relay fee (BTC/kvB)", network.get("relayfee", "?"), "getnetworkinfo")
    add("incremental relay fee", network.get("incrementalfee", "?"), "getnetworkinfo")
    add("min relay tx fee", network.get("minrelaytxfee", "?"), "getnetworkinfo")
    add("blocks only", network.get("blocksonly", False), "getnetworkinfo")
    add("whitelist relay", network.get("whitelistrelay", False), "getnetworkinfo")
    add("chain", chain.get("chain", "?"), "getblockchaininfo")
    add("pruned", chain.get("pruned", False), "getblockchaininfo")

    # Knots-specific fields from getnodeinfo when available
    if node_info:
        for key in (
            "datacarrier",
            "datacarriersize",
            "permitbaremultisig",
            "maxscriptsizepolicy",
            "maxdatacarriersize",
            "minrelaytxfee",
            "incrementalrelayfee",
            "bytespersigop",
            "bytespersigopdiscount",
            "permitbaremultisig",
        ):
            if key in node_info:
                add(key, node_info[key], "getnodeinfo")

    snapshot.entries = entries
    return snapshot


def _btc_per_kvb_to_sat_vb(value: str) -> str | None:
    try:
        btc = float(value)
        sats = int(round(btc * 100_000))
        return f"{sats} sat/vB"
    except (ValueError, TypeError):
        return None


def format_mempool_policy_metric(
    snapshot: KnotsPolicySnapshot,
) -> tuple[str, str, str]:
    """Compact (value, subtitle, severity) for the dashboard policy card."""
    if snapshot.error:
        return "—", "unavailable", "danger"

    by_key = {e.key: e.value for e in snapshot.entries}

    max_mb = by_key.get("mempool max (MB)", "?")
    value = f"{max_mb} MB cap"

    parts: list[str] = []
    for fee_key in ("min relay tx fee", "mempool min fee (BTC/kvB)", "relay fee (BTC/kvB)"):
        fee_raw = by_key.get(fee_key)
        if fee_raw and fee_raw != "?":
            fee_fmt = _btc_per_kvb_to_sat_vb(fee_raw) or fee_raw
            parts.append(fee_fmt)
            break

    datacarrier = by_key.get("datacarrier")
    dc_size = by_key.get("maxdatacarriersize") or by_key.get("datacarriersize")
    if datacarrier == "no":
        parts.append("no datacarrier")
    elif dc_size and dc_size != "?":
        parts.append(f"OP_RETURN≤{dc_size}B")

    if by_key.get("blocks only") == "yes":
        parts.append("blocks-only")

    subtitle = " · ".join(parts[:3]) if parts else "defaults"
    severity = "ok" if snapshot.knots_detected else "warn"
    return value, subtitle, severity