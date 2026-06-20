"""Configuration loader for oraculovision."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


def _config_paths() -> list[Path]:
    env = os.environ.get("ORACULOVISION_CONFIG")
    paths: list[Path] = []
    if env:
        paths.append(Path(env))
    paths.extend([
        Path.home() / ".config" / "oraculovision" / "config.toml",
        Path(__file__).resolve().parent.parent / "config.toml",
    ])
    return paths


@dataclass
class RefreshConfig:
    interval_seconds: int = 30


@dataclass
class AlertsConfig:
    min_peers: int = 8
    mempool_congested_mb: float = 50.0
    mempool_congested_tx: int = 5000
    spam_block_score: int = 45


@dataclass
class MempoolGlassConfig:
    sample_size: int = 120


@dataclass
class BitcoinConfig:
    cli_path: str = "bitcoin-cli"
    datadir: str = ""
    utxo_timeout: float = 120.0


@dataclass
class OceanConfig:
    address: str = ""


@dataclass
class AppConfig:
    refresh: RefreshConfig = field(default_factory=RefreshConfig)
    alerts: AlertsConfig = field(default_factory=AlertsConfig)
    mempool_glass: MempoolGlassConfig = field(default_factory=MempoolGlassConfig)
    bitcoin: BitcoinConfig = field(default_factory=BitcoinConfig)
    ocean: OceanConfig = field(default_factory=OceanConfig)


def load_config() -> AppConfig:
    cfg = AppConfig()
    data: dict = {}

    for path in _config_paths():
        if path.is_file():
            try:
                data = tomllib.loads(path.read_text())
                break
            except (OSError, tomllib.TOMLDecodeError):
                continue

    if refresh := data.get("refresh"):
        cfg.refresh = RefreshConfig(
            interval_seconds=int(refresh.get("interval_seconds", 30)),
        )
    if alerts := data.get("alerts"):
        cfg.alerts = AlertsConfig(
            min_peers=int(alerts.get("min_peers", 8)),
            mempool_congested_mb=float(alerts.get("mempool_congested_mb", 50)),
            mempool_congested_tx=int(alerts.get("mempool_congested_tx", 5000)),
            spam_block_score=int(alerts.get("spam_block_score", 45)),
        )
    if glass := data.get("mempool_glass"):
        cfg.mempool_glass = MempoolGlassConfig(
            sample_size=int(glass.get("sample_size", 120)),
        )
    if btc := data.get("bitcoin"):
        cfg.bitcoin = BitcoinConfig(
            cli_path=str(btc.get("cli_path", "bitcoin-cli")),
            datadir=str(btc.get("datadir", "")),
            utxo_timeout=float(btc.get("utxo_timeout", 120)),
        )
    if ocean := data.get("ocean"):
        cfg.ocean = OceanConfig(
            address=str(ocean.get("address", "")).strip(),
        )
    return cfg