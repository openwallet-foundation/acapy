"""Profile manager for multitenancy."""

import logging

from ..config.provider import BaseProvider
from ..config.settings import BaseSettings
from ..config.injector import BaseInjector
from ..config.base import InjectionError
from .manager import MultitenantManager
from .askar_profile_manager import AskarProfileMultitenantManager

LOGGER = logging.getLogger(__name__)


class MultitenantManagerProvider(BaseProvider):
    """
    Multitenant manager provider.

    Decides which manager to use based on the settings.
    """

    MANAGER_TYPES = {
        "basic": MultitenantManager,
        "askar": AskarProfileMultitenantManager,
    }

    def __init__(self, root_profile):
        """Initialize the multitenant profile manager provider."""
        self.root_profile = root_profile
        self._inst = {}

    def provide(self, settings: BaseSettings, injector: BaseInjector):
        """Create the multitenant manager instance."""

        key_name = "multitenant.wallet_type"
        manager_type = settings.get_value(key_name, default="basic").lower()

        if manager_type not in self.MANAGER_TYPES:
            raise InjectionError(f"Unknown manager type: {manager_type}")

        manager_class = self.MANAGER_TYPES.get(manager_type)

        if manager_type not in self._inst:
            LOGGER.info("Create multitenant manager: %s", manager_type)
            self._inst[manager_type] = manager_class(self.root_profile)

        return self._inst[manager_type]
