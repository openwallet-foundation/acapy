"""DID Indy Registry"""
import logging
from asyncio import shield
import re
from typing import Pattern

from .....config.injection_context import InjectionContext
from .....core.profile import Profile
from .....ledger.base import BaseLedger
from .....ledger.error import LedgerError
from .....ledger.multiple_ledger.ledger_requests_executor import (
    GET_CRED_DEF, GET_SCHEMA, IndyLedgerRequestsExecutor)
from .....messaging.credential_definitions.util import (
    CRED_DEF_SENT_RECORD_TYPE, notify_cred_def_event)
from .....messaging.schemas.util import (SCHEMA_SENT_RECORD_TYPE,
                                         notify_schema_event)
from .....multitenant.base import BaseMultitenantManager
from .....revocation.error import RevocationError
from .....revocation.indy import IndyRevocation
from .....storage.base import BaseStorage
from .....storage.error import StorageNotFoundError
from ....issuer import AnonCredsIssuer, AnonCredsIssuerError
from ....models.anoncreds_cred_def import (
    AnonCredsRegistryGetCredentialDefinition,
    AnonCredsRegistryGetRevocationList,
    AnonCredsRegistryGetRevocationRegistryDefinition)
from ....models.anoncreds_schema import AnonCredsRegistryGetSchema
from ...base_registry import BaseAnonCredsRegistrar, BaseAnonCredsResolver

LOGGER = logging.getLogger(__name__)

