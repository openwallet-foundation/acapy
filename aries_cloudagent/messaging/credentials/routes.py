"""Connection handling admin routes."""

import asyncio
import json

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow import fields, Schema

from ...holder.base import BaseHolder
from ...storage.error import StorageNotFoundError
from ...wallet.error import WalletNotFoundError

from ..connections.models.connection_record import ConnectionRecord

from .manager import CredentialManager
from .models.credential_exchange import CredentialExchange, CredentialExchangeSchema


class CredentialSendRequestSchema(Schema):
    """Request schema for sending a credential offer admin message."""

    connection_id = fields.Str(required=True)
    credential_definition_id = fields.Str(required=True)
    credential_values = fields.Dict(required=False)


class CredentialSendResultSchema(Schema):
    """Result schema for sending a credential offer admin message."""

    credential_id = fields.Str()


class CredentialOfferRequestSchema(Schema):
    """Request schema for sending a credential offer admin message."""

    connection_id = fields.Str(required=True)
    credential_definition_id = fields.Str(required=True)


class CredentialOfferResultSchema(Schema):
    """Result schema for sending a credential offer admin message."""

    credential_id = fields.Str()


class CredentialRequestResultSchema(Schema):
    """Result schema for sending a credential request admin message."""

    credential_id = fields.Str()


class CredentialIssueRequestSchema(Schema):
    """Request schema for sending a credential issue admin message."""

    credential_values = fields.Dict(required=True)


class CredentialIssueResultSchema(Schema):
    """Result schema for sending a credential issue admin message."""

    credential_id = fields.Str()


class CredentialExchangeListSchema(Schema):
    """Result schema for a credential exchange query."""

    results = fields.List(fields.Nested(CredentialExchangeSchema()))


class CredentialSchema(Schema):
    """Result schema for a credential query."""

    # properties undefined


class CredentialListSchema(Schema):
    """Result schema for a credential query."""

    results = fields.List(fields.Nested(CredentialSchema()))


@docs(tags=["credentials"], summary="Fetch a credential from wallet by id")
@response_schema(CredentialSchema(), 200)
async def credentials_get(request: web.BaseRequest):
    """
    Request handler for retrieving a credential.

    Args:
        request: aiohttp request object

    Returns:
        The credential response

    """
    context = request.app["request_context"]

    credential_id = request.match_info["id"]

    holder: BaseHolder = await context.inject(BaseHolder)
    try:
        credential = await holder.get_credential(credential_id)
    except WalletNotFoundError:
        raise web.HTTPNotFound()

    return web.json_response(credential)


@docs(tags=["credentials"], summary="Remove a credential from the wallet by id")
async def credentials_remove(request: web.BaseRequest):
    """
    Request handler for searching connection records.

    Args:
        request: aiohttp request object

    Returns:
        The connection list response

    """
    context = request.app["request_context"]

    credential_id = request.match_info["id"]

    holder: BaseHolder = await context.inject(BaseHolder)
    try:
        await holder.delete_credential(credential_id)
    except WalletNotFoundError:
        raise web.HTTPNotFound()

    return web.json_response({})


