"""Credential schema admin routes."""

import json
from time import time

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
from marshmallow.validate import Regexp

from ...admin.request_context import AdminRequestContext
from ...core.event_bus import Event, EventBus
from ...core.profile import Profile
from ...indy.issuer import IndyIssuer, IndyIssuerError
from ...indy.models.schema import SchemaSchema
from ...ledger.base import BaseLedger
from ...ledger.error import LedgerError
from ...ledger.multiple_ledger.ledger_requests_executor import (
    GET_SCHEMA,
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
from ...storage.base import BaseStorage, StorageRecord
from ...storage.error import StorageError

from ..models.openapi import OpenAPISchema
from ..valid import B58, INDY_SCHEMA_ID, INDY_VERSION

from .util import (
    SchemaQueryStringSchema,
    SCHEMA_SENT_RECORD_TYPE,
    SCHEMA_TAGS,
    EVENT_LISTENER_PATTERN,
    notify_schema_event,
)


from ..valid import UUIDFour
from ...connections.models.conn_record import ConnRecord
from ...storage.error import StorageNotFoundError
from ..models.base import BaseModelError


class SchemaSendRequestSchema(OpenAPISchema):
    """Request schema for schema send request."""

    schema_name = fields.Str(
        required=True,
        description="Schema name",
        example="prefs",
    )
    schema_version = fields.Str(
        required=True, description="Schema version", **INDY_VERSION
    )
    attributes = fields.List(
        fields.Str(
            description="attribute name",
            example="score",
        ),
        required=True,
        description="List of schema attributes",
    )


class SchemaSendResultSchema(OpenAPISchema):
    """Result schema content for schema send request with auto-endorse."""

    schema_id = fields.Str(
        description="Schema identifier", required=True, **INDY_SCHEMA_ID
    )
    schema = fields.Nested(
        SchemaSchema(),
        description="Schema definition",
    )


class TxnOrSchemaSendResultSchema(OpenAPISchema):
    """Result schema for schema send request."""

    sent = fields.Nested(
        SchemaSendResultSchema(),
        required=False,
        description="Content sent",
    )
    txn = fields.Nested(
        TransactionRecordSchema(),
        required=False,
        description="Schema transaction to endorse",
    )


class SchemaGetResultSchema(OpenAPISchema):
    """Result schema for schema get request."""

    schema = fields.Nested(SchemaSchema())


class SchemasCreatedResultSchema(OpenAPISchema):
    """Result schema for a schemas-created request."""

    schema_ids = fields.List(
        fields.Str(description="Schema identifiers", **INDY_SCHEMA_ID)
    )


class SchemaIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking schema id."""

    schema_id = fields.Str(
        description="Schema identifier",
        required=True,
        validate=Regexp(rf"^[1-9][0-9]*|[{B58}]{{21,22}}:2:.+:[0-9.]+$"),
        example=INDY_SCHEMA_ID["example"],
    )


class CreateSchemaTxnForEndorserOptionSchema(OpenAPISchema):
    """Class for user to input whether to create a transaction for endorser or not."""

    create_transaction_for_endorser = fields.Boolean(
        description="Create Transaction For Endorser's signature",
        required=False,
    )


class SchemaConnIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    conn_id = fields.Str(
        description="Connection identifier", required=False, example=UUIDFour.EXAMPLE
    )


@docs(tags=["schema"], summary="Sends a schema to the ledger")
@request_schema(SchemaSendRequestSchema())
@querystring_schema(CreateSchemaTxnForEndorserOptionSchema())
@querystring_schema(SchemaConnIdMatchInfoSchema())
@response_schema(TxnOrSchemaSendResultSchema(), 200, description="")
async def schemas_send_schema(request: web.BaseRequest):
    """
    Request handler for creating a schema.

    Args:
        request: aiohttp request object

    Returns:
        The schema id sent

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

    schema_name = body.get("schema_name")
    schema_version = body.get("schema_version")
    attributes = body.get("attributes")

    tag_query = {"schema_name": schema_name, "schema_version": schema_version}
    async with profile.session() as session:
        storage = session.inject(BaseStorage)
        found = await storage.find_all_records(
            type_filter=SCHEMA_SENT_RECORD_TYPE,
            tag_query=tag_query,
        )
        if 0 < len(found):
            raise web.HTTPBadRequest(
                reason=f"Schema {schema_name} {schema_version} already exists"
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
    async with ledger:
        try:
            # if create_transaction_for_endorser, then the returned "schema_def"
            # is actually the signed transaction
            schema_id, schema_def = await shield(
                ledger.create_and_send_schema(
                    issuer,
                    schema_name,
                    schema_version,
                    attributes,
                    write_ledger=write_ledger,
                    endorser_did=endorser_did,
                )
            )
        except (IndyIssuerError, LedgerError) as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    meta_data = {
        "context": {
            "schema_id": schema_id,
            "schema_name": schema_name,
            "schema_version": schema_version,
            "attributes": attributes,
        },
        "processing": {},
    }

    if not create_transaction_for_endorser:
        # Notify event
        await notify_schema_event(context.profile, schema_id, meta_data)
        return web.json_response(
            {
                "sent": {"schema_id": schema_id, "schema": schema_def},
                "schema_id": schema_id,
                "schema": schema_def,
            }
        )

    # If the transaction is for the endorser, but the schema has already been created,
    # then we send back the schema since the transaction will fail to be created.
    elif "signed_txn" not in schema_def:
        return web.json_response(
            {"sent": {"schema_id": schema_id, "schema": schema_def}}
        )
    else:
        transaction_mgr = TransactionManager(context.profile)
        try:
            transaction = await transaction_mgr.create_record(
                messages_attach=schema_def["signed_txn"],
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
                "sent": {"schema_id": schema_id, "schema": schema_def},
                "txn": transaction.serialize(),
            }
        )


@docs(
    tags=["schema"],
    summary="Search for matching schema that agent originated",
)
@querystring_schema(SchemaQueryStringSchema())
@response_schema(SchemasCreatedResultSchema(), 200, description="")
async def schemas_created(request: web.BaseRequest):
    """
    Request handler for retrieving schemas that current agent created.

    Args:
        request: aiohttp request object

    Returns:
        The identifiers of matching schemas

    """
    context: AdminRequestContext = request["context"]

    session = await context.session()
    storage = session.inject(BaseStorage)
    found = await storage.find_all_records(
        type_filter=SCHEMA_SENT_RECORD_TYPE,
        tag_query={
            tag: request.query[tag] for tag in SCHEMA_TAGS if tag in request.query
        },
    )

    return web.json_response({"schema_ids": [record.value for record in found]})


@docs(tags=["schema"], summary="Gets a schema from the ledger")
@match_info_schema(SchemaIdMatchInfoSchema())
@response_schema(SchemaGetResultSchema(), 200, description="")
async def schemas_get_schema(request: web.BaseRequest):
    """
    Request handler for sending a credential offer.

    Args:
        request: aiohttp request object

    Returns:
        The schema details.

    """
    context: AdminRequestContext = request["context"]
    schema_id = request.match_info["schema_id"]

    async with context.profile.session() as session:
        multitenant_mgr = session.inject_or(BaseMultitenantManager)
        if multitenant_mgr:
            ledger_exec_inst = IndyLedgerRequestsExecutor(context.profile)
        else:
            ledger_exec_inst = session.inject(IndyLedgerRequestsExecutor)
    ledger_id, ledger = await ledger_exec_inst.get_ledger_for_identifier(
        schema_id,
        txn_record_type=GET_SCHEMA,
    )
    if not ledger:
        reason = "No ledger available"
        if not context.settings.get_value("wallet.type"):
            reason += ": missing wallet-type?"
        raise web.HTTPForbidden(reason=reason)

    async with ledger:
        try:
            schema = await ledger.get_schema(schema_id)
        except LedgerError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    if ledger_id:
        return web.json_response({"ledger_id": ledger_id, "schema": schema})
    else:
        return web.json_response({"schema": schema})


@docs(tags=["schema"], summary="Writes a schema non-secret record to the wallet")
@match_info_schema(SchemaIdMatchInfoSchema())
@response_schema(SchemaGetResultSchema(), 200, description="")
async def schemas_fix_schema_wallet_record(request: web.BaseRequest):
    """
    Request handler for fixing a schema's wallet non-secrets records.

    Args:
        request: aiohttp request object

    Returns:
        The schema details.

    """
    context: AdminRequestContext = request["context"]

    profile = context.profile

    schema_id = request.match_info["schema_id"]

    async with profile.session() as session:
        storage = session.inject(BaseStorage)
        multitenant_mgr = session.inject_or(BaseMultitenantManager)
        if multitenant_mgr:
            ledger_exec_inst = IndyLedgerRequestsExecutor(context.profile)
        else:
            ledger_exec_inst = session.inject(IndyLedgerRequestsExecutor)
    ledger_id, ledger = await ledger_exec_inst.get_ledger_for_identifier(
        schema_id,
        txn_record_type=GET_SCHEMA,
    )
    if not ledger:
        reason = "No ledger available"
        if not context.settings.get_value("wallet.type"):
            reason += ": missing wallet-type?"
        raise web.HTTPForbidden(reason=reason)

    async with ledger:
        try:
            schema = await ledger.get_schema(schema_id)

            # check if the record exists, if not add it
            found = await storage.find_all_records(
                type_filter=SCHEMA_SENT_RECORD_TYPE,
                tag_query={
                    "schema_id": schema_id,
                },
            )
            if 0 == len(found):
                await add_schema_non_secrets_record(profile, schema_id)
        except LedgerError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    if ledger_id:
        return web.json_response({"ledger_id": ledger_id, "schema": schema})
    else:
        return web.json_response({"schema": schema})


def register_events(event_bus: EventBus):
    """Subscribe to any events we need to support."""
    event_bus.subscribe(EVENT_LISTENER_PATTERN, on_schema_event)


async def on_schema_event(profile: Profile, event: Event):
    """Handle any events we need to support."""
    schema_id = event.payload["context"]["schema_id"]

    # after the ledger record is written, write the wallet non-secrets record
    await add_schema_non_secrets_record(profile, schema_id)


async def add_schema_non_secrets_record(profile: Profile, schema_id: str):
    """
    Write the wallet non-secrets record for a schema (already written to the ledger).

    Args:
        profile: the current profile (used to determine storage)
        schema_id: The schema id (or stringified sequence number)

    """
    schema_id_parts = schema_id.split(":")
    schema_tags = {
        "schema_id": schema_id,
        "schema_issuer_did": schema_id_parts[0],
        "schema_name": schema_id_parts[-2],
        "schema_version": schema_id_parts[-1],
        "epoch": str(int(time())),
    }
    record = StorageRecord(SCHEMA_SENT_RECORD_TYPE, schema_id, schema_tags)
    async with profile.session() as session:
        storage = session.inject(BaseStorage)
        await storage.add_record(record)


async def register(app: web.Application):
    """Register routes."""
    app.add_routes(
        [
            web.post("/schemas", schemas_send_schema),
            web.get("/schemas/created", schemas_created, allow_head=False),
            web.get("/schemas/{schema_id}", schemas_get_schema, allow_head=False),
            web.post(
                "/schemas/{schema_id}/write_record", schemas_fix_schema_wallet_record
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
            "name": "schema",
            "description": "Schema operations",
            "externalDocs": {
                "description": "Specification",
                "url": (
                    "https://github.com/hyperledger/indy-node/blob/master/"
                    "design/anoncreds.md#schema"
                ),
            },
        }
    )
