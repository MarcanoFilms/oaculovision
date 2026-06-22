"""Node interaction layer — read-only client and gated control."""

from oraculovision.node.client import BitcoinCLIError, NodeClient

__all__ = ["NodeClient", "BitcoinCLIError"]