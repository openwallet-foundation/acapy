"""Module setup."""

from ..config.injection_context import InjectionContext
from ..utils.classloader import ClassLoader
from .handler import WalletHandler
from ..wallet.base import BaseWallet

HANDLER_CLASS = "aries_cloudagent.wallet_handler.handler.WalletHandler"
HANDLED_CLASSES = {
    "base": "aries_cloudagent.wallet.base.BaseWallet",
    "indy": "aries_cloudagent.wallet.Indy.IndyWallet",
    "basic": "aries_cloudagent.wallet.basic.BasicWallet",
}
HANDLED_CLASS = BaseWallet


async def setup(context: InjectionContext):
    """Set up wallet handler."""

    # TODO: get necessary config from context
    settings = context.settings

    wallet_cfg = {}
    if "wallet.key" in settings:
        wallet_cfg["key"] = settings["wallet.key"]
    if "wallet.name" in settings:
        wallet_cfg["name"] = settings["wallet.name"]
    if "wallet.storage_type" in settings:
        wallet_cfg["storage_type"] = settings["wallet.storage_type"]
    # storage.config and storage.creds are required if using postgres plugin
    if "wallet.storage_config" in settings:
        wallet_cfg["storage_config"] = settings["wallet.storage_config"]
    if "wallet.storage_creds" in settings:
        wallet_cfg["storage_creds"] = settings["wallet.storage_creds"]

    handeled_provider = context.injector._providers[HANDLED_CLASS]

    handler = ClassLoader.load_class(HANDLER_CLASS)(handeled_provider, wallet_cfg)
    context.injector.bind_instance(WalletHandler, handler)
