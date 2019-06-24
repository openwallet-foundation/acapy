"""Default ledger provider classes."""

import logging

from ..cache.base import BaseCache
from ..classloader import ClassLoader
from ..config.base import BaseProvider, BaseInjector, BaseSettings
from ..wallet.base import BaseWallet

LOGGER = logging.getLogger(__name__)


class LedgerProvider(BaseProvider):
    """Provider for the default ledger implementation."""

    LEDGER_CLASSES = {"indy": "aries_cloudagent.ledger.indy.IndyLedger"}

    async def provide(self, settings: BaseSettings, injector: BaseInjector):
        """Create and open the ledger instance."""

        genesis_transactions = settings.get("ledger.genesis_transactions")
        keepalive = int(settings.get("ledger.keepalive", 5))
        if genesis_transactions:
            wallet = await injector.inject(BaseWallet)
            IndyLedger = ClassLoader.load_class(self.LEDGER_CLASSES["indy"])
            cache = await injector.inject(BaseCache, required=False)
            return IndyLedger(
                "default",
                wallet,
                genesis_transactions,
                keepalive=keepalive,
                cache=cache,
            )
