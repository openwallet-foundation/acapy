"""Recover a revocation registry.

This module contains general exceptions or helper functions related to revocation
registry recovery that are not specific to any one implementation.
"""


class RevocRecoveryException(Exception):
    """Raise exception performing recovery."""
