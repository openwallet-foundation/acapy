"""Credential definition admin routes."""

import json
from time import time

# from asyncio import ensure_future, shield
from asyncio import shield

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)

from marshmallow import fields

from ...admin.request_context import AdminRequestContext
from ...core.event_bus import Event, EventBus
from ...core.profile import Profile
from ...indy.issuer import IndyIssuer, IndyIssuerError
from ...indy.models.cred_def import CredentialDefinitionSchema
from ...ledger.base import BaseLedger
from ...ledger.error import LedgerError
from ...ledger.multiple_ledger.ledger_requests_executor import (
    GET_CRED_DEF,
    IndyLedgerRequestsExecutor,
)
from ...multitenant.base import BaseMultitenantManager
from ...protocols.endorse_transaction.v1_0.manager import (
    TransactionManager,
    TransactionManagerError,
)
from ...protocols.endorse_transaction.v1_0.models.transaction_record import (
    TransactionRecordSchema,
)
from ...protocols.endorse_transaction.v1_0.util import (
    is_author_role,
    get_endorser_connection_id,
)

from ...revocation.indy import IndyRevocation
from ...storage.base import BaseStorage, StorageRecord
from ...storage.error import StorageError

from ..models.openapi import OpenAPISchema
from ..valid import INDY_CRED_DEF_ID, INDY_REV_REG_SIZE, INDY_SCHEMA_ID


from .util import (
    CredDefQueryStringSchema,
    CRED_DEF_TAGS,
    CRED_DEF_SENT_RECORD_TYPE,
    EVENT_LISTENER_PATTERN,
    notify_cred_def_event,
)


from ..valid import UUIDFour
from ...connections.models.conn_record import ConnRecord
from ...storage.error import StorageNotFoundError
from ..models.base import BaseModelError


class CredentialDefinitionSendRequestSchema(OpenAPISchema):
    """Request schema for schema send request."""

    schema_id = fields.Str(description="Schema identifier", **INDY_SCHEMA_ID)
    support_revocation = fields.Boolean(
        required=False, description="Revocation supported flag"
    )
    revocation_registry_size = fields.Int(
        description="Revocation registry size",
        required=False,
        strict=True,
        **INDY_REV_REG_SIZE,
    )
    tag = fields.Str(
        required=False,
        description="Credential definition identifier tag",
        default="default",
        example="default",
    )


class CredentialDefinitionSendResultSchema(OpenAPISchema):
    """Result schema content for schema send request with auto-endorse."""

    credential_definition_id = fields.Str(
        description="Credential definition identifier", **INDY_CRED_DEF_ID
    )


class TxnOrCredentialDefinitionSendResultSchema(OpenAPISchema):
    """Result schema for credential definition send request."""

    sent = fields.Nested(
        CredentialDefinitionSendResultSchema(),
        required=False,
        definition="Content sent",
    )
    txn = fields.Nested(
        TransactionRecordSchema(),
        required=False,
        description="Credential definition transaction to endorse",
    )


class CredentialDefinitionGetResultSchema(OpenAPISchema):
    """Result schema for schema get request."""

    credential_definition = fields.Nested(CredentialDefinitionSchema)


class CredentialDefinitionsCreatedResultSchema(OpenAPISchema):
    """Result schema for cred-defs-created request."""

    credential_definition_ids = fields.List(
        fields.Str(description="Credential definition identifiers", **INDY_CRED_DEF_ID)
    )


class CredDefIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking cred def id."""

    cred_def_id = fields.Str(
        description="Credential definition identifier",
        required=True,
        **INDY_CRED_DEF_ID,
    )


class CreateCredDefTxnForEndorserOptionSchema(OpenAPISchema):
    """Class for user to input whether to create a transaction for endorser or not."""

    create_transaction_for_endorser = fields.Boolean(
        description="Create Transaction For Endorser's signature",
        required=False,
    )


class CredDefConnIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    conn_id = fields.Str(
        description="Connection identifier", required=False, example=UUIDFour.EXAMPLE
    )


@docs(
    tags=["credential-definition"],
    summary="Sends a credential definition to the ledger",
)
@request_schema(CredentialDefinitionSendRequestSchema())
@querystring_schema(CreateCredDefTxnForEndorserOptionSchema())
@querystring_schema(CredDefConnIdMatchInfoSchema())
@response_schema(TxnOrCredentialDefinitionSendResultSchema(), 200, description="")
async def credential_definitions_send_credential_definition(request: web.BaseRequest):
    """
    Request handler for sending a credential definition to the ledger.

    Args:
        request: aiohttp request object

    Returns:
        The credential definition identifier

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile
    outbound_handler = request["outbound_message_router"]

    create_transaction_for_endorser = json.loads(
        request.query.get("create_transaction_for_endorser", "false")
    )
    write_ledger = not create_transaction_for_endorser
    endorser_did = None
    connection_id = request.query.get("conn_id")

    body = await request.json()

    schema_id = body.get("schema_id")
    support_revocation = bool(body.get("support_revocation"))
    tag = body.get("tag")
    rev_reg_size = body.get("revocation_registry_size")

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
                    raise web.HTTPBadRequest(
                        reason=f"Cred def for {schema_id} {tag} already exists"
                    )

    # check if we need to endorse
    if is_author_role(context.profile):
        # authors cannot write to the ledger
        write_ledger = False
        create_transaction_for_endorser = True
        if not connection_id:
            # author has not provided a connection id, so determine which to use
            connection_id = await get_endorser_connection_id(context.profile)
            if not connection_id:
                raise web.HTTPBadRequest(reason="No endorser connection found")

    if not write_ledger:
        try:
            async with profile.session() as session:
                connection_record = await ConnRecord.retrieve_by_id(
                    session, connection_id
                )
        except StorageNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err
        except BaseModelError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

        async with profile.session() as session:
            endorser_info = await connection_record.metadata_get(
                session, "endorser_info"
            )
        if not endorser_info:
            raise web.HTTPForbidden(
                reason="Endorser Info is not set up in "
                "connection metadata for this connection record"
            )
        if "endorser_did" not in endorser_info.keys():
            raise web.HTTPForbidden(
                reason=' "endorser_did" is not set in "endorser_info"'
                " in connection metadata for this connection record"
            )
        endorser_did = endorser_info["endorser_did"]

    ledger = context.inject_or(BaseLedger)
    if not ledger:
        reason = "No ledger available"
        if not context.settings.get_value("wallet.type"):
            reason += ": missing wallet-type?"
        raise web.HTTPForbidden(reason=reason)

    issuer = context.inject(IndyIssuer)
    try:  # even if in wallet, send it and raise if erroneously so
        async with ledger:
            (cred_def_id, cred_def, novel) = await shield(
                ledger.create_and_send_credential_definition(
                    issuer,
                    schema_id,
                    signature_type=None,
                    tag=tag,
                    support_revocation=support_revocation,
                    write_ledger=write_ledger,
                    endorser_did=endorser_did,
                )
            )

    except (IndyIssuerError, LedgerError) as e:
        raise web.HTTPBadRequest(reason=e.message) from e

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

    if not create_transaction_for_endorser:
        # Notify event
        meta_data["processing"]["auto_create_rev_reg"] = True
        await notify_cred_def_event(context.profile, cred_def_id, meta_data)

        return web.json_response(
            {
                "sent": {"credential_definition_id": cred_def_id},
                "credential_definition_id": cred_def_id,
            }
        )

    # If the transaction is for the endorser, but the schema has already been created,
    # then we send back the schema since the transaction will fail to be created.
    elif "signed_txn" not in cred_def:
        return web.json_response({"sent": {"credential_definition_id": cred_def_id}})
    else:
        meta_data["processing"]["auto_create_rev_reg"] = context.settings.get_value(
            "endorser.auto_create_rev_reg"
        )

        transaction_mgr = TransactionManager(context.profile)
        try:
            transaction = await transaction_mgr.create_record(
                messages_attach=cred_def["signed_txn"],
                connection_id=connection_id,
                meta_data=meta_data,
            )
        except StorageError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

        # if auto-request, send the request to the endorser
        if context.settings.get_value("endorser.auto_request"):
            try:
                transaction, transaction_request = await transaction_mgr.create_request(
                    transaction=transaction,
                    # TODO see if we need to parameterize these params
                    # expires_time=expires_time,
                    # endorser_write_txn=endorser_write_txn,
                )
            except (StorageError, TransactionManagerError) as err:
                raise web.HTTPBadRequest(reason=err.roll_up) from err

            await outbound_handler(transaction_request, connection_id=connection_id)

        return web.json_response(
            {
                "sent": {"credential_definition_id": cred_def_id},
                "txn": transaction.serialize(),
            }
        )


