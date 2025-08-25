"""Error classes for database management."""

from enum import IntEnum


class DBStoreErrorCode(IntEnum):
    """Error codes for database store operations."""

    SUCCESS = 0
    BACKEND = 1
    BUSY = 2
    DUPLICATE = 3
    ENCRYPTION = 4
    INPUT = 5
    NOT_FOUND = 6
    UNEXPECTED = 7
    UNSUPPORTED = 8
    WRAPPER = 99
    CUSTOM = 100


class DBStoreError(Exception):
    """Database store error."""

    def __init__(self, code: DBStoreErrorCode, message: str, extra: str = None):
        """Initialize DBStoreError."""
        super().__init__(message)
        self.code = code
        self.extra = extra
