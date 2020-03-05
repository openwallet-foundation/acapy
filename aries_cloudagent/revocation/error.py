"""Revocation error classes."""

from ..core.error import BaseError


class RevocationError(BaseError):
    """Base exception for revocation-related errors."""


class RevocationNotSupportedError(RevocationError):
    """Attempted to create registry for non-revocable cred def."""
