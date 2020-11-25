"""Default ledger provider classes."""

import logging

from ..cache.base import BaseCache
from ..config.base import BaseProvider, BaseInjector, BaseSettings
from ..utils.classloader import ClassLoader
from ..wallet.base import BaseWallet

LOGGER = logging.getLogger(__name__)


class LedgerProvider(BaseProvider):
    """Provider for the default ledger implementation."""

    LEDGER_CLASSES = {"indy": "aries_cloudagent.ledger.indy.IndyLedger"}

    async def provide(self, settings: BaseSettings, injector: BaseInjector):
        """Create and open the ledger instance."""

        if settings.get("ledger.disabled"):
            LOGGER.info("Ledger support is disabled")
            return

        pool_name = settings.get("ledger.pool_name", "default")
        keepalive = int(settings.get("ledger.keepalive", 5))
        read_only = bool(settings.get("ledger.read_only", False))
        if read_only:
            LOGGER.error("Note: setting ledger to read-only mode")
        wallet = injector.inject(BaseWallet)
        ledger = None

        if wallet.type == "indy":
            IndyLedger = ClassLoader.load_class(self.LEDGER_CLASSES["indy"])
            cache = injector.inject(BaseCache, required=False)
            ledger = IndyLedger(
                pool_name, wallet, keepalive=keepalive, cache=cache, read_only=read_only
            )

            genesis_transactions = settings.get("ledger.genesis_transactions")
            if genesis_transactions:
                await ledger.create_pool_config(genesis_transactions, True)
            elif not await ledger.check_pool_config():
                LOGGER.info("Ledger pool configuration has not been created")
                ledger = None

        return ledger
