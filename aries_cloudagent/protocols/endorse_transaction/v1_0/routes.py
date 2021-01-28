"""Endorse Transaction handling admin routes."""

from asyncio import shield, ensure_future
from aiohttp import web
from aiohttp_apispec import (
    docs,
    response_schema,
    querystring_schema,
    match_info_schema,
)
from marshmallow import fields, validate

from ....admin.request_context import AdminRequestContext
from .manager import TransactionManager
from .models.transaction_record import TransactionRecord, TransactionRecordSchema
from ....connections.models.conn_record import ConnRecord, ConnRecordSchema

from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import UUIDFour
from ....messaging.models.base import BaseModelError

from ....storage.error import StorageError, StorageNotFoundError
from .transaction_jobs import TransactionJob

from ....wallet.base import BaseWallet

from ....ledger.base import BaseLedger
from ....ledger.error import LedgerError
from ....indy.issuer import IndyIssuer, IndyIssuerError
from ....revocation.indy import IndyRevocation
from ....revocation.error import RevocationNotSupportedError, RevocationError
from ....tails.base import BaseTailsServer


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


class AssignTransactionJobsSchema(OpenAPISchema):
    """Assign transaction related jobs to connection record."""

    transaction_my_job = fields.Str(
        description="Transaction related jobs",
        required=False,
        validate=validate.OneOf(
            [r.name for r in TransactionJob if isinstance(r.value[0], int)] + ["reset"]
        ),
    )


class ConnIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    conn_id = fields.Str(
        description="Connection identifier", required=True, example=UUIDFour.EXAMPLE
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
@querystring_schema(TranIdMatchInfoSchema())
@querystring_schema(ConnIdMatchInfoSchema())
@response_schema(TransactionRecordSchema(), 200)
async def transaction_create_request(request: web.BaseRequest):
    """
    Request handler for creating a new transaction record and request.

    Args:
        request: aiohttp request object

    Returns:
        The transaction record

    """

    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]
    connection_id = request.query.get("conn_id")
    transaction_id = request.query.get("tran_id")

    try:
        async with context.session() as session:
            connection_record = await ConnRecord.retrieve_by_id(session, connection_id)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    try:
        async with context.session() as session:
            transaction_record = await TransactionRecord.retrieve_by_id(
                session, transaction_id
            )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    session = await context.session()
    jobs = await connection_record.metadata_get(session, "transaction_jobs")
    if not jobs:
        raise web.HTTPForbidden(
            reason="The transaction related jobs are not setup in "
            "connection metadata for this connection record"
        )
    if "transaction_my_job" not in jobs.keys():
        raise web.HTTPForbidden(
            reason='The "transaction_my_job" is not set in "transaction_jobs"'
            " in connection metadata for this connection record"
        )
    if "transaction_their_job" not in jobs.keys():
        raise web.HTTPForbidden(
            reason='Ask the other agent to set up "transaction_my_job" '
            ' in "transaction_jobs" in connection metadata for their connection record'
        )
    if jobs["transaction_my_job"] != "TRANSACTION_AUTHOR":
        raise web.HTTPForbidden(reason="Only a TRANSACTION_AUTHOR can create a request")

    transaction_mgr = TransactionManager(session)

    (transaction_record, transaction_request) = await transaction_mgr.create_request(
        transaction=transaction_record, connection_id=connection_id
    )

    await outbound_handler(
        transaction_request, connection_id=connection_record.connection_id
    )

    return web.json_response(transaction_record.serialize())


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
    outbound_handler = request["outbound_message_router"]
    session = await context.session()

    wallet: BaseWallet = session.inject(BaseWallet, required=False)

    if not wallet:
        raise web.HTTPForbidden(reason="No wallet available")
    endorser_did_info = await wallet.get_public_did()
    if not endorser_did_info:
        raise web.HTTPForbidden(
            reason="Transaction cannot be endorsed as there is no Public DID in wallet"
        )
    endorser_did = endorser_did_info.did
    endorser_verkey = endorser_did_info.verkey

    transaction_id = request.match_info["tran_id"]
    try:
        async with context.session() as session:
            transaction = await TransactionRecord.retrieve_by_id(
                session, transaction_id
            )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    try:
        async with context.session() as session:
            connection_record = await ConnRecord.retrieve_by_id(
                session, transaction.connection_id
            )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    session = await context.session()
    jobs = await connection_record.metadata_get(session, "transaction_jobs")
    if not jobs:
        raise web.HTTPForbidden(
            reason="The transaction related jobs are not setup in "
            "connection metadata for this connection record"
        )
    if jobs["transaction_my_job"] != "TRANSACTION_ENDORSER":
        raise web.HTTPForbidden(
            reason="Only a TRANSACTION_ENDORSER can endorse a transaction"
        )

    transaction_mgr = TransactionManager(session)
    (
        transaction,
        endorsed_transaction_response,
    ) = await transaction_mgr.create_endorse_response(
        transaction=transaction,
        state=TransactionRecord.STATE_TRANSACTION_ENDORSED,
        endorser_did=endorser_did,
        endorser_verkey=endorser_verkey,
    )

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
async def refuse_transaction_response(request: web.BaseRequest):
    """
    Request handler for creating a refused transaction response.

    Args:
        request: aiohttp request object

    Returns:
        The updated transaction record details

    """

    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]
    session = await context.session()

    wallet: BaseWallet = session.inject(BaseWallet, required=False)

    if not wallet:
        raise web.HTTPForbidden(reason="No wallet available")
    refuser_did_info = await wallet.get_public_did()
    if not refuser_did_info:
        raise web.HTTPForbidden(
            reason="Transaction cannot be refused as there is no Public DID in wallet"
        )
    refuser_did = refuser_did_info.did

    transaction_id = request.match_info["tran_id"]
    try:
        async with context.session() as session:
            transaction = await TransactionRecord.retrieve_by_id(
                session, transaction_id
            )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    try:
        async with context.session() as session:
            connection_record = await ConnRecord.retrieve_by_id(
                session, transaction.connection_id
            )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    session = await context.session()
    jobs = await connection_record.metadata_get(session, "transaction_jobs")
    if not jobs:
        raise web.HTTPForbidden(
            reason="The transaction related jobs are not setup in "
            "connection metadata for this connection record"
        )
    if jobs["transaction_my_job"] != "TRANSACTION_ENDORSER":
        raise web.HTTPForbidden(
            reason="Only a TRANSACTION_ENDORSER can refuse a transaction"
        )

    transaction_mgr = TransactionManager(session)
    (
        transaction,
        refused_transaction_response,
    ) = await transaction_mgr.create_refuse_response(
        transaction=transaction,
        state=TransactionRecord.STATE_TRANSACTION_REFUSED,
        refuser_did=refuser_did,
    )

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
async def cancel_transaction(request: web.BaseRequest):
    """
    Request handler for cancelling a Transaction request.

    Args:
        request: aiohttp request object

    Returns:
        The updated transaction record details

    """

    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]

    transaction_id = request.match_info["tran_id"]
    try:
        async with context.session() as session:
            transaction = await TransactionRecord.retrieve_by_id(
                session, transaction_id
            )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    try:
        async with context.session() as session:
            connection_record = await ConnRecord.retrieve_by_id(
                session, transaction.connection_id
            )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    session = await context.session()
    jobs = await connection_record.metadata_get(session, "transaction_jobs")
    if not jobs:
        raise web.HTTPForbidden(
            reason="The transaction related jobs are not setup in "
            "connection metadata for this connection record"
        )
    if jobs["transaction_my_job"] != "TRANSACTION_AUTHOR":
        raise web.HTTPForbidden(
            reason="Only a TRANSACTION_AUTHOR can cancel a transaction"
        )

    transaction_mgr = TransactionManager(session)
    (
        transaction,
        cancelled_transaction_response,
    ) = await transaction_mgr.cancel_transaction(
        transaction=transaction, state=TransactionRecord.STATE_TRANSACTION_CANCELLED
    )

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
async def transaction_resend(request: web.BaseRequest):
    """
    Request handler for resending a transaction request.

    Args:
        request: aiohttp request object

    Returns:
        The updated transaction record details

    """

    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]

    transaction_id = request.match_info["tran_id"]
    try:
        async with context.session() as session:
            transaction = await TransactionRecord.retrieve_by_id(
                session, transaction_id
            )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    try:
        async with context.session() as session:
            connection_record = await ConnRecord.retrieve_by_id(
                session, transaction.connection_id
            )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    session = await context.session()
    jobs = await connection_record.metadata_get(session, "transaction_jobs")
    if not jobs:
        raise web.HTTPForbidden(
            reason="The transaction related jobs are not setup in "
            "connection metadata for this connection record"
        )
    if jobs["transaction_my_job"] != "TRANSACTION_AUTHOR":
        raise web.HTTPForbidden(
            reason="Only a TRANSACTION_AUTHOR can resend a transaction"
        )

    transaction_mgr = TransactionManager(session)
    (
        transaction,
        resend_transaction_response,
    ) = await transaction_mgr.transaction_resend(
        transaction=transaction, state=TransactionRecord.STATE_TRANSACTION_RESENT
    )

    await outbound_handler(
        resend_transaction_response, connection_id=transaction.connection_id
    )

    return web.json_response(transaction.serialize())


@docs(
    tags=["endorse-transaction"],
    summary="Set transaction jobs",
)
@querystring_schema(AssignTransactionJobsSchema())
@match_info_schema(ConnIdMatchInfoSchema())
@response_schema(ConnRecordSchema(), 200, description="")
async def set_transaction_jobs(request: web.BaseRequest):
    """
    Request handler for assigning transaction jobs.

    Args:
        request: aiohttp request object

    Returns:
        The assigned transaction jobs

    """

    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]
    connection_id = request.match_info["conn_id"]
    transaction_my_job = request.query.get("transaction_my_job")
    session = await context.session()

    try:
        record = await ConnRecord.retrieve_by_id(session, connection_id)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except BaseModelError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    transaction_mgr = TransactionManager(session)
    tx_job_to_send = await transaction_mgr.set_transaction_my_job(
        record=record, transaction_my_job=transaction_my_job
    )
    jobs = await record.metadata_get(session, "transaction_jobs")

    await outbound_handler(tx_job_to_send, connection_id=connection_id)
    return web.json_response(jobs)


