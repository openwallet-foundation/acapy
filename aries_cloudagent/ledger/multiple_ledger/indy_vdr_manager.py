"""Multiple IndyVdrLedger Manager."""
import asyncio
import concurrent.futures
import logging
import json

from collections import OrderedDict
from typing import Optional, Tuple, Mapping

from ...cache.base import BaseCache
from ...core.profile import Profile
from ...ledger.error import LedgerError
from ...wallet.crypto import did_is_self_certified

from ..indy_vdr import IndyVdrLedger
from ..merkel_validation.domain_txn_handler import (
    prepare_for_state_read,
    get_proof_nodes,
)
from ..merkel_validation.trie import SubTrie

from .base_manager import BaseMultipleLedgerManager, MultipleLedgerManagerError

LOGGER = logging.getLogger(__name__)


class MultiIndyVDRLedgerManager(BaseMultipleLedgerManager):
    """Multiple Indy VDR Ledger Manager."""

    def __init__(
        self,
        profile: Profile,
        production_ledgers: OrderedDict = OrderedDict(),
        non_production_ledgers: OrderedDict = OrderedDict(),
        write_ledger_info: Tuple[str, IndyVdrLedger] = None,
        cache_ttl: int = None,
    ):
        """Initialize MultiIndyLedgerManager.

        Args:
            profile: The base profile for this manager
            production_ledgers: production IndyVDRLedger mapping
            non_production_ledgers: non_production IndyVDRLedger mapping
            cache_ttl: Time in sec to persist did_ledger_id_resolver cache keys

        """
        self.profile = profile
        self.production_ledgers = production_ledgers
        self.non_production_ledgers = non_production_ledgers
        self.write_ledger_info = write_ledger_info
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        self.cache_ttl = cache_ttl

    async def get_write_ledger(self) -> Optional[Tuple[str, IndyVdrLedger]]:
        """Return the write IndyVdrLedger instance."""
        return self.write_ledger_info

    async def get_prod_ledgers(self) -> Mapping:
        """Return production ledgers mapping."""
        return self.production_ledgers

    async def get_nonprod_ledgers(self) -> Mapping:
        """Return non_production ledgers mapping."""
        return self.non_production_ledgers

    async def _get_ledger_by_did(
        self,
        ledger_id: str,
        did: str,
    ) -> Optional[Tuple[str, IndyVdrLedger, bool]]:
        """Build and submit GET_NYM request and process response.

        Successful response return tuple with ledger_id, IndyVdrLedger instance
        and is_self_certified bool flag. Unsuccessful response return None.

        Args:
            ledger_id: provided ledger_id to retrieve IndyVdrLedger instance
                        from production_ledgers or non_production_ledgers
            did: provided DID

        Return:
            (str, IndyVdrLedger, bool) or None
        """
        try:
            indy_vdr_ledger = None
            if ledger_id in self.production_ledgers:
                indy_vdr_ledger = self.production_ledgers.get(ledger_id)
            else:
                indy_vdr_ledger = self.non_production_ledgers.get(ledger_id)
            async with indy_vdr_ledger:
                request = await indy_vdr_ledger.build_and_return_get_nym_request(
                    None, did
                )
                response_json = await asyncio.wait_for(
                    indy_vdr_ledger.submit_get_nym_request(request), 10
                )
                if isinstance(response_json, dict):
                    response = response_json
                else:
                    response = json.loads(response_json)
                if "result" in response.keys():
                    data = response.get("result", {}).get("data")
                else:
                    data = response.get("data")
                if not data:
                    LOGGER.warning(f"Did {did} not posted to ledger {ledger_id}")
                    return None
                if isinstance(data, str):
                    data = json.loads(data)
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
                    return (ledger_id, indy_vdr_ledger, True)
                return (ledger_id, indy_vdr_ledger, False)
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

    async def lookup_did_in_configured_ledgers(
        self, did: str, cache_did: bool = True
    ) -> Tuple[str, IndyVdrLedger]:
        """Lookup given DID in configured ledgers in parallel."""
        self.cache = self.profile.inject_or(BaseCache)
        cache_key = f"did_ledger_id_resolver::{did}"
        if bool(cache_did and self.cache and await self.cache.get(cache_key)):
            cached_ledger_id = await self.cache.get(cache_key)
            if cached_ledger_id in self.production_ledgers:
                return (cached_ledger_id, self.production_ledgers.get(cached_ledger_id))
            elif cached_ledger_id in self.non_production_ledgers:
                return (
                    cached_ledger_id,
                    self.non_production_ledgers.get(cached_ledger_id),
                )
            else:
                raise MultipleLedgerManagerError(
                    f"cached ledger_id {cached_ledger_id} not found in either "
                    "production_ledgers or non_production_ledgers"
                )
        applicable_prod_ledgers = {"self_certified": {}, "non_self_certified": {}}
        applicable_non_prod_ledgers = {"self_certified": {}, "non_self_certified": {}}
        ledger_ids = list(self.production_ledgers.keys()) + list(
            self.non_production_ledgers.keys()
        )
        coro_futures = {
            self.executor.submit(self._get_ledger_by_did, ledger_id, did): ledger_id
            for ledger_id in ledger_ids
        }
        for coro_future in concurrent.futures.as_completed(coro_futures):
            result = await coro_future.result()
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
            if cache_did and self.cache:
                await self.cache.set(
                    cache_key, successful_ledger_inst[0], self.cache_ttl
                )
            return successful_ledger_inst
        elif len(applicable_non_prod_ledgers.get("self_certified")) > 0:
            successful_ledger_inst = list(
                applicable_non_prod_ledgers.get("self_certified").values()
            )[0]
            if cache_did and self.cache:
                await self.cache.set(
                    cache_key, successful_ledger_inst[0], self.cache_ttl
                )
            return successful_ledger_inst
        elif len(applicable_prod_ledgers.get("non_self_certified")) > 0:
            successful_ledger_inst = list(
                applicable_prod_ledgers.get("non_self_certified").values()
            )[0]
            if cache_did and self.cache:
                await self.cache.set(
                    cache_key, successful_ledger_inst[0], self.cache_ttl
                )
            return successful_ledger_inst
        elif len(applicable_non_prod_ledgers.get("non_self_certified")) > 0:
            successful_ledger_inst = list(
                applicable_non_prod_ledgers.get("non_self_certified").values()
            )[0]
            if cache_did and self.cache:
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
