import logging
from typing import List

from .base_registry import BaseRegistry

LOGGER = logging.getLogger(__name__)


class AnonCredsRegistry:
    def __init__(self, registries: List[BaseRegistry] = None):
        """Create DID Resolver."""
        self.registries = registries or []
        # TODO: add schema and cred def registries

    def register_registry(self, registry: BaseRegistry):
        """Register a new registry."""
        self.registries.append(registry)

    # TODO: add logic for picking the correct registry
