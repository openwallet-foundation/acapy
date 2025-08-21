"""Module docstring."""

from enum import Enum


class DatabaseErrorCode(Enum):
    """Enum for database error codes."""

    DATABASE_NOT_FOUND = "DATABASE_NOT_FOUND"
    UNSUPPORTED_VERSION = "UNSUPPORTED_VERSION"
    DEFAULT_PROFILE_NOT_FOUND = "DEFAULT_PROFILE_NOT_FOUND"
    PROFILE_NOT_FOUND = "PROFILE_NOT_FOUND"
    CONNECTION_POOL_EXHAUSTED = "CONNECTION_POOL_EXHAUSTED"
    PROFILE_ALREADY_EXISTS = "PROFILE_ALREADY_EXISTS"
    DATABASE_NOT_ENCRYPTED = "DATABASE_NOT_ENCRYPTED"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    QUERY_ERROR = "QUERY_ERROR"
    PROVISION_ERROR = "PROVISION_ERROR"
    DUPLICATE_ITEM_ENTRY_ERROR = "DUPLICATE_ITEM_ENTRY_ERROR"
    RECORD_NOT_FOUND = "RECORD_NOT_FOUND"


class DatabaseError(Exception):
    """Custom exception class for database-related errors."""

    def __init__(self, code: DatabaseErrorCode, message: str, actual_error: str = None):
        """Initialize DatabaseError with code, message and optional actual error."""
        super().__init__(message)
        self.code = code
        self.actual_error = actual_error
