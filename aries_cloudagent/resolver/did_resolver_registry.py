"""In memmory storage for registering did resolvers."""

import logging
from typing import Sequence

from .base import BaseDIDResolver

LOGGER = logging.getLogger(__name__)


class DIDResolverRegistry:
    """Registry for did resolvers."""

    def __init__(self):
        """Initialize list for did resolvers."""
        self._resolvers = []

    @property
    def resolvers(
        self,
    ) -> Sequence[BaseDIDResolver]:
        """Accessor for a list of all did resolvers."""
        return self._resolvers

    def register(self, resolver) -> None:
        """Register a resolver."""
        LOGGER.debug("Registering resolver %s", resolver)
        self._resolvers.append(resolver)