@docs(
    tags=["credential-definition"],
    summary="Search for matching credential definitions that agent originated",
)
@querystring_schema(CredDefQueryStringSchema())
@response_schema(CredentialDefinitionsCreatedResultSchema(), 200, description="")
async def credential_definitions_created(request: web.BaseRequest):
    """
    Request handler for retrieving credential definitions that current agent created.

    Args:
        request: aiohttp request object

    Returns:
        The identifiers of matching credential definitions.

    """
    context: AdminRequestContext = request["context"]

    session = await context.session()
    storage = session.inject(BaseStorage)
    found = await storage.find_all_records(
        type_filter=CRED_DEF_SENT_RECORD_TYPE,
        tag_query={
            tag: request.query[tag] for tag in CRED_DEF_TAGS if tag in request.query
        },
    )

    return web.json_response(
        {"credential_definition_ids": [record.value for record in found]}
    )


@docs(
    tags=["credential-definition"],
    summary="Gets a credential definition from the ledger",
)
@match_info_schema(CredDefIdMatchInfoSchema())
@response_schema(CredentialDefinitionGetResultSchema(), 200, description="")
async def credential_definitions_get_credential_definition(request: web.BaseRequest):
    """
    Request handler for getting a credential definition from the ledger.

    Args:
        request: aiohttp request object

    Returns:
        The credential definition details.

    """
    context: AdminRequestContext = request["context"]
    cred_def_id = request.match_info["cred_def_id"]

    async with context.profile.session() as session:
        multitenant_mgr = session.inject_or(BaseMultitenantManager)
        if multitenant_mgr:
            ledger_exec_inst = IndyLedgerRequestsExecutor(context.profile)
        else:
            ledger_exec_inst = session.inject(IndyLedgerRequestsExecutor)
    ledger_id, ledger = await ledger_exec_inst.get_ledger_for_identifier(
        cred_def_id,
        txn_record_type=GET_CRED_DEF,
    )
    if not ledger:
        reason = "No ledger available"
        if not context.settings.get_value("wallet.type"):
            reason += ": missing wallet-type?"
        raise web.HTTPForbidden(reason=reason)

    async with ledger:
        cred_def = await ledger.get_credential_definition(cred_def_id)

    if ledger_id:
        return web.json_response(
            {"ledger_id": ledger_id, "credential_definition": cred_def}
        )
    else:
        return web.json_response({"credential_definition": cred_def})


@docs(
    tags=["credential-definition"],
    summary="Writes a credential definition non-secret record to the wallet",
)
@match_info_schema(CredDefIdMatchInfoSchema())
@response_schema(CredentialDefinitionGetResultSchema(), 200, description="")
async def credential_definitions_fix_cred_def_wallet_record(request: web.BaseRequest):
    """
    Request handler for fixing a credential definition wallet non-secret record.

    Args:
        request: aiohttp request object

    Returns:
        The credential definition details.

    """
    context: AdminRequestContext = request["context"]

    cred_def_id = request.match_info["cred_def_id"]

    async with context.profile.session() as session:
        storage = session.inject(BaseStorage)
        multitenant_mgr = session.inject_or(BaseMultitenantManager)
        if multitenant_mgr:
            ledger_exec_inst = IndyLedgerRequestsExecutor(context.profile)
        else:
            ledger_exec_inst = session.inject(IndyLedgerRequestsExecutor)
    ledger_id, ledger = await ledger_exec_inst.get_ledger_for_identifier(
        cred_def_id,
        txn_record_type=GET_CRED_DEF,
    )
    if not ledger:
        reason = "No ledger available"
        if not context.settings.get_value("wallet.type"):
            reason += ": missing wallet-type?"
        raise web.HTTPForbidden(reason=reason)

    async with ledger:
        cred_def = await ledger.get_credential_definition(cred_def_id)
        cred_def_id_parts = cred_def_id.split(":")
        schema_seq_no = cred_def_id_parts[3]
        schema_response = await ledger.get_schema(schema_seq_no)
        schema_id = schema_response["id"]
        iss_did = cred_def_id_parts[0]

        # check if the record exists, if not add it
        found = await storage.find_all_records(
            type_filter=CRED_DEF_SENT_RECORD_TYPE,
            tag_query={
                "cred_def_id": cred_def_id,
            },
        )
        if 0 == len(found):
            await add_cred_def_non_secrets_record(
                session.profile, schema_id, iss_did, cred_def_id
            )

    if ledger_id:
        return web.json_response(
            {"ledger_id": ledger_id, "credential_definition": cred_def}
        )
    else:
        return web.json_response({"credential_definition": cred_def})


