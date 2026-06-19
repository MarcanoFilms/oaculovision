"""bitcoin-cli subprocess wrapper for oraculovision."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any


class BitcoinCLIError(Exception):
    """Raised when bitcoin-cli fails or is unavailable."""

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        self.hint = hint
        super().__init__(message)


class BitcoinCLI:
    """Thin wrapper around bitcoin-cli JSON-RPC."""

    def __init__(
        self,
        cli_path: str | None = None,
        datadir: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.cli_path = cli_path or os.environ.get("BITCOIN_CLI", "bitcoin-cli")
        self.datadir = datadir or os.environ.get("BITCOIN_DATADIR")
        self.timeout = timeout

    def _base_cmd(self) -> list[str]:
        cmd = [self.cli_path]
        if self.datadir:
            cmd.extend(["-datadir", self.datadir])
        return cmd

    def call(self, method: str, *params: Any) -> Any:
        if not shutil.which(self.cli_path) and not os.path.isabs(self.cli_path):
            raise BitcoinCLIError(
                f"bitcoin-cli no encontrado: {self.cli_path}",
                hint="Instala Bitcoin Knots o define BITCOIN_CLI=/ruta/a/bitcoin-cli",
            )

        cmd = self._base_cmd() + [method]
        for param in params:
            if isinstance(param, (dict, list)):
                cmd.append(json.dumps(param))
            elif isinstance(param, bool):
                cmd.append("true" if param else "false")
            else:
                cmd.append(str(param))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise BitcoinCLIError(
                f"Timeout llamando {method} ({self.timeout}s)",
                hint="El nodo puede estar ocupado o no responder.",
            ) from exc
        except FileNotFoundError as exc:
            raise BitcoinCLIError(
                f"bitcoin-cli no encontrado: {self.cli_path}",
                hint="Verifica la instalación de Knots/Core.",
            ) from exc

        if result.returncode != 0:
            stderr = (result.stderr or result.stdout or "").strip()
            hint = None
            lower = stderr.lower()
            if "could not connect" in lower or "connection refused" in lower:
                hint = "Inicia bitcoind/knots y verifica RPC (bitcoin.conf)."
            elif "verifying blocks" in lower or "initial block download" in lower:
                hint = "El nodo aún sincroniza. Espera a que termine IBD."
            raise BitcoinCLIError(stderr or f"Error en {method}", hint=hint)

        stdout = result.stdout.strip()
        if not stdout:
            return None
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return stdout

    def get_blockchain_info(self) -> dict[str, Any]:
        return self.call("getblockchaininfo")

    def get_network_info(self) -> dict[str, Any]:
        return self.call("getnetworkinfo")

    def get_mempool_info(self) -> dict[str, Any]:
        return self.call("getmempoolinfo")

    def get_block_count(self) -> int:
        return int(self.call("getblockcount"))

    def get_block_hash(self, height: int) -> str:
        return str(self.call("getblockhash", height))

    def get_block(self, block_hash: str, verbosity: int = 2) -> dict[str, Any]:
        return self.call("getblock", block_hash, verbosity)

    def get_block_stats(self, block_hash: str) -> dict[str, Any]:
        try:
            return self.call("getblockstats", block_hash)
        except BitcoinCLIError:
            return {}

    def get_raw_mempool(self, verbose: bool = False) -> list[str] | dict[str, Any]:
        result = self.call("getrawmempool", verbose)
        if verbose:
            return result if isinstance(result, dict) else {}
        return result if isinstance(result, list) else []

    def get_raw_transaction(self, txid: str, verbose: bool = True) -> dict[str, Any]:
        return self.call("getrawtransaction", txid, verbose)

    def get_txoutset_info(self, timeout: float | None = None) -> dict[str, Any]:
        old_timeout = self.timeout
        if timeout is not None:
            self.timeout = timeout
        try:
            return self.call("gettxoutsetinfo")
        finally:
            self.timeout = old_timeout

    def get_block_template(self) -> dict[str, Any]:
        return self.call("getblocktemplate", {"rules": ["segwit"]})

    def decode_raw_transaction(self, hex_data: str) -> dict[str, Any]:
        return self.call("decoderawtransaction", hex_data)

    def is_available(self) -> tuple[bool, str | None]:
        try:
            self.get_block_count()
            return True, None
        except BitcoinCLIError as exc:
            msg = str(exc)
            if exc.hint:
                msg = f"{msg}\n→ {exc.hint}"
            return False, msg