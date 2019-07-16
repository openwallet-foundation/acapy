"""Errors for config modules."""

from ..error import BaseError


class ArgsParseError(BaseError):
    """Error raised when there is a problem parsing the command-line arguments."""
