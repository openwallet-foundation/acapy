"""Errors for config modules."""

from .base import ConfigError


class ArgsParseError(ConfigError):
    """Error raised when there is a problem parsing the command-line arguments."""
