"""Profile manager for multiple Indy ledger support."""

import logging
from collections import OrderedDict

from ...cache.base import BaseCache
from ...config.injector import BaseInjector, InjectionError
from ...config.provider import BaseProvider
from ...config.settings import BaseSettings
from ...core.profile import Profile
from ...utils.classloader import ClassNotFoundError, DeferLoad
from .base_manager import MultipleLedgerManagerError

LOGGER = logging.getLogger(__name__)


class MultiIndyLedgerManagerProvider(BaseProvider):
    """Multiple Indy ledger support manager provider."""

    MANAGER_TYPES = {
        "single-wallet-askar": (
            DeferLoad(
                "acapy_agent.ledger.multiple_ledger."
                "indy_vdr_manager.MultiIndyVDRLedgerManager"
            )
        ),
    }
    LEDGER_TYPES = {
        "single-wallet-askar": {
            "pool": DeferLoad("acapy_agent.ledger.indy_vdr.IndyVdrLedgerPool"),
            "ledger": DeferLoad("acapy_agent.ledger.indy_vdr.IndyVdrLedger"),
        },
    }

    def __init__(self, root_profile):
        """Initialize the multiple Indy ledger profile manager provider."""
        self._inst = {}
        self.root_profile: Profile = root_profile

    def provide(self, settings: BaseSettings, injector: BaseInjector):
        """Create the multiple Indy ledger manager instance."""

        backend_name = self.root_profile.BACKEND_NAME
        if backend_name in ("askar", "askar-anoncreds"):
            manager_type = "single-wallet-askar"
        else:
            raise MultipleLedgerManagerError(f"Unexpected wallet backend: {backend_name}")

        if manager_type not in self._inst:
            manager_class = self.MANAGER_TYPES.get(manager_type)
            pool_class = self.LEDGER_TYPES[manager_type]["pool"]
            ledger_class = self.LEDGER_TYPES[manager_type]["ledger"]
            LOGGER.info("Create multiple Indy ledger manager: %s", manager_type)
            try:
                indy_vdr_production_ledgers = OrderedDict()
                indy_vdr_non_production_ledgers = OrderedDict()
                ledger_config_list = settings.get_value("ledger.ledger_config_list")
                ledger_endorser_map = {}
                write_ledgers = set()
                for config in ledger_config_list:
                    keepalive = config.get("keepalive")
                    read_only = config.get("read_only")
                    socks_proxy = config.get("socks_proxy")
                    genesis_transactions = config.get("genesis_transactions")
                    cache = injector.inject_or(BaseCache)
                    ledger_id = config.get("id")
                    pool_name = config.get("pool_name")
                    ledger_is_production = config.get("is_production")
                    ledger_is_write = config.get("is_write")
                    ledger_endorser_alias = config.get("endorser_alias")
                    ledger_endorser_did = config.get("endorser_did")
                    ledger_pool = pool_class(
                        pool_name,
                        keepalive=keepalive,
                        cache=cache,
                        genesis_transactions=genesis_transactions,
                        read_only=read_only,
                        socks_proxy=socks_proxy,
                    )
                    ledger_instance = ledger_class(
                        pool=ledger_pool,
                        profile=self.root_profile,
                    )
                    if ledger_is_write:
                        write_ledgers.add(ledger_id)
                    if ledger_is_production:
                        indy_vdr_production_ledgers[ledger_id] = ledger_instance
                    else:
                        indy_vdr_non_production_ledgers[ledger_id] = ledger_instance
                    if ledger_endorser_alias and ledger_endorser_did:
                        ledger_endorser_map[ledger_id] = {
                            "endorser_alias": ledger_endorser_alias,
                            "endorser_did": ledger_endorser_did,
                        }
                self._inst[manager_type] = manager_class(
                    self.root_profile,
                    production_ledgers=indy_vdr_production_ledgers,
                    non_production_ledgers=indy_vdr_non_production_ledgers,
                    writable_ledgers=write_ledgers,
                    endorser_map=ledger_endorser_map,
                )
            except ClassNotFoundError as err:
                raise InjectionError(
                    f"Unknown multiple Indy ledger manager type: {manager_type}"
                ) from err

        return self._inst[manager_type]
