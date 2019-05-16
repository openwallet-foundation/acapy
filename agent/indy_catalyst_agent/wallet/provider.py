"""Default wallet provider classes."""

import logging

from ..classloader import ClassLoader
from ..config.base import BaseProvider, BaseInjector, BaseSettings

LOGGER = logging.getLogger(__name__)


class WalletProvider(BaseProvider):
    """Provider for the default configurable wallet classes."""

    WALLET_TYPES = {
        "basic": "indy_catalyst_agent.wallet.basic.BasicWallet",
        "indy": "indy_catalyst_agent.wallet.indy.IndyWallet",
    }

    async def provide(self, settings: BaseSettings, injector: BaseInjector):
        """Create and open the wallet instance."""

        wallet_type = settings.get_value("wallet.type", default="basic").lower()
        wallet_class = self.WALLET_TYPES.get(wallet_type, wallet_type)

        LOGGER.info("Opening wallet type: %s", wallet_type)

        wallet_cfg = {}
        if "wallet.key" in settings:
            wallet_cfg["key"] = settings["wallet.key"]
        if "wallet.name" in settings:
            wallet_cfg["name"] = settings["wallet.name"]
        wallet = ClassLoader.load_class(wallet_class)(wallet_cfg)
        await wallet.open()
        return wallet