@docs(
    tags=["credentials"],
    parameters=[
        {
            "name": "start",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
        {
            "name": "count",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
        {"name": "wql", "in": "query", "schema": {"type": "string"}, "required": False},
    ],
    summary="Fetch credentials from wallet",
)
@response_schema(CredentialListSchema(), 200)
async def credentials_list(request: web.BaseRequest):
    """
    Request handler for searching credential records.

    Args:
        request: aiohttp request object

    Returns:
        The credential list response

    """
    context = request.app["request_context"]

    start = request.query.get("start")
    count = request.query.get("count")

    # url encoded json wql
    encoded_wql = request.query.get("wql") or "{}"
    wql = json.loads(encoded_wql)

    # defaults
    start = int(start) if isinstance(start, str) else 0
    count = int(count) if isinstance(count, str) else 10

    holder: BaseHolder = await context.inject(BaseHolder)
    credentials = await holder.get_credentials(start, count, wql)

    return web.json_response({"results": credentials})


@docs(tags=["credential_exchange"], summary="Fetch all credential exchange records")
@response_schema(CredentialExchangeListSchema(), 200)
async def credential_exchange_list(request: web.BaseRequest):
    """
    Request handler for searching credential exchange records.

    Args:
        request: aiohttp request object

    Returns:
        The credential exchange list response

    """
    context = request.app["request_context"]
    tag_filter = {}
    for param_name in (
        "connection_id",
        "initiator",
        "state",
        "credential_definition_id",
        "schema_id",
    ):
        if param_name in request.query and request.query[param_name] != "":
            tag_filter[param_name] = request.query[param_name]
    records = await CredentialExchange.query(context, tag_filter)
    return web.json_response({"results": [record.serialize() for record in records]})


@docs(tags=["credential_exchange"], summary="Fetch a single credential exchange record")
@response_schema(CredentialExchangeSchema(), 200)
async def credential_exchange_retrieve(request: web.BaseRequest):
    """
    Request handler for fetching a single credential exchange record.

    Args:
        request: aiohttp request object

    Returns:
        The credential exchange record response

    """
    context = request.app["request_context"]
    credential_exchange_id = request.match_info["id"]
    try:
        record = await CredentialExchange.retrieve_by_id(
            context, credential_exchange_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound()
    return web.json_response(record.serialize())


@docs(
    tags=["credential_exchange"],
    summary="Sends a credential and automates the entire flow",
)
@request_schema(CredentialSendRequestSchema())
@response_schema(CredentialSendResultSchema(), 200)
async def credential_exchange_send(request: web.BaseRequest):
    """
    Request handler for sending a credential offer.

    Args:
        request: aiohttp request object

    Returns:
        The credential offer details.

    """

    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    body = await request.json()

    connection_id = body.get("connection_id")
    credential_definition_id = body.get("credential_definition_id")
    credential_values = body.get("credential_values")

    credential_manager = CredentialManager(context)

    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPBadRequest()

    if not connection_record.is_ready:
        raise web.HTTPForbidden()

    credential_exchange_record = await credential_manager.prepare_send(
        credential_definition_id, connection_id, credential_values
    )
    asyncio.ensure_future(
        credential_manager.perform_send(credential_exchange_record, outbound_handler)
    )

    return web.json_response(credential_exchange_record.serialize())


@docs(tags=["credential_exchange"], summary="Sends a credential offer")
@request_schema(CredentialOfferRequestSchema())
@response_schema(CredentialOfferResultSchema(), 200)
async def credential_exchange_send_offer(request: web.BaseRequest):
    """
    Request handler for sending a credential offer.

    Args:
        request: aiohttp request object

    Returns:
        The credential offer details.

    """

    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    body = await request.json()

    connection_id = body.get("connection_id")
    credential_definition_id = body.get("credential_definition_id")

    credential_manager = CredentialManager(context)

    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPBadRequest()

    if not connection_record.is_ready:
        raise web.HTTPForbidden()

    credential_exchange_record = await credential_manager.create_offer(
        credential_definition_id, connection_id
    )

    (
        credential_exchange_record,
        credential_offer_message,
    ) = await credential_manager.offer_credential(credential_exchange_record)
    await outbound_handler(credential_offer_message, connection_id=connection_id)

    return web.json_response(credential_exchange_record.serialize())


@docs(tags=["credential_exchange"], summary="Sends a credential request")
@response_schema(CredentialRequestResultSchema(), 200)
async def credential_exchange_send_request(request: web.BaseRequest):
    """
    Request handler for sending a credential request.

    Args:
        request: aiohttp request object

    Returns:
        The credential request details.

    """

    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    credential_exchange_id = request.match_info["id"]
    credential_exchange_record = await CredentialExchange.retrieve_by_id(
        context, credential_exchange_id
    )
    connection_id = credential_exchange_record.connection_id

    assert credential_exchange_record.state == CredentialExchange.STATE_OFFER_RECEIVED

    credential_manager = CredentialManager(context)

    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPBadRequest()

    if not connection_record.is_ready:
        raise web.HTTPForbidden()

    (
        credential_exchange_record,
        credential_request_message,
    ) = await credential_manager.create_request(
        credential_exchange_record, connection_record
    )

    await outbound_handler(credential_request_message, connection_id=connection_id)
    return web.json_response(credential_exchange_record.serialize())


@docs(tags=["credential_exchange"], summary="Sends a credential")
@request_schema(CredentialIssueRequestSchema())
@response_schema(CredentialIssueResultSchema(), 200)
async def credential_exchange_issue(request: web.BaseRequest):
    """
    Request handler for sending a credential.

    Args:
        request: aiohttp request object

    Returns:
        The credential details.

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    body = await request.json()
    credential_values = body["credential_values"]

    credential_exchange_id = request.match_info["id"]
    credential_exchange_record = await CredentialExchange.retrieve_by_id(
        context, credential_exchange_id
    )
    connection_id = credential_exchange_record.connection_id

    assert credential_exchange_record.state == CredentialExchange.STATE_REQUEST_RECEIVED

    credential_manager = CredentialManager(context)
    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPBadRequest()

    if not connection_record.is_ready:
        raise web.HTTPForbidden()

    credential_exchange_record.credential_values = credential_values
    (
        credential_exchange_record,
        credential_issue_message,
    ) = await credential_manager.issue_credential(credential_exchange_record)

    await outbound_handler(credential_issue_message, connection_id=connection_id)
    return web.json_response(credential_exchange_record.serialize())


@docs(
    tags=["credential_exchange"],
    summary="Remove an existing credential exchange record",
)
async def credential_exchange_remove(request: web.BaseRequest):
    """
    Request handler for removing a credential exchange record.

    Args:
        request: aiohttp request object
    """
    context = request.app["request_context"]
    credential_exchange_id = request.match_info["id"]
    try:
        credential_exchange_id = request.match_info["id"]
        credential_exchange_record = await CredentialExchange.retrieve_by_id(
            context, credential_exchange_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound()
    await credential_exchange_record.delete_record(context)
    return web.json_response({})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/credential/{id}", credentials_get),
            web.post("/credential/{id}/remove", credentials_remove),
            web.get("/credentials", credentials_list),
            web.get("/credential_exchange", credential_exchange_list),
            web.get("/credential_exchange/{id}", credential_exchange_retrieve),
            web.post("/credential_exchange/send", credential_exchange_send),
            web.post("/credential_exchange/send-offer", credential_exchange_send_offer),
            web.post(
                "/credential_exchange/{id}/send-request",
                credential_exchange_send_request,
            ),
            web.post("/credential_exchange/{id}/issue", credential_exchange_issue),
            web.post("/credential_exchange/{id}/remove", credential_exchange_remove),
        ]
    )
