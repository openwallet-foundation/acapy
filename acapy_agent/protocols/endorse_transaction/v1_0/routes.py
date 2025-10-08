"""Endorse Transaction handling admin routes."""

import logging

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)
from marshmallow import fields, validate

from ....admin.decorators.auth import tenant_authentication
from ....admin.request_context import AdminRequestContext
from ....connections.models.conn_record import ConnRecord
from ....core.event_bus import Event, EventBus
from ....core.profile import Profile
from ....core.util import SHUTDOWN_EVENT_PATTERN, STARTUP_EVENT_PATTERN
from ....indy.issuer import IndyIssuerError
from ....ledger.error import LedgerError
from ....messaging.models.base import BaseModelError
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import UUID4_EXAMPLE
from ....storage.error import StorageError, StorageNotFoundError
from ....utils.endorsement_setup import attempt_auto_author_with_endorser_setup
from .manager import TransactionManager, TransactionManagerError
from .models.transaction_record import TransactionRecord, TransactionRecordSchema
from .transaction_jobs import TransactionJob

LOGGER = logging.getLogger(__name__)


class TransactionListSchema(OpenAPISchema):
    """Result schema for transaction list."""

    results = fields.List(
        fields.Nested(TransactionRecordSchema()),
        metadata={"description": "List of transaction records"},
    )


class TransactionsListQueryStringSchema(OpenAPISchema):
    """Parameters and validators for transactions list request query string."""


class TranIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking transaction id."""

    tran_id = fields.Str(
        required=True,
        metadata={"description": "Transaction identifier", "example": UUID4_EXAMPLE},
    )


class EndorserDIDInfoSchema(OpenAPISchema):
    """Path parameters and validators for request Endorser DID."""

    endorser_did = fields.Str(required=False, metadata={"description": "Endorser DID"})


class AssignTransactionJobsSchema(OpenAPISchema):
    """Assign transaction related jobs to connection record."""

    transaction_my_job = fields.Str(
        required=False,
        validate=validate.OneOf(
            [r.name for r in TransactionJob if isinstance(r.value[0], int)] + ["reset"]
        ),
        metadata={"description": "Transaction related jobs"},
    )


class TransactionJobsSchema(OpenAPISchema):
    """Transaction jobs metadata on connection record."""

    transaction_my_job = fields.Str(
        required=False,
        validate=validate.OneOf(
            [r.name for r in TransactionJob if isinstance(r.value[0], int)] + ["reset"]
        ),
        metadata={"description": "My transaction related job"},
    )
    transaction_their_job = fields.Str(
        required=False,
        validate=validate.OneOf(
            [r.name for r in TransactionJob if isinstance(r.value[0], int)] + ["reset"]
        ),
        metadata={"description": "Their transaction related job"},
    )


class TransactionConnIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    conn_id = fields.Str(
        required=True,
        metadata={"description": "Connection identifier", "example": UUID4_EXAMPLE},
    )


class DateSchema(OpenAPISchema):
    """Sets Expiry date, till when the transaction should be endorsed."""

    expires_time = fields.DateTime(
        required=True,
        metadata={"description": "Expiry Date", "example": "2021-03-29T05:22:19Z"},
    )


class EndorserInfoSchema(OpenAPISchema):
    """Class for user to input the DID associated with the requested endorser."""

    endorser_did = fields.Str(required=True, metadata={"description": "Endorser DID"})

    endorser_name = fields.Str(required=False, metadata={"description": "Endorser Name"})


@docs(
    tags=["endorse-transaction"],
    summary="Query transactions",
)
@querystring_schema(TransactionsListQueryStringSchema())
@response_schema(TransactionListSchema(), 200)
@tenant_authentication
async def transactions_list(request: web.BaseRequest):
    """Request handler for searching transaction records.

    Args:
        request: aiohttp request object
    Returns:
        The transaction list response

    """
    context: AdminRequestContext = request["context"]

    tag_filter = {}
    post_filter = {}

    try:
        async with context.profile.session() as session:
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
@tenant_authentication
async def transactions_retrieve(request: web.BaseRequest):
    """Request handler for fetching a single transaction record.

    Args:
        request: aiohttp request object
    Returns:
        The transaction record response

    """
    context: AdminRequestContext = request["context"]
    transaction_id = request.match_info["tran_id"]

    try:
        async with context.profile.session() as session:
            record = await TransactionRecord.retrieve_by_id(session, transaction_id)
        result = record.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except BaseModelError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(result)


# todo - implementing changes for writing final transaction to the ledger
# (For Sign Transaction Protocol)
@docs(
    tags=["endorse-transaction"],
    summary="For author to send a transaction request",
)
@querystring_schema(TranIdMatchInfoSchema())
@request_schema(DateSchema())
@response_schema(TransactionRecordSchema(), 200)
@tenant_authentication
async def transaction_create_request(request: web.BaseRequest):
    """Request handler for creating a new transaction record and request.

    Args:
        request: aiohttp request object
    Returns:
        The transaction record

    """
    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]
    transaction_id = request.query.get("tran_id")
    endorser_write_txn = False

    body = await request.json()
    expires_time = body.get("expires_time")

    try:
        async with context.profile.session() as session:
            transaction_record = await TransactionRecord.retrieve_by_id(
                session, transaction_id
            )
            connection_record = await ConnRecord.retrieve_by_id(
                session, transaction_record.connection_id
            )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except BaseModelError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    async with context.profile.session() as session:
        jobs = await connection_record.metadata_get(session, "transaction_jobs")
    if not jobs:
        raise web.HTTPForbidden(
            reason=(
                "The transaction related jobs are not set up in "
                "connection metadata for this connection record"
            )
        )
    if "transaction_my_job" not in jobs.keys():
        raise web.HTTPForbidden(
            reason=(
                'The "transaction_my_job" is not set in "transaction_jobs" '
                "connection metadata for this connection record"
            )
        )
    if "transaction_their_job" not in jobs.keys():
        raise web.HTTPForbidden(
            reason=(
                'Ask the other agent to set up "transaction_my_job" in '
                '"transaction_jobs" in connection metadata for their connection record'
            )
        )
    if jobs["transaction_my_job"] != TransactionJob.TRANSACTION_AUTHOR.name:
        raise web.HTTPForbidden(reason="Only a TRANSACTION_AUTHOR can create a request")

    if jobs["transaction_their_job"] != TransactionJob.TRANSACTION_ENDORSER.name:
        raise web.HTTPForbidden(
            reason="A request can only be created to a TRANSACTION_ENDORSER"
        )

    transaction_mgr = TransactionManager(context.profile)
    try:
        (
            transaction_record,
            transaction_request,
        ) = await transaction_mgr.create_request(
            transaction=transaction_record,
            expires_time=expires_time,
            endorser_write_txn=endorser_write_txn,
        )
    except (StorageError, TransactionManagerError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(
        transaction_request, connection_id=connection_record.connection_id
    )

    return web.json_response(transaction_record.serialize())


# todo - implementing changes for writing final transaction to the ledger
# (For Sign Transaction Protocol)
@docs(
    tags=["endorse-transaction"],
    summary="For Endorser to endorse a particular transaction record",
)
@querystring_schema(EndorserDIDInfoSchema())
@match_info_schema(TranIdMatchInfoSchema())
@response_schema(TransactionRecordSchema(), 200)
@tenant_authentication
async def endorse_transaction_response(request: web.BaseRequest):
    """Request handler for creating an endorsed transaction response.

    Args:
        request: aiohttp request object
    Returns:
        The updated transaction record details

    """
    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]

    transaction_id = request.match_info["tran_id"]
    endorser_did = request.query.get("endorser_did")
    try:
        async with context.profile.session() as session:
            transaction = await TransactionRecord.retrieve_by_id(session, transaction_id)
            connection_record = await ConnRecord.retrieve_by_id(
                session, transaction.connection_id
            )
            # provided DID is validated in the TransactionManager

    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except BaseModelError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    async with context.profile.session() as session:
        jobs = await connection_record.metadata_get(session, "transaction_jobs")
    if not jobs:
        raise web.HTTPForbidden(
            reason=(
                "The transaction related jobs are not set up in "
                "connection metadata for this connection record"
            )
        )
    if jobs["transaction_my_job"] != TransactionJob.TRANSACTION_ENDORSER.name:
        raise web.HTTPForbidden(
            reason="Only a TRANSACTION_ENDORSER can endorse a transaction"
        )

    transaction_mgr = TransactionManager(context.profile)
    try:
        (
            transaction,
            endorsed_transaction_response,
        ) = await transaction_mgr.create_endorse_response(
            transaction=transaction,
            state=TransactionRecord.STATE_TRANSACTION_ENDORSED,
            use_endorser_did=endorser_did,
        )
    except (IndyIssuerError, LedgerError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    except (StorageError, TransactionManagerError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(
        endorsed_transaction_response, connection_id=transaction.connection_id
    )

    return web.json_response(transaction.serialize())


@docs(
    tags=["endorse-transaction"],
    summary="For Endorser to refuse a particular transaction record",
)
@match_info_schema(TranIdMatchInfoSchema())
@response_schema(TransactionRecordSchema(), 200)
@tenant_authentication
async def refuse_transaction_response(request: web.BaseRequest):
    """Request handler for creating a refused transaction response.

    Args:
        request: aiohttp request object
    Returns:
        The updated transaction record details

    """
    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]

    transaction_id = request.match_info["tran_id"]
    try:
        async with context.profile.session() as session:
            transaction = await TransactionRecord.retrieve_by_id(session, transaction_id)
            connection_record = await ConnRecord.retrieve_by_id(
                session, transaction.connection_id
            )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except BaseModelError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    async with context.profile.session() as session:
        jobs = await connection_record.metadata_get(session, "transaction_jobs")
    if not jobs:
        raise web.HTTPForbidden(
            reason=(
                "The transaction related jobs are not set up in "
                "connection metadata for this connection record"
            )
        )
    if jobs["transaction_my_job"] != TransactionJob.TRANSACTION_ENDORSER.name:
        raise web.HTTPForbidden(
            reason="Only a TRANSACTION_ENDORSER can refuse a transaction"
        )

    try:
        transaction_mgr = TransactionManager(context.profile)
        (
            transaction,
            refused_transaction_response,
        ) = await transaction_mgr.create_refuse_response(
            transaction=transaction,
            state=TransactionRecord.STATE_TRANSACTION_REFUSED,
            refuser_did=None,
        )
    except (StorageError, TransactionManagerError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(
        refused_transaction_response, connection_id=transaction.connection_id
    )

    return web.json_response(transaction.serialize())


@docs(
    tags=["endorse-transaction"],
    summary="For Author to cancel a particular transaction request",
)
@match_info_schema(TranIdMatchInfoSchema())
@response_schema(TransactionRecordSchema(), 200)
@tenant_authentication
async def cancel_transaction(request: web.BaseRequest):
    """Request handler for cancelling a Transaction request.

    Args:
        request: aiohttp request object
    Returns:
        The updated transaction record details

    """
    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]
    transaction_id = request.match_info["tran_id"]
    try:
        async with context.profile.session() as session:
            transaction = await TransactionRecord.retrieve_by_id(session, transaction_id)
            connection_record = await ConnRecord.retrieve_by_id(
                session, transaction.connection_id
            )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except BaseModelError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    async with context.profile.session() as session:
        jobs = await connection_record.metadata_get(session, "transaction_jobs")
    if not jobs:
        raise web.HTTPForbidden(
            reason=(
                "The transaction related jobs are not set up in "
                "connection metadata for this connection record"
            )
        )
    if jobs["transaction_my_job"] != TransactionJob.TRANSACTION_AUTHOR.name:
        raise web.HTTPForbidden(
            reason="Only a TRANSACTION_AUTHOR can cancel a transaction"
        )

    transaction_mgr = TransactionManager(context.profile)
    try:
        (
            transaction,
            cancelled_transaction_response,
        ) = await transaction_mgr.cancel_transaction(
            transaction=transaction,
            state=TransactionRecord.STATE_TRANSACTION_CANCELLED,
        )
    except (StorageError, TransactionManagerError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(
        cancelled_transaction_response, connection_id=transaction.connection_id
    )

    return web.json_response(transaction.serialize())


@docs(
    tags=["endorse-transaction"],
    summary="For Author to resend a particular transaction request",
)
@match_info_schema(TranIdMatchInfoSchema())
@response_schema(TransactionRecordSchema(), 200)
@tenant_authentication
async def transaction_resend(request: web.BaseRequest):
    """Request handler for resending a transaction request.

    Args:
        request: aiohttp request object
    Returns:
        The updated transaction record details

    """
    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]
    transaction_id = request.match_info["tran_id"]
    try:
        async with context.profile.session() as session:
            transaction = await TransactionRecord.retrieve_by_id(session, transaction_id)
            connection_record = await ConnRecord.retrieve_by_id(
                session, transaction.connection_id
            )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except BaseModelError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    async with context.profile.session() as session:
        jobs = await connection_record.metadata_get(session, "transaction_jobs")
    if not jobs:
        raise web.HTTPForbidden(
            reason=(
                "The transaction related jobs are not set up in "
                "connection metadata for this connection record"
            )
        )
    if jobs["transaction_my_job"] != TransactionJob.TRANSACTION_AUTHOR.name:
        raise web.HTTPForbidden(
            reason="Only a TRANSACTION_AUTHOR can resend a transaction"
        )

    try:
        transaction_mgr = TransactionManager(context.profile)
        (
            transaction,
            resend_transaction_response,
        ) = await transaction_mgr.transaction_resend(
            transaction=transaction, state=TransactionRecord.STATE_TRANSACTION_RESENT
        )
    except (StorageError, TransactionManagerError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(
        resend_transaction_response, connection_id=transaction.connection_id
    )

    return web.json_response(transaction.serialize())


@docs(
    tags=["endorse-transaction"],
    summary="Set transaction jobs",
)
@querystring_schema(AssignTransactionJobsSchema())
@match_info_schema(TransactionConnIdMatchInfoSchema())
@response_schema(TransactionJobsSchema(), 200)
@tenant_authentication
async def set_endorser_role(request: web.BaseRequest):
    """Request handler for assigning transaction jobs.

    Args:
        request: aiohttp request object
    Returns:
        The assigned transaction jobs

    """
    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]
    connection_id = request.match_info["conn_id"]
    transaction_my_job = request.query.get("transaction_my_job")

    async with context.profile.session() as session:
        try:
            record = await ConnRecord.retrieve_by_id(session, connection_id)
        except StorageNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err
        except BaseModelError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    transaction_mgr = TransactionManager(context.profile)
    tx_job_to_send = await transaction_mgr.set_transaction_my_job(
        record=record, transaction_my_job=transaction_my_job
    )
    async with context.profile.session() as session:
        jobs = await record.metadata_get(session, "transaction_jobs")

    await outbound_handler(tx_job_to_send, connection_id=connection_id)
    return web.json_response(jobs)


@docs(
    tags=["endorse-transaction"],
    summary="Set Endorser Info",
)
@querystring_schema(EndorserInfoSchema())
@match_info_schema(TransactionConnIdMatchInfoSchema())
@response_schema(EndorserInfoSchema(), 200)
@tenant_authentication
async def set_endorser_info(request: web.BaseRequest):
    """Request handler for assigning endorser information.

    Args:
        request: aiohttp request object
    Returns:
        The assigned endorser information

    """
    context: AdminRequestContext = request["context"]
    connection_id = request.match_info["conn_id"]
    endorser_did = request.query.get("endorser_did")
    endorser_name = request.query.get("endorser_name")

    async with context.profile.session() as session:
        try:
            record = await ConnRecord.retrieve_by_id(session, connection_id)
        except StorageNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err
        except BaseModelError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err
        jobs = await record.metadata_get(session, "transaction_jobs")
    if not jobs:
        raise web.HTTPForbidden(
            reason=(
                "The transaction related jobs are not set up in "
                "connection metadata for this connection record"
            )
        )
    if "transaction_my_job" not in jobs.keys():
        raise web.HTTPForbidden(
            reason=(
                'The "transaction_my_job" is not set in "transaction_jobs"'
                " in connection metadata for this connection record"
            )
        )
    if jobs["transaction_my_job"] != TransactionJob.TRANSACTION_AUTHOR.name:
        raise web.HTTPForbidden(
            reason=(
                "Only a TRANSACTION_AUTHOR can add endorser_info "
                "to metadata of its connection record"
            )
        )
    async with context.profile.session() as session:
        value = await record.metadata_get(session, "endorser_info")
        if value:
            value["endorser_did"] = endorser_did
            value["endorser_name"] = endorser_name
        else:
            value = {"endorser_did": endorser_did, "endorser_name": endorser_name}
        await record.metadata_set(session, key="endorser_info", value=value)

        endorser_info = await record.metadata_get(session, "endorser_info")

    return web.json_response(endorser_info)


@docs(
    tags=["endorse-transaction"],
    summary="For Author / Endorser to write an endorsed transaction to the ledger",
)
@match_info_schema(TranIdMatchInfoSchema())
@response_schema(TransactionRecordSchema(), 200)
@tenant_authentication
async def transaction_write(request: web.BaseRequest):
    """Request handler for writing an endorsed transaction to the ledger.

    Args:
        request: aiohttp request object
    Returns:
        The returned ledger response

    """
    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]
    transaction_id = request.match_info["tran_id"]
    try:
        async with context.profile.session() as session:
            transaction = await TransactionRecord.retrieve_by_id(session, transaction_id)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except BaseModelError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    if transaction.state != TransactionRecord.STATE_TRANSACTION_ENDORSED:
        raise web.HTTPForbidden(
            reason=(
                " The transaction cannot be written to the ledger as it is in state: "
            )
            + transaction.state
        )

    # update the final transaction status
    transaction_mgr = TransactionManager(context.profile)
    try:
        (
            tx_completed,
            transaction_acknowledgement_message,
        ) = await transaction_mgr.complete_transaction(transaction, False)
    except StorageError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(
        transaction_acknowledgement_message, connection_id=transaction.connection_id
    )

    return web.json_response(tx_completed.serialize())


def register_events(event_bus: EventBus):
    """Subscribe to any events we need to support."""
    event_bus.subscribe(STARTUP_EVENT_PATTERN, on_startup_event)
    event_bus.subscribe(SHUTDOWN_EVENT_PATTERN, on_shutdown_event)


async def on_startup_event(profile: Profile, event: Event):
    """Handle any events we need to support."""
    await attempt_auto_author_with_endorser_setup(profile)


async def on_shutdown_event(profile: Profile, event: Event):
    """Handle any events we need to support."""
    # nothing to do for now ...
    pass


async def register(app: web.Application):
    """Register routes."""
    app.add_routes(
        [
            web.get("/transactions", transactions_list, allow_head=False),
            web.get("/transactions/{tran_id}", transactions_retrieve, allow_head=False),
            web.post("/transactions/create-request", transaction_create_request),
            web.post("/transactions/{tran_id}/endorse", endorse_transaction_response),
            web.post("/transactions/{tran_id}/refuse", refuse_transaction_response),
            web.post("/transactions/{tran_id}/cancel", cancel_transaction),
            web.post("/transaction/{tran_id}/resend", transaction_resend),
            web.post("/transactions/{conn_id}/set-endorser-role", set_endorser_role),
            web.post("/transactions/{conn_id}/set-endorser-info", set_endorser_info),
            web.post("/transactions/{tran_id}/write", transaction_write),
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
