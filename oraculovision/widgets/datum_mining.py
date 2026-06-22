"""DATUM mining panel widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, Static

from oraculovision.config import AppConfig
from oraculovision.data.datum import DatumJob, DatumStatus, fetch_datum_job, fetch_datum_status
from oraculovision.data.ocean import (
    OceanAccountStats,
    OceanEarnings,
    fetch_ocean_account_stats,
    format_ocean_address,
    invalidate_ocean_cache,
)

_LABEL_WIDTH = 20


class DatumMining(Static):
    """Shows DATUM gateway status, workers, hashrate, and shares."""

    DEFAULT_CSS = """
    DatumMining {
        height: auto;
        min-height: 14;
        border: solid #ffd700;
        padding: 1 2;
    }
    DatumMining .datum-ok { color: #3dd68c; }
    DatumMining .datum-warn { color: #ffd700; }
    DatumMining .datum-err { color: #ff6b6b; }
    DatumMining .datum-metric { color: #e0e0e0; }
    DatumMining .datum-hint { color: #888; }
    """

    def __init__(self, config: AppConfig | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = config or AppConfig()
        self.border_title = "DATUM MINING"
        self._session_ocean_address: str | None = None

    @property
    def active_ocean_address(self) -> str:
        """Session override, else config.toml [ocean].address."""
        if self._session_ocean_address is not None:
            return self._session_ocean_address
        return self.config.ocean.address

    def set_ocean_address(self, address: str) -> None:
        """Set session Ocean address (empty string hides the section)."""
        previous = self.active_ocean_address
        self._session_ocean_address = address.strip()
        if previous and previous != self._session_ocean_address:
            invalidate_ocean_cache(previous)
        if self._session_ocean_address:
            invalidate_ocean_cache(self._session_ocean_address)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Querying DATUM...", id="datum-content", classes="datum-metric")

    @staticmethod
    def _kv(label: str, value: str, width: int = _LABEL_WIDTH) -> str:
        return f"  {label.ljust(width)}{value}"

    def _render_job_lines(self, job: DatumJob) -> list[str]:
        if not job.available:
            return ["", "[bold]CURRENT JOB[/]", "  [dim]No active stratum job[/]"]

        prev = job.prev_block_hash
        if len(prev) > 20:
            prev = f"{prev[:16]}…"

        lines = [
            "",
            "[bold #ffd700]──── CURRENT JOB ────[/]",
            f"  Job ID     {job.job_id}",
            f"  Height     {job.height}",
            f"  Value      {job.coinbase_value_btc}",
            f"  Prev block {prev}",
            f"  Target     {job.target[:24] + '…' if len(job.target) > 24 else job.target}",
            f"  Difficulty {job.difficulty}",
            f"  Tx count   {job.tx_count}  weight {job.weight}  size {job.size}",
            f"  Version    {job.version}  bits {job.bits}",
            f"  Time       {job.time_info}",
            f"  Limits     {job.limits}",
        ]
        if job.coinbase_outputs:
            lines.append(f"  Coinbase   {job.coinbase_outputs} outputs (/coinbaser)")
        return lines

    def _render_datum_lines(self, status: DatumStatus) -> list[str]:
        workers = status.workers
        if status.worker_names:
            worker_detail = ", ".join(status.worker_names[:5])
            if len(status.worker_names) > 5:
                worker_detail += f" +{len(status.worker_names) - 5}"
        else:
            worker_detail = str(workers)

        lines = [
            f"Gateway:   {status.gateway_state}",
            f"Workers:   {worker_detail}",
            f"Hashrate:  {status.hashrate}",
            f"Shares:    ✓ {status.shares_accepted}",
            f"Rejected:  ✗ {status.shares_rejected}",
            f"Pool:      {status.pool_host}",
            f"Miner tag: {status.miner_tag}",
            f"Job h:     {status.job_height}  uptime: {status.uptime}",
        ]
        if status.last_events:
            lines.append("— Recent events —")
            lines.extend(f"  {e[:72]}" for e in status.last_events[-4:])
        return lines

    def _render_ocean_prompt(self) -> list[str]:
        return [
            "",
            "[bold #ffd700]──── OCEAN ACCOUNT ────[/]",
            "[dim]Press o to enter a payout address[/]",
        ]

    def _render_hashrate_section(self, stats: OceanAccountStats) -> list[str]:
        lines = ["", "[bold]Hashrate[/]"]
        for interval in stats.intervals:
            pct = interval.hash_pct if interval.hash_pct != "—" else "—"
            lines.append(f"  [bold]{interval.label}[/]")
            lines.append(
                self._kv(
                    "You",
                    f"{interval.miner_hashrate}  shares {interval.shares}  {pct} of pool",
                    width=6,
                )
            )
            lines.append(self._kv("Pool", interval.pool_hashrate, width=6))
        lines.append(self._kv("TIDES window", stats.tides_shares_pct))
        return lines

    def _render_earnings_section(self, earnings: OceanEarnings) -> list[str]:
        lines = ["", "[bold]Earnings & Payouts[/]"]
        if earnings.error:
            lines.append(f"  [yellow]⚠ {earnings.error}[/]")
            return lines

        lines.append(self._kv("Est. per day", earnings.est_per_day))
        lines.append(self._kv("Unpaid", earnings.unpaid))
        lines.append(self._kv("Next block est.", earnings.est_next_block))
        if earnings.lifetime != "—":
            lines.append(self._kv("Lifetime", earnings.lifetime))
        lines.append(self._kv("Blocks earned (TIDES)", f"{earnings.blocks_earned_tides} (30d)"))
        found_line = f"{earnings.blocks_found_by_you} (30d)"
        if earnings.blocks_found_by_you > 0 and earnings.found_worker_names:
            names = ", ".join(earnings.found_worker_names[:3])
            if len(earnings.found_worker_names) > 3:
                names += f" +{len(earnings.found_worker_names) - 3}"
            found_line = f"{found_line}  ({names})"
        lines.append(self._kv("Blocks found by you", found_line))

        if earnings.workers_hashing:
            names = ", ".join(earnings.worker_names[:4])
            if len(earnings.worker_names) > 4:
                names += f" +{len(earnings.worker_names) - 4}"
            lines.append(self._kv("Workers hashing", f"{earnings.workers_hashing}  ({names})"))
        else:
            lines.append(self._kv("Workers hashing", "0"))

        return lines

    def _render_ocean_section(self, stats: OceanAccountStats) -> list[str]:
        lines = [
            "",
            "[bold #ffd700]──── OCEAN ACCOUNT ────[/]",
            f"  Address   {format_ocean_address(stats.address)}  [dim](o = change)[/]",
        ]

        if stats.error:
            lines.append(f"  [yellow]⚠ {stats.error}[/]")
            return lines

        if not stats.available:
            lines.append("  [yellow]⚠ Ocean data unavailable[/]")
            return lines

        lines.extend(self._render_hashrate_section(stats))
        lines.extend(self._render_earnings_section(stats.earnings))
        return lines

    def _append_ocean_lines(self, lines: list[str]) -> None:
        ocean_address = self.active_ocean_address
        if not ocean_address:
            lines.extend(self._render_ocean_prompt())
            return
        ocean_stats = fetch_ocean_account_stats(ocean_address)
        lines.extend(self._render_ocean_section(ocean_stats))

    def refresh_data(self) -> None:
        label = self.query_one("#datum-content", Label)
        status = fetch_datum_status()

        if not status.available:
            lines = [status.setup_hint or "DATUM unavailable."]
            self._append_ocean_lines(lines)
            label.update("\n".join(lines))
            label.remove_class("datum-ok", "datum-err")
            label.add_class("datum-warn")
            return

        state_lower = status.gateway_state.lower()
        if "ready" in state_lower or "connected" in state_lower:
            state_cls = "datum-ok"
        elif "error" in state_lower or "not" in state_lower:
            state_cls = "datum-err"
        else:
            state_cls = "datum-warn"

        lines = self._render_datum_lines(status)
        lines.extend(self._render_job_lines(fetch_datum_job()))
        self._append_ocean_lines(lines)

        label.update("\n".join(lines))
        label.remove_class("datum-ok", "datum-warn", "datum-err")
        label.add_class(state_cls)