"""Endorse Transaction handling admin routes."""

from aiohttp import web
from aiohttp_apispec import (
    request_schema,
    docs,
    response_schema,
    querystring_schema,
    match_info_schema,
)
from marshmallow import fields

from ....admin.request_context import AdminRequestContext
from ....utils.tracing import AdminAPIMessageTracingSchema
from .manager import TransactionManager
from .models.transaction_record import TransactionRecord, TransactionRecordSchema
from ....connections.models.conn_record import ConnRecord

from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import UUIDFour
from ....messaging.models.base import BaseModelError

from ....storage.error import StorageError, StorageNotFoundError


class TransactionListSchema(OpenAPISchema):
    """Result schema for transaction list."""

    results = fields.List(
        fields.Nested(TransactionRecordSchema()),
        description="List of transaction records",
    )


class TransactionsListQueryStringSchema(OpenAPISchema):
    """Parameters and validators for transactions list request query string."""


class TranIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking transaction id."""

    tran_id = fields.Str(
        description="Transaction identifier", required=True, example=UUIDFour.EXAMPLE
    )


class CreateTransactionRecordSchema(AdminAPIMessageTracingSchema):
    """Parameters and validators to create transaction request and record."""

    conn_id = fields.Str(
        description="Connection identifier", required=True, example=UUIDFour.EXAMPLE
    )
    transaction_message = fields.Dict(
        required=False,
        example={
            "attr_names": ["first_name", "last_name"],
            "name": "test_schema",
            "version": "2.1",
        },
    )


@docs(
    tags=["endorse-transaction"],
    summary="Query transactions",
)
@querystring_schema(TransactionsListQueryStringSchema())
@response_schema(TransactionListSchema(), 200)
async def transactions_list(request: web.BaseRequest):
    """
    Request handler for searching transaction records.

    Args:
        request: aiohttp request object

    Returns:
        The transaction list response

    """

    context: AdminRequestContext = request["context"]

    tag_filter = {}
    post_filter = {}

    try:
        async with context.session() as session:
            records = await TransactionRecord.query(
                session, tag_filter, post_filter_positive=post_filter, alt=True
            )
        results = [record.serialize() for record in records]
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"results": results})


@docs(tags=["endorse-transaction"], summary="Fetch a single transaction record")
@match_info_schema(TranIdMatchInfoSchema())
@response_schema(TransactionRecordSchema(), 200)
async def transactions_retrieve(request: web.BaseRequest):
    """
    Request handler for fetching a single transaction record.

    Args:
        request: aiohttp request object

    Returns:
        The transaction record response

    """

    context: AdminRequestContext = request["context"]
    transaction_id = request.match_info["tran_id"]

    try:
        async with context.session() as session:
            record = await TransactionRecord.retrieve_by_id(session, transaction_id)
        result = record.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    return web.json_response(result)


@docs(
    tags=["endorse-transaction"],
    summary="For author to send a transaction request",
)
@request_schema(CreateTransactionRecordSchema())
@response_schema(TransactionRecordSchema(), 200)
async def transaction_record_create(request: web.BaseRequest):
    """
    Request handler for creating a new transaction record and request.

    Args:
        request: aiohttp request object

    Returns:
        The transaction record

    """

    context: AdminRequestContext = request["context"]
    outbound_handler = request.app["outbound_message_router"]

    body = await request.json()

    connection_id = body.get("conn_id")
    transaction_message = body.get("transaction_message")

    try:
        async with context.session() as session:
            connection = await ConnRecord.retrieve_by_id(session, connection_id)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    session = await context.session()
    transaction_mgr = TransactionManager(session, context.profile)
    (transaction, transaction_request) = await transaction_mgr.create_request(
        connection_id=connection_id,
        transaction_message=transaction_message,
    )

    await outbound_handler(transaction_request, connection_id=connection.connection_id)

    return web.json_response(transaction.serialize())


@docs(
    tags=["endorse-transaction"],
    summary="For Endorser to endorse a particular transaction record",
)
@match_info_schema(TranIdMatchInfoSchema())
@response_schema(TransactionRecordSchema(), 200)
async def endorse_transaction_response(request: web.BaseRequest):
    """
    Request handler for creating an endorsed transaction response.

    Args:
        request: aiohttp request object

    Returns:
        The updated transaction record details

    """

    context: AdminRequestContext = request["context"]
    outbound_handler = request.app["outbound_message_router"]

    transaction_id = request.match_info["tran_id"]
    try:
        async with context.session() as session:
            transaction = await TransactionRecord.retrieve_by_id(
                session, transaction_id
            )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    if transaction.state == "request" or transaction.state == "resend":

        session = await context.session()
        transaction_mgr = TransactionManager(session, context.profile)
        (
            transaction,
            endorsed_transaction_response,
        ) = await transaction_mgr.create_endorse_response(
            transaction=transaction, state="endorsed"
        )

        await outbound_handler(
            endorsed_transaction_response, connection_id=transaction.connection_id
        )

        return web.json_response(transaction.serialize())

    else:
        return web.json_response({"error": "You cannot endorse this transaction"})


@docs(
    tags=["endorse-transaction"],
    summary="For Endorser to refuse a particular transaction record",
)
@match_info_schema(TranIdMatchInfoSchema())
@response_schema(TransactionRecordSchema(), 200)
async def refuse_transaction_response(request: web.BaseRequest):
    """
    Request handler for creating a refused transaction response.

    Args:
        request: aiohttp request object

    Returns:
        The updated transaction record details

    """

    context: AdminRequestContext = request["context"]
    outbound_handler = request.app["outbound_message_router"]

    transaction_id = request.match_info["tran_id"]
    try:
        async with context.session() as session:
            transaction = await TransactionRecord.retrieve_by_id(
                session, transaction_id
            )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    if transaction.state == "request" or transaction.state == "resend":

        session = await context.session()
        transaction_mgr = TransactionManager(session, context.profile)
        (
            transaction,
            refused_transaction_response,
        ) = await transaction_mgr.create_refuse_response(
            transaction=transaction, state="refused"
        )

        await outbound_handler(
            refused_transaction_response, connection_id=transaction.connection_id
        )

        return web.json_response(transaction.serialize())

    else:
        return web.json_response({"error": "You cannot refuse the transaction"})


@docs(
    tags=["endorse-transaction"],
    summary="For Author to cancel a particular transaction request",
)
@match_info_schema(TranIdMatchInfoSchema())
@response_schema(TransactionRecordSchema(), 200)
async def cancel_transaction(request: web.BaseRequest):
    """
    Request handler for cancelling a Transaction request.

    Args:
        request: aiohttp request object

    Returns:
        The updated transaction record details

    """

    context: AdminRequestContext = request["context"]
    outbound_handler = request.app["outbound_message_router"]

    transaction_id = request.match_info["tran_id"]
    try:
        async with context.session() as session:
            transaction = await TransactionRecord.retrieve_by_id(
                session, transaction_id
            )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    if transaction.state != "endorsed" and transaction.state != "refused":

        session = await context.session()
        transaction_mgr = TransactionManager(session, context.profile)
        (
            transaction,
            cancelled_transaction_response,
        ) = await transaction_mgr.cancel_transaction(
            transaction=transaction, state="cancelled"
        )

        await outbound_handler(
            cancelled_transaction_response, connection_id=transaction.connection_id
        )

        return web.json_response(transaction.serialize())

    else:
        return web.json_response({"error": "This transaction cannot be cancelled"})


@docs(
    tags=["endorse-transaction"],
    summary="For Author to resend a particular transaction request",
)
@match_info_schema(TranIdMatchInfoSchema())
@response_schema(TransactionRecordSchema(), 200)
async def transaction_resend(request: web.BaseRequest):
    """
    Request handler for resending a transaction request.

    Args:
        request: aiohttp request object

    Returns:
        The updated transaction record details

    """

    context: AdminRequestContext = request["context"]
    outbound_handler = request.app["outbound_message_router"]

    transaction_id = request.match_info["tran_id"]
    try:
        async with context.session() as session:
            transaction = await TransactionRecord.retrieve_by_id(
                session, transaction_id
            )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    if transaction.state != "endorsed":

        session = await context.session()
        transaction_mgr = TransactionManager(session, context.profile)
        (
            transaction,
            resend_transaction_response,
        ) = await transaction_mgr.transaction_resend(
            transaction=transaction, state="resend"
        )

        await outbound_handler(
            resend_transaction_response, connection_id=transaction.connection_id
        )

        return web.json_response(transaction.serialize())

    else:
        return web.json_response({"error": "You cannot resend an endorsed transaction"})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/transactions", transactions_list, allow_head=False),
            web.get("/transactions/{tran_id}", transactions_retrieve, allow_head=False),
            web.post("/transactions/create-request", transaction_record_create),
            web.post("/transactions/{tran_id}/endorse", endorse_transaction_response),
            web.post("/transactions/{tran_id}/refuse", refuse_transaction_response),
            web.post("/transactions/{tran_id}/cancel", cancel_transaction),
            web.post("/transaction/{tran_id}/resend", transaction_resend),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "endorse-transaction",
            "description": "Endorse a Transaction",
        }
    )
