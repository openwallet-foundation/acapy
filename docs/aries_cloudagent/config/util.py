"""Entrypoint."""

import os
import re

from configargparse import ArgumentTypeError
from typing import Any, Mapping

from .logging import LoggingConfigurator


def common_config(settings: Mapping[str, Any]):
    """Perform common app configuration."""
    # Set up logging
    log_config = settings.get("log.config")
    log_level = settings.get("log.level") or os.getenv("LOG_LEVEL")
    log_file = settings.get("log.file")
    LoggingConfigurator.configure(log_config, log_level, log_file)


class BoundedInt:
    """Argument value parser for a bounded integer."""

    def __init__(self, min: int = None, max: int = None):
        """Initialize the ByteBoundedIntSize parser."""
        self.min_val = min
        self.max_val = max

    def __call__(self, arg: str) -> int:
        """Interpret the argument value."""
        if not arg:
            raise ArgumentTypeError("Expected integer value")
        try:
            val = int(arg)
        except ValueError:
            raise ArgumentTypeError(f"Invalid integer value: '{arg}'")
        if self.min_val is not None and val < self.min_val:
            raise ArgumentTypeError(
                f"Value must be greater than or equal to {self.min_val}"
            )
        if self.max_val is not None and val > self.max_val:
            raise ArgumentTypeError(
                f"Value must be less than or equal to {self.max_val}"
            )
        return val

    def __repr__(self):
        """Format for in error reporting."""
        return "integer"


class ByteSize:
    """Argument value parser for byte sizes."""

    def __init__(self, min: int = 0, max: int = None):
        """Initialize the ByteSize parser."""
        self.min_size = min
        self.max_size = max

    def __call__(self, arg: str) -> int:
        """Interpret the argument value."""
        if not arg:
            raise ArgumentTypeError("Expected value (size in bytes)")
        parts = re.match(r"^(\d+)([kKmMgGtT]?)[bB]?$", arg)
        if not parts:
            raise ArgumentTypeError(f"Invalid size value: '{arg}'")
        size = int(parts[1])
        suffix = parts[2].upper()
        if suffix == "K":
            size = size << 10
        elif suffix == "M":
            size = size << 20
        elif suffix == "G":
            size = size << 30
        elif suffix == "T":
            size = size << 40
        if size < self.min_size:
            raise ArgumentTypeError(
                f"Value must be greater than or equal to {self.min_size}"
            )
        if self.max_size and size > self.max_size:
            raise ArgumentTypeError(
                f"Value must be less than or equal to {self.max_size}"
            )
        return size

    def __repr__(self):
        """Format for in error reporting."""
        return "bytes"
