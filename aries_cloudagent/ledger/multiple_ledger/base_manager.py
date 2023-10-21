"""Manager for multiple ledger."""

import json

from abc import ABC, abstractmethod
from typing import Optional, Tuple, Mapping, List

from ...admin.request_context import AdminRequestContext
from ...core.error import BaseError
from ...core.profile import Profile
from ...ledger.base import BaseLedger
from ...storage.base import BaseStorage, StorageRecord
from ...storage.error import StorageNotFoundError, StorageDuplicateError, StorageError
from ...messaging.valid import IndyDID
from ...multitenant.manager import BaseMultitenantManager
from ...wallet.base import BaseWallet, DEFAULT_PUBLIC_DID
from ...wallet.routes import promote_wallet_public_did

RECORD_TYPE_LEDGER_PUBLIC_DID_MAP = "acapy_ledger_public_did_map"


class MultipleLedgerManagerError(BaseError):
    """Generic multiledger error."""


class BaseMultipleLedgerManager(ABC):
    """Base class for handling multiple ledger support."""

    def __init__(self, profile: Profile):
        """Initialize Multiple Ledger Manager."""

    @abstractmethod
    def get_endorser_info_for_ledger(self, ledger_id: str) -> Optional[Tuple[str, str]]:
        """Return endorser alias, did tuple for provided ledger, if available."""

    @abstractmethod
    async def get_write_ledgers(self) -> List[str]:
        """Return write ledger."""

    @abstractmethod
    async def get_prod_ledgers(self) -> Mapping:
        """Return configured production ledgers."""

    @abstractmethod
    async def get_nonprod_ledgers(self) -> Mapping:
        """Return configured non production ledgers."""

    @abstractmethod
    async def _get_ledger_by_did(
        self, ledger_id: str, did: str
    ) -> Optional[Tuple[str, BaseLedger, bool]]:
        """Build and submit GET_NYM request and process response."""

    @abstractmethod
    async def get_ledger_inst_by_id(self, ledger_id: str) -> Optional[BaseLedger]:
        """Return ledger instance by identifier."""

    @abstractmethod
    async def lookup_did_in_configured_ledgers(
        self, did: str, cache_did: bool
    ) -> Tuple[str, BaseLedger]:
        """Lookup given DID in configured ledgers in parallel."""

    def extract_did_from_identifier(self, identifier: str) -> str:
        """Return did from record identifier (REV_REG_ID, CRED_DEF_ID, SCHEMA_ID)."""
        if bool(IndyDID.PATTERN.match(identifier)):
            return identifier.split(":")[-1]
        else:
            return identifier.split(":")[0]

    async def get_ledger_id_by_ledger_pool_name(self, pool_name: str) -> str:
        """Return ledger_id by ledger pool name."""
        multi_ledgers = self.production_ledgers | self.non_production_ledgers
        for ledger_id, ledger in multi_ledgers.items():
            if ledger.pool_name == pool_name:
                return ledger_id
        raise MultipleLedgerManagerError(
            f"Provided Ledger pool name {pool_name} not found "
            "in either production_ledgers or non_production_ledgers"
        )

    async def set_profile_write_ledger(
        self, ledger_id: str, context: AdminRequestContext
    ) -> str:
        """Set the write ledger for the profile."""
        profile = context.profile
        if ledger_id not in self.writable_ledgers:
            raise MultipleLedgerManagerError(
                f"Provided Ledger identifier {ledger_id} is not write configurable."
            )
        extra_settings = {}
        multi_tenant_mgr = self.profile.inject_or(BaseMultitenantManager)
        multi_ledgers = self.production_ledgers | self.non_production_ledgers
        if ledger_id in multi_ledgers:
            profile.context.injector.bind_instance(
                BaseLedger, multi_ledgers.get(ledger_id)
            )
            self._update_settings(profile.context.settings, ledger_id)
            self._update_settings(extra_settings, ledger_id)
            if multi_tenant_mgr:
                await multi_tenant_mgr.update_wallet(
                    profile.context.settings["wallet.id"],
                    extra_settings,
                )
                set_default_public_did = False
                try:
                    async with profile.session() as session:
                        storage = session.inject_or(BaseStorage)
                        write_ledger = session.inject(BaseLedger)
                        ledger_id_public_did_map_record: StorageRecord = (
                            await storage.find_record(
                                type_filter=RECORD_TYPE_LEDGER_PUBLIC_DID_MAP,
                                tag_query={},
                            )
                        )
                        ledger_id = await self.get_ledger_id_by_ledger_pool_name(
                            write_ledger.pool_name
                        )
                        ledger_id_public_did_map = json.loads(
                            ledger_id_public_did_map_record.value
                        )
                        public_did_config = ledger_id_public_did_map.get(ledger_id)
                        if public_did_config:
                            info, _ = await promote_wallet_public_did(
                                profile=profile,
                                context=context,
                                session_fn=context.session,
                                did=public_did_config.get("did"),
                                write_ledger=public_did_config.get("write_ledger"),
                                connection_id=public_did_config.get("connection_id"),
                                routing_keys=public_did_config.get("routing_keys"),
                                mediator_endpoint=public_did_config.get(
                                    "mediator_endpoint"
                                ),
                                ledger_pool_name=write_ledger.pool_name,
                                record_type_name=RECORD_TYPE_LEDGER_PUBLIC_DID_MAP,
                            )
                            assert info
                            set_default_public_did = False
                        else:
                            set_default_public_did = True
                except (
                    StorageError,
                    StorageNotFoundError,
                    StorageDuplicateError,
                ):
                    set_default_public_did = True
                if set_default_public_did:
                    try:
                        async with self.profile.session() as session:
                            storage = session.inject_or(BaseStorage)
                            wallet = session.inject_or(BaseWallet)
                            default_public_did_record: StorageRecord = (
                                await storage.find_record(
                                    type_filter=DEFAULT_PUBLIC_DID, tag_query={}
                                )
                            )
                            default_public_did = default_public_did_record.value
                            info = await wallet.set_public_did(default_public_did)
                            assert info
                    except (
                        StorageError,
                        StorageNotFoundError,
                        StorageDuplicateError,
                    ):
                        pass
            return ledger_id
        raise MultipleLedgerManagerError(f"No ledger info found for {ledger_id}.")

    def _update_settings(self, settings, ledger_id: str):
        endorser_info = self.get_endorser_info_for_ledger(ledger_id)
        if endorser_info:
            endorser_alias, endorser_did = endorser_info
            settings["endorser.endorser_alias"] = endorser_alias
            settings["endorser.endorser_public_did"] = endorser_did
        settings["ledger.write_ledger"] = ledger_id
