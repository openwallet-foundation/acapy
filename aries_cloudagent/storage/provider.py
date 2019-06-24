"""Default storage provider classes."""

import logging

from ..classloader import ClassLoader
from ..config.base import BaseProvider, BaseInjector, BaseSettings
from ..wallet.base import BaseWallet

LOGGER = logging.getLogger(__name__)


class StorageProvider(BaseProvider):
    """Provider for the default configurable storage classes."""

    STORAGE_TYPES = {
        "basic": "aries_cloudagent.storage.basic.BasicStorage",
        "indy": "aries_cloudagent.storage.indy.IndyStorage",
        "postgres_storage": "aries_cloudagent.storage.indy.IndyStorage",
    }

    async def provide(self, settings: BaseSettings, injector: BaseInjector):
        """Create and return the storage instance."""

        wallet: BaseWallet = await injector.inject(BaseWallet)

        wallet_type = settings.get_value("wallet.type", default="basic").lower()
        storage_default_type = "indy" if wallet_type == "indy" else "basic"
        storage_type = settings.get_value(
            "storage.type", default=storage_default_type
        ).lower()
        storage_class = self.STORAGE_TYPES.get(storage_type, storage_type)
        storage = ClassLoader.load_class(storage_class)(wallet)
        return storage
