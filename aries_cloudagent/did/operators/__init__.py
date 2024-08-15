from .did_key import DidKeyOperator


class DidOperatorError(Exception):
    """Generic DID Operator Error."""


__all__ = [
    "DidKeyOperator",
    "DidOperatorError",
]
