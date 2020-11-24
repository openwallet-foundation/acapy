"""Default ledger provider classes."""

import logging

from ..cache.base import BaseCache
from ..config.base import BaseProvider, BaseInjector, BaseSettings
from ..utils.classloader import ClassLoader
from ..wallet.base import BaseWallet
from .pool.base import BaseLedgerPool

LOGGER = logging.getLogger(__name__)


class LedgerProvider(BaseProvider):
    """Provider for the default ledger implementation."""

    LEDGER_CLASSES = {"indy": "aries_cloudagent.ledger.indy.IndyLedger"}

    async def provide(self, settings: BaseSettings, injector: BaseInjector):
        """Create the ledger instance."""

        read_only = bool(settings.get("ledger.read_only", False))
        if read_only:
            LOGGER.error("Note: setting ledger to read-only mode")
        wallet = await injector.inject(BaseWallet)
        pool = await injector.inject(BaseLedgerPool, required=False)
        ledger = None

        if pool and wallet.type == "indy":
            IndyLedger = ClassLoader.load_class(self.LEDGER_CLASSES["indy"])
            cache = await injector.inject(BaseCache, required=False)
            ledger = IndyLedger(pool, wallet, cache=cache, read_only=read_only)

        return ledger