@docs(
    tags=["endorse-transaction"],
    summary="For Author to write an endorsed transaction to the ledger",
)
@match_info_schema(TranIdMatchInfoSchema())
@response_schema(TransactionRecordSchema(), 200)
async def transaction_write(request: web.BaseRequest):
    """
    Request handler for writing an endorsed transaction to the ledger.

    Args:
        request: aiohttp request object

    Returns:
        The returned ledger response

    """

    context: AdminRequestContext = request["context"]

    transaction_id = request.match_info["tran_id"]
    try:
        async with context.session() as session:
            transaction = await TransactionRecord.retrieve_by_id(
                session, transaction_id
            )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    try:
        async with context.session() as session:
            connection_record = await ConnRecord.retrieve_by_id(
                session, transaction.connection_id
            )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    session = await context.session()
    jobs = await connection_record.metadata_get(session, "transaction_jobs")
    if not jobs:
        raise web.HTTPForbidden(
            reason="The transaction related jobs are not setup in "
            "connection metadata for this connection record"
        )
    if jobs["transaction_my_job"] != "TRANSACTION_AUTHOR":
        raise web.HTTPForbidden(
            reason="Only a TRANSACTION_AUTHOR can write a transaction to the ledger"
        )

    if transaction.state != TransactionRecord.STATE_TRANSACTION_ENDORSED:
        raise web.HTTPForbidden(
            reason="Only an endorsed transaction can be written to the ledger"
        )

    body = transaction.messages_attach[0]["data"]["json"]["operation"]["data"]

    if transaction.messages_attach[0]["data"]["json"]["operation"]["type"] == "101":

        schema_name = body.get("schema_name")
        schema_version = body.get("schema_version")
        attributes = body.get("attributes")

        ledger = context.inject(BaseLedger, required=False)
        if not ledger:
            reason = "No ledger available"
            if not context.settings.get_value("wallet.type"):
                reason += ": missing wallet-type?"
            raise web.HTTPForbidden(reason=reason)

        issuer = context.inject(IndyIssuer)
        async with ledger:
            try:
                schema_id, schema_def = await shield(
                    ledger.create_and_send_schema(
                        issuer, schema_name, schema_version, attributes
                    )
                )
            except (IndyIssuerError, LedgerError) as err:
                raise web.HTTPBadRequest(reason=err.roll_up) from err

        return web.json_response({"schema_id": schema_id, "schema": schema_def})

    else:

        schema_id = body.get("schema_id")
        support_revocation = bool(body.get("support_revocation"))
        tag = body.get("tag")
        rev_reg_size = body.get("revocation_registry_size")

        ledger = context.inject(BaseLedger, required=False)
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
                    )
                )
        except LedgerError as e:
            raise web.HTTPBadRequest(reason=e.message) from e

        # If revocation is requested and cred def is novel, create revocation registry
        if support_revocation and novel:
            session = (
                await context.session()
            )  # FIXME - will update to not require session here
            tails_base_url = session.settings.get("tails_server_base_url")
            if not tails_base_url:
                raise web.HTTPBadRequest(reason="tails_server_base_url not configured")
            try:
                # Create registry
                revoc = IndyRevocation(session)
                registry_record = await revoc.init_issuer_registry(
                    cred_def_id,
                    max_cred_num=rev_reg_size,
                )

            except RevocationNotSupportedError as e:
                raise web.HTTPBadRequest(reason=e.message) from e
            await shield(registry_record.generate_registry(session))
            try:
                await registry_record.set_tails_file_public_uri(
                    session, f"{tails_base_url}/{registry_record.revoc_reg_id}"
                )
                await registry_record.send_def(session)
                await registry_record.send_entry(session)

                # stage pending registry independent of whether tails server is OK
                pending_registry_record = await revoc.init_issuer_registry(
                    registry_record.cred_def_id,
                    max_cred_num=registry_record.max_cred_num,
                )
                ensure_future(
                    pending_registry_record.stage_pending_registry(
                        session, max_attempts=16
                    )
                )

                tails_server = session.inject(BaseTailsServer)
                (upload_success, reason) = await tails_server.upload_tails_file(
                    session,
                    registry_record.revoc_reg_id,
                    registry_record.tails_local_path,
                    interval=0.8,
                    backoff=-0.5,
                    max_attempts=5,  # heuristic: respect HTTP timeout
                )
                if not upload_success:
                    raise web.HTTPInternalServerError(
                        reason=(
                            f"Tails file for rev reg {registry_record.revoc_reg_id} "
                            f"failed to upload: {reason}"
                        )
                    )

            except RevocationError as e:
                raise web.HTTPBadRequest(reason=e.message) from e

        return web.json_response({"credential_definition_id": cred_def_id})


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
            web.post(
                "/transactions/{conn_id}/set-transaction-jobs", set_transaction_jobs
            ),
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