def register_events(event_bus: EventBus):
    """Subscribe to any events we need to support."""
    event_bus.subscribe(EVENT_LISTENER_PATTERN, on_cred_def_event)


async def on_cred_def_event(profile: Profile, event: Event):
    """Handle any events we need to support."""
    schema_id = event.payload["context"]["schema_id"]
    cred_def_id = event.payload["context"]["cred_def_id"]
    issuer_did = event.payload["context"]["issuer_did"]

    # after the ledger record is written, write the wallet non-secrets record
    await add_cred_def_non_secrets_record(profile, schema_id, issuer_did, cred_def_id)

    # check if we need to kick off the revocation registry setup
    meta_data = event.payload
    support_revocation = meta_data["context"]["support_revocation"]
    novel = meta_data["context"]["novel"]
    rev_reg_size = (
        meta_data["context"].get("rev_reg_size", None) if support_revocation else None
    )
    auto_create_rev_reg = meta_data["processing"].get("auto_create_rev_reg", False)
    create_pending_rev_reg = meta_data["processing"].get(
        "create_pending_rev_reg", False
    )
    endorser_connection_id = (
        meta_data["endorser"].get("connection_id", None)
        if "endorser" in meta_data
        else None
    )
    if support_revocation and novel and auto_create_rev_reg:
        # this kicks off the revocation registry creation process, which is 3 steps:
        # 1 - create revocation registry (ledger transaction may require endorsement)
        # 2 - upload tails file
        # 3 - create revocation entry (ledger transaction may require endorsement)
        # For a cred def we also automatically create a second "pending" revocation
        # registry, so when the first one fills up we can continue to issue credentials
        # without a delay
        revoc = IndyRevocation(profile)
        await revoc.init_issuer_registry(
            cred_def_id,
            rev_reg_size,
            create_pending_rev_reg=create_pending_rev_reg,
            endorser_connection_id=endorser_connection_id,
        )


async def add_cred_def_non_secrets_record(
    profile: Profile, schema_id: str, issuer_did: str, credential_definition_id: str
):
    """
    Write the wallet non-secrets record for cred def (already written to the ledger).

    Note that the cred def private key signing informtion must already exist in the
    wallet.

    Args:
        schema_id: The schema id (or stringified sequence number)
        issuer_did: The DID of the issuer
        credential_definition_id: The credential definition id

    """
    schema_id_parts = schema_id.split(":")
    cred_def_tags = {
        "schema_id": schema_id,
        "schema_issuer_did": schema_id_parts[0],
        "schema_name": schema_id_parts[-2],
        "schema_version": schema_id_parts[-1],
        "issuer_did": issuer_did,
        "cred_def_id": credential_definition_id,
        "epoch": str(int(time())),
    }
    record = StorageRecord(
        CRED_DEF_SENT_RECORD_TYPE, credential_definition_id, cred_def_tags
    )
    async with profile.session() as session:
        storage = session.inject(BaseStorage)
        await storage.add_record(record)


async def register(app: web.Application):
    """Register routes."""
    app.add_routes(
        [
            web.post(
                "/credential-definitions",
                credential_definitions_send_credential_definition,
            ),
            web.get(
                "/credential-definitions/created",
                credential_definitions_created,
                allow_head=False,
            ),
            web.get(
                "/credential-definitions/{cred_def_id}",
                credential_definitions_get_credential_definition,
                allow_head=False,
            ),
            web.post(
                "/credential-definitions/{cred_def_id}/write_record",
                credential_definitions_fix_cred_def_wallet_record,
            ),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "credential-definition",
            "description": "Credential definition operations",
            "externalDocs": {
                "description": "Specification",
                "url": (
                    "https://github.com/hyperledger/indy-node/blob/master/"
                    "design/anoncreds.md#cred_def"
                ),
            },
        }
    )
