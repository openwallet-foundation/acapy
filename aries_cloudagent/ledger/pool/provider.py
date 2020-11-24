"""Default ledger pool provider classes."""

import logging

from ...config.base import BaseProvider, BaseInjector, BaseSettings
from ...utils.classloader import ClassLoader

LOGGER = logging.getLogger(__name__)


class LedgerPoolProvider(BaseProvider):
    """Provider for the default ledger pool implementation."""

    POOL_CLASSES = {"indy": "aries_cloudagent.ledger.pool.indy.IndyLegderPool"}

    async def provide(self, settings: BaseSettings, injector: BaseInjector):
        """Create and open the pool instance."""

        pool_name = settings.get("ledger.pool_name", "default")
        keepalive = int(settings.get("ledger.keepalive", 5))
        wallet_type = settings.get("wallet.type")
        pool = None

        if wallet_type == "indy":
            IndyLedgerPool = ClassLoader.load_class(self.POOL_CLASSES["indy"])
            pool = IndyLedgerPool(pool_name, keepalive=keepalive)

            genesis_transactions = settings.get("ledger.genesis_transactions")
            if genesis_transactions:
                await pool.create_pool_config(genesis_transactions, True)
            elif not await pool.check_pool_config():
                LOGGER.info("Ledger pool configuration has not been created")
                pool = None

        return pool
