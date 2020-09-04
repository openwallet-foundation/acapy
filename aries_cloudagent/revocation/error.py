"""Revocation error classes."""

from ..core.error import BaseError


class RevocationError(BaseError):
    """Base exception for revocation-related errors."""


class RevocationNotSupportedError(RevocationError):
    """Attempted to create registry for non-revocable cred def."""


class RevocationRegistryBadSizeError(RevocationError):
    """Attempted to create registry with maximum credentials too large or too small."""
