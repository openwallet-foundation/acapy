"""Legacy Indy Registry"""
import logging
import re
from asyncio import shield
from typing import Pattern

from .....config.injection_context import InjectionContext
from .....core.profile import Profile
from .....ledger.base import BaseLedger
from .....ledger.error import LedgerError
from .....ledger.merkel_validation.constants import GET_SCHEMA
from .....ledger.multiple_ledger.ledger_requests_executor import (
    GET_CRED_DEF, IndyLedgerRequestsExecutor)
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
    AnonCredsCredentialDefinition,
    AnonCredsCredentialDefinitionValue,
    AnonCredsRegistryGetCredentialDefinition,
    AnonCredsRegistryGetRevocationList,
    AnonCredsRegistryGetRevocationRegistryDefinition)
from ....models.anoncreds_schema import AnonCredsRegistryGetSchema, AnonCredsSchema
from ...base_registry import BaseAnonCredsRegistrar, BaseAnonCredsResolver

LOGGER = logging.getLogger(__name__)


class LegacyIndyRegistry(BaseAnonCredsResolver, BaseAnonCredsRegistrar):
    """LegacyIndyRegistry"""

    def __init__(self):
        self._supported_identifiers_regex = re.compile(r"^(?!did).*$")
        # TODO: fix regex (too general)

    @property
    def supported_identifiers_regex(self) -> Pattern:
        return self._supported_identifiers_regex

    async def setup(self, context: InjectionContext):
        """Setup."""
        print("Successfully registered LegacyIndyRegistry")

    async def get_schema(self, profile: Profile, schema_id: str) -> AnonCredsRegistryGetSchema:
        """Get a schema from the registry."""

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
            raise # TODO: AnonCreds error

        async with ledger:
            try:
                schema = await ledger.get_schema(schema_id)
                anonscreds_schema = AnonCredsSchema(
                    issuer_id=schema["id"].split(":")[0],
                    attr_names=schema["attrNames"],
                    name=schema["name"],
                    version=schema["ver"]
                )
                anoncreds_registry_get_schema = AnonCredsRegistryGetSchema(
                    schema=anonscreds_schema,
                    schema_id=schema["id"],
                    resolution_metadata={"ledger_id": ledger_id},
                    schema_metadata={"seqNo": schema["seqNo"]}
                )
            except LedgerError as err:
                raise # TODO: AnonCreds error
        return anoncreds_registry_get_schema

    async def get_schemas(self, profile: Profile, filter: str):
        """Get schema ids filtered by filter"""

    async def register_schema(
        self,
        profile: Profile,
        options: dict,
        schema,
    ):
        """Register a schema on the registry."""
        # Check that schema doesn't already exist
        tag_query = {"schema_name": schema.name, "schema_version": schema.version}
        async with profile.session() as session:
            storage = session.inject(BaseStorage)
            found = await storage.find_all_records(
                type_filter=SCHEMA_SENT_RECORD_TYPE,
                tag_query=tag_query,
            )
            if 0 < len(found):
                raise # TODO: Anoncreds error: f"Schema {schema_name} {schema_version} already exists"

        # Assume endorser role on the network, no option for 3rd-party endorser
        ledger = profile.inject_or(BaseLedger)
        if not ledger:
            reason = "No ledger available"
            if not profile.settings.get_value("wallet.type"):
                reason += ": missing wallet-type?"
            raise # TODO: Anoncreds error

        issuer = profile.inject(AnonCredsIssuer)
        async with ledger:
            try:
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
                raise # TODO: Anoncreds error
        
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
            "schema_metadata": {
                "seqNo": schema_def["seqNo"]
            }
        }

    async def get_credential_definition(
        self, profile: Profile, cred_def_id: str
    ) -> AnonCredsRegistryGetCredentialDefinition:
        """Get a credential definition from the registry."""

<<<<<<< HEAD
    async def get_credential_definitions(self, profile: Profile, filter: str):
        """Get credential definition ids filtered by filter"""
=======
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
            anoncreds_credential_definition_value = AnonCredsCredentialDefinitionValue(
                primary=cred_def["value"]
            )
            anoncreds_credential_definition = AnonCredsCredentialDefinition(
                issuer_id=cred_def["id"].split(":")[0],
                schema_id=cred_def["schemaId"],
                type=cred_def["type"],
                tag=cred_def["tag"],
                value=anoncreds_credential_definition_value,
            )
            anoncreds_registry_get_credential_definition = AnonCredsRegistryGetCredentialDefinition(
                credential_definition=anoncreds_credential_definition,
                credential_definition_id=cred_def["id"],
                resolution_metadata={},
                credential_definition_metadata={},
            )
        return cred_def

        # job_id

>>>>>>> feat: legacy indy schema, cred def logic

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

        return {
            "job_id": None,
            "credential_definition_state": {
                "state": "finished",
                "credential_definition_id": cred_def_id,
                "credential_definition": {
                    "issuerId": issuer_did,
                    "schemaId": schema_id,
                    "type": "CL",
                    "tag": tag,
                    "value": {
                        "primary": {
                            "n": cred_def["value"]["primary"]["n"],
                            "r": cred_def["value"]["primary"]["r"],
                            "rctxt": cred_def["value"]["primary"]["rctxt"],
                            "s": cred_def["value"]["primary"]["s"],
                            "z": cred_def["value"]["primary"]["z"]
                        }
                    }
                }
            },
            "registration_metadata": {},
            "credential_definition_metadata": {}
        }

    async def get_revocation_registry_definition(
        self, profile: Profile, rev_reg_id: str
    ) -> AnonCredsRegistryGetRevocationRegistryDefinition:
        """Get a revocation registry definition from the registry."""

<<<<<<< HEAD
    async def get_revocation_registry_definitions(self, profile: Profile, filter: str):
        """Get credential definition ids filtered by filter"""
=======
        try:
            revoc = IndyRevocation(profile)
            rev_reg = await revoc.get_issuer_rev_reg_record(rev_reg_id)
        except StorageNotFoundError as err:
            raise # Anoncreds error web.HTTPNotFound(reason=err.roll_up) from err

        return rev_reg.serialize
        # use AnonCredsRevocationRegistryDefinition object
>>>>>>> feat: legacy indy schema, cred def logic

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
