from .did_key import DIDKey


class DidOperationError(Exception):
    """Generic DID operation Error."""


__all__ = [
    "DIDKey",
    "DidOperationError",
]