class DIDIndyRegistry(BaseAnonCredsResolver, BaseAnonCredsRegistrar):
    """DIDIndyRegistry"""

    def __init__(self):
        self._supported_identifiers_regex = re.compile(r"^did:indy:.*$")

    @property
    def supported_identifiers_regex(self) -> Pattern:
        return self._supported_identifiers_regex
        # TODO: fix regex (too general)

    async def setup(self, context: InjectionContext):
        """Setup."""
        print("Successfully registered DIDIndyRegistry")

    async def get_schema(self, profile: Profile, options, schema, issuer_id) -> AnonCredsRegistryGetSchema:
        """Get a schema from the registry."""
        schema_id = schema.schema_id
        multitenant_mgr = profile.inject_or(BaseMultitenantManager)
        if multitenant_mgr:
            ledger_exec_inst = IndyLedgerRequestsExecutor(profile)
        else:
            ledger_exec_inst = profile.inject(IndyLedgerRequestsExecutor)
        ledger_id, ledger = await ledger_exec_inst.get_ledger_for_identifier(
            schema_id,
            txn_record_type=GET_SCHEMA,
        )
        if not ledger:
            reason = "No ledger available"
            if not profile.settings.get_value("wallet.type"):
                reason += ": missing wallet-type?"
            raise # TODO: create AnonCreds error

        async with ledger:
            try:
                schema = await ledger.get_schema(schema_id)
                # TODO: use schema to create AnonCredsSchema and AnonCredsRegistryGetSchema objects
                # ledger_id goes in resolution_metadata
            except LedgerError as err:
                raise # TODO: create AnonCreds error
        return schema
    # TODO: job_id?

    async def get_schemas(self, profile: Profile, filter: str):
        """Get schema ids filtered by filter"""

    # TODO: determine keyword arguments
    async def register_schema(
        self,
        profile: Profile,
        options: dict,
        schema,
        ):
        """Register a schema on the registry."""
        # TODO: need issuer_id to
        # issuer_id needs to sign the transaction too

        # Check that schema doesn't already exist
        tag_query = {"schema_name": schema.name, "schema_version": schema.version}
        async with profile.session() as session:
            storage = session.inject(BaseStorage)
            found = await storage.find_all_records(
                type_filter=SCHEMA_SENT_RECORD_TYPE,
                tag_query=tag_query,
            )
            if 0 < len(found):
                raise # Anoncreds error: f"Schema {schema_name} {schema_version} already exists"

        # Assume endorser role on the network
        # No option for 3rd-party endorser

        ledger = profile.inject_or(BaseLedger)
        if not ledger:
            reason = "No ledger available"
            if not profile.settings.get_value("wallet.type"):
                reason += ": missing wallet-type?"
            raise # Anoncreds error | web.HTTPForbidden(reason=reason)

        issuer = profile.inject(AnonCredsIssuer)
        async with ledger:
            try:
                # if create_transaction_for_endorser, then the returned "schema_def"
                # is actually the signed transaction
                schema_id, schema_def = await shield(
                    ledger.create_and_send_schema(
                        issuer,
                        schema.name,
                        schema.version,
                        schema.attr_names,
                        write_ledger=True,  # TODO: check
                        endorser_did=schema.issuer_id,
                    )
                )
            except (AnonCredsIssuerError, LedgerError) as err:
                raise # Anoncreds error | web.HTTPBadRequest(reason=err.roll_up) from err
        
        # TODO: use AnonCredsSchema object?
        meta_data = {
            "context": {
                "schema_id": schema_id,
                "schema_name": schema.name,
                "schema_version": schema.version,
                "attributes": schema.attr_names,
            },
            "processing": {},
        }

        # Notify event
        await notify_schema_event(profile, schema_id, meta_data)

        return {
            "job_id": None,
            "schema_state": {
                "state": "finished",
                "schema_id": schema_id,
                "schema": {
                "attrNames": schema_def["attrNames"],
                "name": schema_def["name"],
                "version": schema_def["ver"],
                "issuerId": schema.issuer_id
                }
            },
            "registration_metadata": {},
            # For indy, schema_metadata will contain the seqNo
            "schema_metadata": {
                "seqNo": schema_def["seqNo"]
            }
        }

    async def get_credential_definition(
        self, profile: Profile, cred_def_id: str
    ) -> AnonCredsRegistryGetCredentialDefinition:
        """Get a credential definition from the registry."""

        async with profile.session() as session:
            multitenant_mgr = session.inject_or(BaseMultitenantManager)
            if multitenant_mgr:
                ledger_exec_inst = IndyLedgerRequestsExecutor(profile)
            else:
                ledger_exec_inst = session.inject(IndyLedgerRequestsExecutor)
        ledger_id, ledger = await ledger_exec_inst.get_ledger_for_identifier(
            cred_def_id,
            txn_record_type=GET_CRED_DEF,
        )
        if not ledger:
            reason = "No ledger available"
            if not profile.settings.get_value("wallet.type"):
                reason += ": missing wallet-type?"
            raise # Anoncreds error | web.HTTPForbidden(reason=reason)

        async with ledger:
            cred_def = await ledger.get_credential_definition(cred_def_id)

        return cred_def
    
        # job_id


    # TODO: determine keyword arguments
    async def register_credential_definition(
        self,
        profile: Profile,
        schema_id: str,
        support_revocation: bool,
        tag: str,
        rev_reg_size: int,
        issuer_id: str,
    ):
        """Register a credential definition on the registry."""

        tag_query = {"schema_id": schema_id}
        async with profile.session() as session:
            storage = session.inject(BaseStorage)
            found = await storage.find_all_records(
                type_filter=CRED_DEF_SENT_RECORD_TYPE,
                tag_query=tag_query,
            )
            if 0 < len(found):
                # need to check the 'tag' value
                for record in found:
                    cred_def_id = record.value
                    cred_def_id_parts = cred_def_id.split(":")
                    if tag == cred_def_id_parts[4]:
                        raise # Anoncreds error: web.HTTPBadRequest(
                        #     reason=f"Cred def for {schema_id} {tag} already exists"
                        # )

        ledger = profile.inject_or(BaseLedger)
        if not ledger:
            reason = "No ledger available"
            if not profile.settings.get_value("wallet.type"):
                reason += ": missing wallet-type?"
            raise # Anoncreds error web.HTTPForbidden(reason=reason)

        issuer = profile.inject(AnonCredsIssuer)
        try:  # even if in wallet, send it and raise if erroneously so
            async with ledger:
                (cred_def_id, cred_def, novel) = await shield(
                    ledger.create_and_send_credential_definition(
                        issuer,
                        schema_id,
                        signature_type=None,
                        tag=tag,
                        support_revocation=support_revocation,
                        write_ledger=True,          # TODO: check
                        endorser_did=issuer_id,
                    )
                )

        except (AnonCredsIssuerError, LedgerError) as e:
            raise # Anoncreds error web.HTTPBadRequest(reason=e.message) from e

        issuer_did = cred_def_id.split(":")[0]
        meta_data = {
            "context": {
                "schema_id": schema_id,
                "cred_def_id": cred_def_id,
                "issuer_did": issuer_did,
                "support_revocation": support_revocation,
                "novel": novel,
                "tag": tag,
                "rev_reg_size": rev_reg_size,
            },
            "processing": {
                "create_pending_rev_reg": True,
            },
        }

        # Notify event
        meta_data["processing"]["auto_create_rev_reg"] = True
        await notify_cred_def_event(profile, cred_def_id, meta_data)

        return ( # TODO: check
            {
                "sent": {"credential_definition_id": cred_def_id},
                "credential_definition_id": cred_def_id,
            }
        )


    async def get_revocation_registry_definition(
        self, profile: Profile, rev_reg_id: str
    ) -> AnonCredsRegistryGetRevocationRegistryDefinition:
        """Get a revocation registry definition from the registry."""

        try:
            revoc = IndyRevocation(profile)
            rev_reg = await revoc.get_issuer_rev_reg_record(rev_reg_id)
        except StorageNotFoundError as err:
            raise # Anoncreds error web.HTTPNotFound(reason=err.roll_up) from err

        return rev_reg.serialize
        # use AnonCredsRevocationRegistryDefinition object

    # TODO: determine keyword arguments
    async def register_revocation_registry_definition(
        self,
        profile: Profile,
        rev_reg_id: str,
        issuer_id: str,
    ):
        """Register a revocation registry definition on the registry."""

        try:
            revoc = IndyRevocation(profile)
            rev_reg = await revoc.get_issuer_rev_reg_record(rev_reg_id)

            rev_reg_resp = await rev_reg.send_def(
                profile,
                write_ledger=True,
                endorser_did=issuer_id,
            )
            LOGGER.debug("published rev reg definition: %s", rev_reg_id)
        except StorageNotFoundError as err:
            raise # Anoncreds error web.HTTPNotFound(reason=err.roll_up) from err
        except RevocationError as err:
            raise # Anoncreds error web.HTTPBadRequest(reason=err.roll_up) from err

    async def get_revocation_list(
        self, revocation_registry_id: str, timestamp: str
    ) -> AnonCredsRegistryGetRevocationList:
        """Get a revocation list from the registry."""

    # TODO: determine keyword arguments
    async def register_revocation_list(self):
        """Register a revocation list on the registry."""
