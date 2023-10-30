"""Tails server related errors."""

from ..core.error import BaseError


class TailsServerNotConfiguredError(BaseError):
    """Error indicating the tails server plugin hasn't been configured."""
