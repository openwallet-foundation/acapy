"""Admin error classes."""

from ..core.error import BaseError


class AdminError(BaseError):
    """Base class for Admin-related errors."""


class AdminSetupError(AdminError):
    """Admin server setup or configuration error."""
