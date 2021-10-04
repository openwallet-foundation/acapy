import asyncio
import concurrent.futures
import json

from collections import OrderedDict
from typing import List, Optional, Sequence

from ...cache.base import BaseCache
from ...core.profile import Profile
from ...config.provider import ClassProvider
from ...indy.verifier import IndyVerifier
from ...ledger.base import BaseLedger
from ...ledger.error import LedgerTransactionError, LedgerError

from ..indy_vdr import IndyVdrLedger, IndyVdrLedgerPool

from .base_manager import BaseMultipleLedgerManager, MultipleLedgerManagerError


class MultiIndyVDRLedgerManager:
    """Multiple Indy VDR Ledger Manager."""

    def __init__(
        self,
        profile: Profile,
        production_ledgers: OrderedDict = OrderedDict(),
        non_production_ledgers: OrderedDict = OrderedDict(),
    ):
        """Initialize MultiIndyLedgerManager.

        Args:
            profile (Profile): The profile
            ledgers: List of IndyVDRLedger

        """
        self.profile = profile
        self.production_ledgers = production_ledgers
        self.non_production_ledgers = non_production_ledgers
        self.cache = profile.inject_or(BaseCache)
        self.write_ledger = None
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    async def get_write_ledger(self) -> IndyVdrLedger:
        """Return the write IndySdkLedger instance."""
        if not self.write_ledger:
            if len(self.production_ledgers.keys()) > 0:
                return list(self.production_ledgers.items())[0][1]
            elif len(self.non_production_ledgers.keys()) > 0:
                return list(self.non_production_ledgers.items())[0][1]
        else:
            return self.write_ledger

    async def set_write_ledger(self, ledger_id: str = None) -> IndyVdrLedger:
        ledger = None
        if ledger_id in self.production_ledgers.keys():
            ledger = self.production_ledgers.get(ledger_id)
        elif ledger_id in self.non_production_ledgers.keys():
            ledger = self.non_production_ledgers.get(ledger_id)

        if ledger:
            await self.update_profile_context(ledger)
            return ledger
        else:
            raise MultipleLedgerManagerError(
                "ledger_id not found in configured production and non_production ledgers."
            )

    async def update_profile_context(self, ledger: IndyVdrLedger):
        self.profile.context.injector.bind_instance(BaseLedger, ledger)
        self.profile.context.injector.bind_provider(
            IndyVerifier,
            ClassProvider(
                "aries_cloudagent.indy.credx.verifier.IndyCredxVerifier",
                self.profile,
            ),
        )

    async def reset_write_ledger(self) -> IndyVdrLedger:
        self.write_ledger = None
        ledger = self.get_write_ledger()
        await self.update_profile_context(ledger)
        return ledger

    async def update_ledger_config(self, ledger_config_list: List):
        production_ledgers = OrderedDict()
        non_production_ledgers = OrderedDict()
        for config in ledger_config_list:
            pool_name = config.get("pool_name", "default")
            keepalive = int(config.get("keepalive", 5))
            read_only = bool(config.get("read_only", False))
            socks_proxy = config.get("socks_proxy")
            genesis_transactions = config.get("genesis_transactions")
            cache = self.profile.inject_or(BaseCache)
            ledger_id = config.get("id")
            ledger_is_production = config.get("is_production")
            ledger_pool = IndyVdrLedgerPool(
                pool_name,
                keepalive=keepalive,
                cache=cache,
                genesis_transactions=genesis_transactions,
                read_only=read_only,
                socks_proxy=socks_proxy,
            )
            ledger_instance = IndyVdrLedger(
                pool=ledger_pool,
                profile=self.profile,
            )
            if ledger_is_production:
                production_ledgers[ledger_id] = ledger_instance
            else:
                non_production_ledgers[ledger_id] = ledger_instance
        self.production_ledgers = production_ledgers
        self.non_production_ledgers = non_production_ledgers

    async def get_ledger_instance_by_did(
        self,
        ledger_instance: IndyVdrLedger,
        public_did: str,
        schema_name: str,
        schema_version: str,
        attribute_names: Sequence[str],
    ) -> Optional[IndyVdrLedger]:
        pass
