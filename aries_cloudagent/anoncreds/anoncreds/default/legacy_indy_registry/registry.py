"""Legacy Indy Registry"""
import logging
import re
from asyncio import shield
from typing import Optional, Pattern, Sequence

from anoncreds import Schema

from .....config.injection_context import InjectionContext
from .....core.profile import Profile
from .....ledger.base import BaseLedger
from .....ledger.error import LedgerError, LedgerObjectAlreadyExistsError
from .....ledger.merkel_validation.constants import GET_SCHEMA
from .....ledger.multiple_ledger.ledger_requests_executor import (
    GET_CRED_DEF,
    IndyLedgerRequestsExecutor,
)
from .....messaging.credential_definitions.util import notify_cred_def_event
from .....multitenant.base import BaseMultitenantManager
from .....revocation.error import RevocationError
from .....revocation.indy import IndyRevocation
from .....storage.error import StorageNotFoundError
from ....issuer import AnonCredsIssuer, AnonCredsIssuerError
from ....models.anoncreds_cred_def import (
    AnonCredsCredentialDefinition,
    AnonCredsCredentialDefinitionValue,
    AnonCredsRegistryGetCredentialDefinition,
    AnonCredsRegistryGetRevocationList,
    AnonCredsRegistryGetRevocationRegistryDefinition,
)
from ....models.anoncreds_schema import (
    GetSchemaResult,
    AnonCredsSchema,
    SchemaResult,
    SchemaState,
)
from ...base_registry import (
    AnonCredsRegistrationError,
    AnonCredsResolutionError,
    AnonCredsSchemaAlreadyExists,
    BaseAnonCredsRegistrar,
    BaseAnonCredsResolver,
)

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

    async def get_schema(self, profile: Profile, schema_id: str) -> GetSchemaResult:
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
            raise AnonCredsResolutionError(reason)

        async with ledger:
            try:
                schema = await ledger.get_schema(schema_id)
                anonscreds_schema = AnonCredsSchema(
                    issuer_id=schema["id"].split(":")[0],
                    attr_names=schema["attrNames"],
                    name=schema["name"],
                    version=schema["ver"],
                )
                result = GetSchemaResult(
                    schema=anonscreds_schema,
                    schema_id=schema["id"],
                    resolution_metadata={"ledger_id": ledger_id},
                    schema_metadata={"seqNo": schema["seqNo"]},
                )
            except LedgerError as err:
                raise AnonCredsResolutionError("Failed to retrieve schema") from err

        return result

    async def register_schema(
        self,
        profile: Profile,
        issuer_id: str,
        name: str,
        version: str,
        attr_names: Sequence[str],
        options: Optional[dict] = None,
    ) -> SchemaResult:
        """Register a schema on the registry."""

        schema = Schema.create(name, version, issuer_id, attr_names)
        schema_id = f"{issuer_id}:2:{name}:{version}"

        # Assume endorser role on the network, no option for 3rd-party endorser
        ledger = profile.inject_or(BaseLedger)
        if not ledger:
            reason = "No ledger available"
            if not profile.settings.get_value("wallet.type"):
                # TODO is this warning necessary?
                reason += ": missing wallet-type?"
            raise AnonCredsRegistrationError(reason)

        # Translate schema into format expected by Indy
        LOGGER.debug("Registering schema: %s", schema_id)
        anoncreds_schema = schema.to_dict()
        indy_schema = {
            "ver": "1.0",
            "id": schema_id,
            "name": anoncreds_schema["name"],
            "version": anoncreds_schema["version"],
            "attrNames": anoncreds_schema["attrNames"],
            "seqNo": None,
        }
        LOGGER.debug("schema value: %s", indy_schema)

        async with ledger:
            try:
                seq_no = await shield(ledger.send_schema(schema_id, indy_schema))
            except LedgerObjectAlreadyExistsError as err:
                raise AnonCredsSchemaAlreadyExists(err.message, err.obj)
            except (AnonCredsIssuerError, LedgerError) as err:
                raise AnonCredsRegistrationError("Failed to register schema") from err

        return SchemaResult(
            job_id=None,
            schema_state=SchemaState(
                state=SchemaState.STATE_FINISHED,
                schema_id=schema_id,
                schema_def=AnonCredsSchema.deserialize(anoncreds_schema),
            ),
            registration_metadata={},
            schema_metadata={"seqNo": seq_no},
        )

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
            raise AnonCredsResolutionError(reason)

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
            anoncreds_registry_get_credential_definition = (
                AnonCredsRegistryGetCredentialDefinition(
                    credential_definition=anoncreds_credential_definition,
                    credential_definition_id=cred_def["id"],
                    resolution_metadata={},
                    credential_definition_metadata={},
                )
            )
        return anoncreds_registry_get_credential_definition

    async def register_credential_definition(
        self,
        profile: Profile,
        schema_id: str,
        support_revocation: bool,
        tag: str,
        rev_reg_size: int,
        issuer_id: str,
        options,  # TODO: handle options
    ):
        """Register a credential definition on the registry."""

        ledger = profile.inject_or(BaseLedger)
        if not ledger:
            reason = "No ledger available"
            if not profile.settings.get_value("wallet.type"):
                reason += ": missing wallet-type?"
            raise AnonCredsRegistrationError(reason)

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
                        write_ledger=True,
                        endorser_did=issuer_id,
                    )
                )

        except (AnonCredsIssuerError, LedgerError) as e:
            raise AnonCredsRegistrationError(e)

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
                            "z": cred_def["value"]["primary"]["z"],
                        }
                    },
                },
            },
            "registration_metadata": {},
            "credential_definition_metadata": {},
        }

    async def get_revocation_registry_definition(
        self, profile: Profile, rev_reg_id: str
    ) -> AnonCredsRegistryGetRevocationRegistryDefinition:
        """Get a revocation registry definition from the registry."""

        try:
            revoc = IndyRevocation(profile)
            rev_reg = await revoc.get_issuer_rev_reg_record(rev_reg_id)
        except StorageNotFoundError as err:
            raise AnonCredsResolutionError(err)

        return rev_reg.serialize
        # use AnonCredsRevocationRegistryDefinition object

    async def get_revocation_registry_definitions(self, profile: Profile, filter: str):
        """Get credential definition ids filtered by filter"""

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

            await rev_reg.send_def(
                profile,
                write_ledger=True,
                endorser_did=issuer_id,
            )
            LOGGER.debug("published rev reg definition: %s", rev_reg_id)
        except StorageNotFoundError as err:
            raise AnonCredsRegistrationError(err)
        except RevocationError as err:
            raise AnonCredsRegistrationError(err)

    async def get_revocation_list(
        self, revocation_registry_id: str, timestamp: str
    ) -> AnonCredsRegistryGetRevocationList:
        """Get a revocation list from the registry."""

    # TODO: determine keyword arguments
    async def register_revocation_list(self):
        """Register a revocation list on the registry."""
