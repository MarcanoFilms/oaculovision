"""Backward-compatible re-export of the node client.

New code should import from ``oraculovision.node.client``.
"""

from oraculovision.node.client import BitcoinCLIError, NodeClient

# Legacy alias used throughout v1 widgets
BitcoinCLI = NodeClient

__all__ = ["BitcoinCLI", "BitcoinCLIError", "NodeClient"]