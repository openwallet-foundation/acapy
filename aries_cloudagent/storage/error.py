"""Storage-related exceptions."""

from ..core.error import BaseError


class StorageError(BaseError):
    """Base class for Storage errors."""


class StorageNotFoundError(StorageError):
    """Record not found in storage."""


class StorageDuplicateError(StorageError):
    """Duplicate record found in storage."""


class StorageSearchError(StorageError):
    """General exception during record search."""
