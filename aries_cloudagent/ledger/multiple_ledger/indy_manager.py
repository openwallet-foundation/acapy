"""Multiple IndySdkLedger Manager."""
import asyncio
import concurrent.futures
import logging
import json

from collections import OrderedDict
from typing import List, Optional, Tuple

from ...cache.base import BaseCache
from ...core.profile import Profile
from ...config.provider import ClassProvider
from ...indy.verifier import IndyVerifier
from ...ledger.base import BaseLedger
from ...ledger.error import LedgerError
from ...wallet.base import BaseWallet
from ...wallet.crypto import did_is_self_certified

from ..indy import IndySdkLedger, IndySdkLedgerPool
from ..merkel_validation.domain_txn_handler import (
    prepare_for_state_read,
    get_proof_nodes,
)
from ..merkel_validation.trie import SubTrie

from .base_manager import BaseMultipleLedgerManager, MultipleLedgerManagerError

LOGGER = logging.getLogger(__name__)
 

class MultiIndyLedgerManager(BaseMultipleLedgerManager):
    """Multiple Indy SDK Ledger Manager."""

    def __init__(
        self,
        profile: Profile,
        production_ledgers: OrderedDict = OrderedDict(),
        non_production_ledgers: OrderedDict = OrderedDict(),
        cache_ttl: int = 600,
    ):
        """Initialize MultiIndyLedgerManager.

        Args:
            profile: The base profile for this manager
            production_ledgers: List of production IndySdkLedger
            non_production_ledgers: List of non_production IndySdkLedger
            cache_ttl: Time in sec to persist did_ledger_id_resolver cache keys

        """
        self.profile = profile
        self.production_ledgers = production_ledgers
        self.non_production_ledgers = non_production_ledgers
        self.cache = profile.inject_or(BaseCache)
        self.write_ledger = None
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        self.cache_ttl = cache_ttl

    async def get_write_ledger(self) -> IndySdkLedger:
        """Return the write IndySdkLedger instance."""
        if not self.write_ledger:
            if len(self.production_ledgers) > 0:
                return list(self.production_ledgers.items())[0][1]
            elif len(self.non_production_ledgers) > 0:
                return list(self.non_production_ledgers.items())[0][1]
        else:
            return self.write_ledger

    async def set_write_ledger(self, ledger_id: str) -> IndySdkLedger:
        """Set a IndySdkLedger as the write ledger.

        Args:
            ledger_id: The identifier for the configured ledger

        Returns:
            IndySdkLedger: IndySdkLedger to submit write requests

        """
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
                f"ledger {ledger_id} not found in configured production"
                " and non_production ledgers."
            )

    async def update_profile_context(self, ledger: IndySdkLedger):
        """Bind updated BaseLedger and IndyVerifer in Profile Context."""
        self.profile.context.injector.bind_instance(BaseLedger, ledger)
        self.profile.context.injector.bind_provider(
            IndyVerifier,
            ClassProvider(
                "aries_cloudagent.indy.sdk.verifier.IndySdkVerifier",
                ledger,
            ),
        )

    async def reset_write_ledger(self) -> IndySdkLedger:
        """Reset set write ledger, if any, to default."""
        self.write_ledger = None
        ledger = self.get_write_ledger()
        await self.update_profile_context(ledger)
        return ledger

    async def update_ledger_config(self, ledger_config_list: List):
        """
        Update ledger config.

        Recreate production_ledgers and non_production_ledgers from
        the provided ledger_config_list

        Args:
            ledger_config_list: provided config list

        """
        production_ledgers = OrderedDict()
        non_production_ledgers = OrderedDict()
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            for config in ledger_config_list:
                pool_name = config.get("pool_name", "default")
                keepalive = int(config.get("keepalive", 5))
                read_only = bool(config.get("read_only", False))
                socks_proxy = config.get("socks_proxy")
                genesis_transactions = config.get("genesis_transactions")
                cache = self.profile.inject_or(BaseCache)
                ledger_id = config.get("id")
                ledger_is_production = config.get("is_production")
                ledger_pool = IndySdkLedgerPool(
                    pool_name,
                    keepalive=keepalive,
                    cache=cache,
                    genesis_transactions=genesis_transactions,
                    read_only=read_only,
                    socks_proxy=socks_proxy,
                )
                ledger_instance = IndySdkLedger(
                    pool=ledger_pool,
                    wallet=wallet,
                )
                if ledger_is_production:
                    production_ledgers[ledger_id] = ledger_instance
                else:
                    non_production_ledgers[ledger_id] = ledger_instance
        self.production_ledgers = production_ledgers
        self.non_production_ledgers = non_production_ledgers

    async def _get_ledger_by_did(
        self,
        ledger_id: str,
        did: str,
    ) -> Optional[Tuple[str, IndySdkLedger, bool]]:
        """Call _get_ledger_by_did and return value or None.

        Args:
            ledger_id: provided ledger_id to retrieve IndySdkLedger instance
                        from production_ledgers or non_production_ledgers
            did: provided DID

        Return:
            (str, IndySdkLedger, bool) or None
        """
        try:
            indy_sdk_ledger = None
            if ledger_id in self.production_ledgers:
                indy_sdk_ledger = self.production_ledgers.get(ledger_id)
            else:
                indy_sdk_ledger = self.non_production_ledgers.get(ledger_id)
            async with indy_sdk_ledger:
                request = await indy_sdk_ledger.build_get_nym_request(None, did)
                response = await asyncio.wait_for(indy_sdk_ledger._submit(request), 10)
                data = json.loads(response["data"])
                if not data:
                    LOGGER.warning(f"Did {did} not posted to ledger {ledger_id}")
                    return None
                if not await SubTrie.verify_spv_proof(
                    expected_value=prepare_for_state_read(response),
                    proof_nodes=get_proof_nodes(response),
                ):
                    LOGGER.warning(
                        f"State Proof validation failed for Did {did} "
                        f"and ledger {ledger_id}"
                    )
                    return None
                if did_is_self_certified(did, data.get("verkey")):
                    return (ledger_id, indy_sdk_ledger, True)
                return (ledger_id, indy_sdk_ledger, False)
        except asyncio.TimeoutError:
            LOGGER.exception(
                f"get-nym request timedout for Did {did} and "
                f"ledger {ledger_id}, reply not received within 10 sec"
            )
            return None
        except LedgerError as err:
            LOGGER.error(
                "Exception when building and submitting get-nym request, "
                f"for Did {did} and ledger {ledger_id}, {err}"
            )
            return None

    def get_ledger_by_did_callable(
        self,
        ledger_id: str,
        did: str,
    ) -> Optional[Tuple[str, IndySdkLedger, bool]]:
        """Call _get_ledger_by_did, return (ledger_id, IndySdkLedger, bool) or None."""
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(self._get_ledger_by_did(ledger_id, did))

    async def lookup_did_in_configured_ledgers(
        self, did: str
    ) -> Tuple[str, IndySdkLedger]:
        """Lookup given DID in configured ledgers in parallel."""
        cache_key = f"did_ledger_id_resolver::{did}"
        if self.cache and await self.cache.get(cache_key):
            cached_ledger_id = await self.cache.get(cache_key)
            if cached_ledger_id in self.production_ledgers:
                return (cached_ledger_id, self.production_ledgers.get(cached_ledger_id))
            elif cached_ledger_id in self.non_production_ledgers:
                return (
                    cached_ledger_id,
                    self.non_production_ledgers.get(cached_ledger_id),
                )
            else:
                raise MultipleLedgerManagerError()
        applicable_prod_ledgers = {"self_certified": {}, "non_self_certified": {}}
        applicable_non_prod_ledgers = {"self_certified": {}, "non_self_certified": {}}
        ledger_ids = list(self.production_ledgers.keys()) + list(
            self.non_production_ledgers.keys()
        )
        coro_futures = {
            self.executor.submit(
                self.get_ledger_by_did_callable, ledger_id, did
            ): ledger_id
            for ledger_id in ledger_ids
        }
        for coro_future in concurrent.futures.as_completed(coro_futures):
            result = coro_future.result()
            if result:
                applicable_ledger_id = result[0]
                applicable_ledger_inst = result[1]
                is_self_certified = result[2]
                if applicable_ledger_id in self.production_ledgers:
                    insert_key = list(self.production_ledgers).index(
                        applicable_ledger_id
                    )
                    if is_self_certified:
                        applicable_prod_ledgers["self_certified"][insert_key] = (
                            applicable_ledger_id,
                            applicable_ledger_inst,
                        )
                    else:
                        applicable_prod_ledgers["non_self_certified"][insert_key] = (
                            applicable_ledger_id,
                            applicable_ledger_inst,
                        )
                else:
                    insert_key = list(self.non_production_ledgers).index(
                        applicable_ledger_id
                    )
                    if is_self_certified:
                        applicable_non_prod_ledgers["self_certified"][insert_key] = (
                            applicable_ledger_id,
                            applicable_ledger_inst,
                        )
                    else:
                        applicable_non_prod_ledgers["non_self_certified"][
                            insert_key
                        ] = (applicable_ledger_id, applicable_ledger_inst)
        applicable_prod_ledgers["self_certified"] = OrderedDict(
            sorted(applicable_prod_ledgers.get("self_certified").items())
        )
        applicable_prod_ledgers["non_self_certified"] = OrderedDict(
            sorted(applicable_prod_ledgers.get("non_self_certified").items())
        )
        applicable_non_prod_ledgers["self_certified"] = OrderedDict(
            sorted(applicable_non_prod_ledgers.get("self_certified").items())
        )
        applicable_non_prod_ledgers["non_self_certified"] = OrderedDict(
            sorted(applicable_non_prod_ledgers.get("non_self_certified").items())
        )
        if len(applicable_prod_ledgers.get("self_certified")) > 0:
            successful_ledger_inst = list(
                applicable_prod_ledgers.get("self_certified").values()
            )[0]
            if self.cache:
                await self.cache.set(
                    cache_key, successful_ledger_inst[0], self.cache_ttl
                )
            return successful_ledger_inst
        elif len(applicable_non_prod_ledgers.get("self_certified")) > 0:
            successful_ledger_inst = list(
                applicable_non_prod_ledgers.get("self_certified").values()
            )[0]
            if self.cache:
                await self.cache.set(
                    cache_key, successful_ledger_inst[0], self.cache_ttl
                )
            return successful_ledger_inst
        elif len(applicable_prod_ledgers.get("non_self_certified")) > 0:
            successful_ledger_inst = list(
                applicable_prod_ledgers.get("non_self_certified").values()
            )[0]
            if self.cache:
                await self.cache.set(
                    cache_key, successful_ledger_inst[0], self.cache_ttl
                )
            return successful_ledger_inst
        elif len(applicable_non_prod_ledgers.get("non_self_certified")) > 0:
            successful_ledger_inst = list(
                applicable_non_prod_ledgers.get("non_self_certified").values()
            )[0]
            if self.cache:
                await self.cache.set(
                    cache_key, successful_ledger_inst[0], self.cache_ttl
                )
            return successful_ledger_inst
        else:
            raise MultipleLedgerManagerError(
                f"DID {did} not found in any of the ledgers total: "
                f"(production: {len(self.production_ledgers)}, "
                f"non_production: {len(self.non_production_ledgers)})"
            )
