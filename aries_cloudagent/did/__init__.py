from .key.manager import DidKeyManager


class DidOperationError(Exception):
    """Generic DID operation Error."""


__all__ = [
    "DidKeyManager",
    "DidOperationError",
]
