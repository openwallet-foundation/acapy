"""Ledger admin routes."""

import json
import logging

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, request_schema, response_schema
from marshmallow import fields, validate

from ..admin.request_context import AdminRequestContext
from ..connections.models.conn_record import ConnRecord
from ..messaging.models.base import BaseModelError
from ..messaging.models.openapi import OpenAPISchema
from ..messaging.valid import (
    ENDPOINT,
    ENDPOINT_TYPE,
    INDY_DID,
    INDY_RAW_PUBLIC_KEY,
    INT_EPOCH,
    UUIDFour,
)
from ..multitenant.base import BaseMultitenantManager

from ..protocols.endorse_transaction.v1_0.manager import (
    TransactionManager,
    TransactionManagerError,
)
from ..protocols.endorse_transaction.v1_0.models.transaction_record import (
    TransactionRecord,
    TransactionRecordSchema,
)
from ..protocols.endorse_transaction.v1_0.util import (
    is_author_role,
    get_endorser_connection_id,
)
from ..storage.error import StorageError, StorageNotFoundError
from ..wallet.error import WalletError, WalletNotFoundError

from .base import BaseLedger, Role as LedgerRole
from .multiple_ledger.base_manager import (
    BaseMultipleLedgerManager,
)
from .multiple_ledger.ledger_requests_executor import (
    GET_NYM_ROLE,
    GET_KEY_FOR_DID,
    GET_ENDPOINT_FOR_DID,
    IndyLedgerRequestsExecutor,
)
from .multiple_ledger.ledger_config_schema import (
    LedgerConfigListSchema,
    WriteLedgerRequestSchema,
)
from .endpoint_type import EndpointType
from .error import BadLedgerRequestError, LedgerError, LedgerTransactionError
from .util import notify_register_did_event


LOGGER = logging.getLogger(__name__)


class LedgerModulesResultSchema(OpenAPISchema):
    """Schema for the modules endpoint."""


class AMLRecordSchema(OpenAPISchema):
    """Ledger AML record."""

    version = fields.Str()
    aml = fields.Dict(fields.Str(), fields.Str())
    amlContext = fields.Str()


class TAARecordSchema(OpenAPISchema):
    """Ledger TAA record."""

    version = fields.Str()
    text = fields.Str()
    digest = fields.Str()


class TAAAcceptanceSchema(OpenAPISchema):
    """TAA acceptance record."""

    mechanism = fields.Str()
    time = fields.Int(strict=True, **INT_EPOCH)


class TAAInfoSchema(OpenAPISchema):
    """Transaction author agreement info."""

    aml_record = fields.Nested(AMLRecordSchema())
    taa_record = fields.Nested(TAARecordSchema())
    taa_required = fields.Bool()
    taa_accepted = fields.Nested(TAAAcceptanceSchema())


class TAAResultSchema(OpenAPISchema):
    """Result schema for a transaction author agreement."""

    result = fields.Nested(TAAInfoSchema())


class TAAAcceptSchema(OpenAPISchema):
    """Input schema for accepting the TAA."""

    version = fields.Str()
    text = fields.Str()
    mechanism = fields.Str()


class RegisterLedgerNymQueryStringSchema(OpenAPISchema):
    """Query string parameters and validators for register ledger nym request."""

    did = fields.Str(
        description="DID to register",
        required=True,
        **INDY_DID,
    )
    verkey = fields.Str(
        description="Verification key", required=True, **INDY_RAW_PUBLIC_KEY
    )
    alias = fields.Str(
        description="Alias",
        required=False,
        example="Barry",
    )
    role = fields.Str(
        description="Role",
        required=False,
        validate=validate.OneOf(
            [r.name for r in LedgerRole if isinstance(r.value[0], int)] + ["reset"]
        ),
    )


class CreateDidTxnForEndorserOptionSchema(OpenAPISchema):
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


class QueryStringDIDSchema(OpenAPISchema):
    """Parameters and validators for query string with DID only."""

    did = fields.Str(description="DID of interest", required=True, **INDY_DID)


class QueryStringEndpointSchema(OpenAPISchema):
    """Parameters and validators for query string with DID and endpoint type."""

    did = fields.Str(description="DID of interest", required=True, **INDY_DID)
    endpoint_type = fields.Str(
        description=(
            f"Endpoint type of interest (default '{EndpointType.ENDPOINT.w3c}')"
        ),
        required=False,
        **ENDPOINT_TYPE,
    )


class TxnOrRegisterLedgerNymResponseSchema(OpenAPISchema):
    """Response schema for ledger nym registration."""

    success = fields.Bool(
        description="Success of nym registration operation",
        example=True,
    )

    txn = fields.Nested(
        TransactionRecordSchema(),
        required=False,
        description="DID transaction to endorse",
    )


class GetNymRoleResponseSchema(OpenAPISchema):
    """Response schema to get nym role operation."""

    role = fields.Str(
        description="Ledger role",
        validate=validate.OneOf([r.name for r in LedgerRole]),
        example=LedgerRole.ENDORSER.name,
    )


class GetDIDVerkeyResponseSchema(OpenAPISchema):
    """Response schema to get DID verkey."""

    verkey = fields.Str(
        description="Full verification key",
        allow_none=True,
        **INDY_RAW_PUBLIC_KEY,
    )


class GetDIDEndpointResponseSchema(OpenAPISchema):
    """Response schema to get DID endpoint."""

    endpoint = fields.Str(
        description="Full verification key",
        allow_none=True,
        **ENDPOINT,
    )


@docs(
    tags=["ledger"],
    summary="Send a NYM registration to the ledger.",
)
@querystring_schema(RegisterLedgerNymQueryStringSchema())
@querystring_schema(CreateDidTxnForEndorserOptionSchema())
@querystring_schema(SchemaConnIdMatchInfoSchema())
@response_schema(TxnOrRegisterLedgerNymResponseSchema(), 200, description="")
async def register_ledger_nym(request: web.BaseRequest):
    """
    Request handler for registering a NYM with the ledger.

    Args:
        request: aiohttp request object
    """
    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]
    async with context.profile.session() as session:
        ledger = session.inject_or(BaseLedger)
        if not ledger:
            reason = "No Indy ledger available"
            if not session.settings.get_value("wallet.type"):
                reason += ": missing wallet-type?"
            raise web.HTTPForbidden(reason=reason)

    did = request.query.get("did")
    verkey = request.query.get("verkey")
    if not did or not verkey:
        raise web.HTTPBadRequest(
            reason="Request query must include both did and verkey"
        )

    alias = request.query.get("alias")
    role = request.query.get("role")
    if role == "reset":  # indy: empty to reset, null for regular user
        role = ""  # visually: confusing - correct 'reset' to empty string here

    create_transaction_for_endorser = json.loads(
        request.query.get("create_transaction_for_endorser", "false")
    )
    write_ledger = not create_transaction_for_endorser
    endorser_did = None
    connection_id = request.query.get("conn_id")

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
            async with context.profile.session() as session:
                connection_record = await ConnRecord.retrieve_by_id(
                    session, connection_id
                )
        except StorageNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err
        except BaseModelError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

        async with context.profile.session() as session:
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

    meta_data = {"did": did, "verkey": verkey, "alias": alias, "role": role}
    success = False
    txn = None
    async with ledger:
        try:
            # if we are an author check if we have a public DID or not
            write_ledger_nym_transaction = True
            # special case - if we are an author with no public DID
            if create_transaction_for_endorser:
                public_info = await ledger.get_wallet_public_did()
                if not public_info:
                    write_ledger_nym_transaction = False
                    success = False
                    txn = {"signed_txn": json.dumps(meta_data)}
            if write_ledger_nym_transaction:
                (success, txn) = await ledger.register_nym(
                    did,
                    verkey,
                    alias,
                    role,
                    write_ledger=write_ledger,
                    endorser_did=endorser_did,
                )
        except LedgerTransactionError as err:
            raise web.HTTPForbidden(reason=err.roll_up)
        except LedgerError as err:
            raise web.HTTPBadRequest(reason=err.roll_up)
        except WalletNotFoundError as err:
            raise web.HTTPForbidden(reason=err.roll_up)
        except WalletError as err:
            raise web.HTTPBadRequest(
                reason=(
                    f"Registered NYM for DID {did} on ledger but could not "
                    f"replace metadata in wallet: {err.roll_up}"
                )
            )

    if not create_transaction_for_endorser:
        # Notify event
        await notify_register_did_event(context.profile, did, meta_data)
        return web.json_response({"success": success})
    else:
        transaction_mgr = TransactionManager(context.profile)
        try:
            transaction = await transaction_mgr.create_record(
                messages_attach=txn["signed_txn"],
                connection_id=connection_id,
                meta_data=meta_data,
            )
        except StorageError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

        # if auto-request, send the request to the endorser
        if context.settings.get_value("endorser.auto_request"):
            try:
                endorser_write_txn = not write_ledger_nym_transaction
                transaction, transaction_request = await transaction_mgr.create_request(
                    transaction=transaction,
                    author_goal_code=TransactionRecord.REGISTER_PUBLIC_DID
                    if endorser_write_txn
                    else None,
                    signer_goal_code=TransactionRecord.WRITE_DID_TRANSACTION
                    if endorser_write_txn
                    else None,
                    endorser_write_txn=endorser_write_txn,
                    # TODO see if we need to parameterize these params
                    # expires_time=expires_time,
                    # endorser_write_txn=endorser_write_txn,
                )
                txn = transaction.serialize()
            except (StorageError, TransactionManagerError) as err:
                raise web.HTTPBadRequest(reason=err.roll_up) from err

            await outbound_handler(transaction_request, connection_id=connection_id)

        return web.json_response({"success": success, "txn": txn})


@docs(
    tags=["ledger"],
    summary="Get the role from the NYM registration of a public DID.",
)
@querystring_schema(QueryStringDIDSchema)
@response_schema(GetNymRoleResponseSchema(), 200, description="")
async def get_nym_role(request: web.BaseRequest):
    """
    Request handler for getting the role from the NYM registration of a public DID.

    Args:
        request: aiohttp request object
    """
    context: AdminRequestContext = request["context"]

    did = request.query.get("did")
    if not did:
        raise web.HTTPBadRequest(reason="Request query must include DID")

    async with context.profile.session() as session:
        multitenant_mgr = session.inject_or(BaseMultitenantManager)
        if multitenant_mgr:
            ledger_exec_inst = IndyLedgerRequestsExecutor(context.profile)
        else:
            ledger_exec_inst = session.inject(IndyLedgerRequestsExecutor)
        ledger_id, ledger = await ledger_exec_inst.get_ledger_for_identifier(
            did,
            txn_record_type=GET_NYM_ROLE,
        )
        if not ledger:
            reason = "No Indy ledger available"
            if not session.settings.get_value("wallet.type"):
                reason += ": missing wallet-type?"
            raise web.HTTPForbidden(reason=reason)

    async with ledger:
        try:
            role = await ledger.get_nym_role(did)
        except LedgerTransactionError as err:
            raise web.HTTPForbidden(reason=err.roll_up)
        except BadLedgerRequestError as err:
            raise web.HTTPNotFound(reason=err.roll_up)
        except LedgerError as err:
            raise web.HTTPBadRequest(reason=err.roll_up)

    if ledger_id:
        return web.json_response({"ledger_id": ledger_id, "role": role.name})
    else:
        return web.json_response({"role": role.name})


@docs(tags=["ledger"], summary="Rotate key pair for public DID.")
@response_schema(LedgerModulesResultSchema(), 200, description="")
async def rotate_public_did_keypair(request: web.BaseRequest):
    """
    Request handler for rotating key pair associated with public DID.

    Args:
        request: aiohttp request object
    """
    context: AdminRequestContext = request["context"]
    async with context.profile.session() as session:
        ledger = session.inject_or(BaseLedger)
        if not ledger:
            reason = "No Indy ledger available"
            if not session.settings.get_value("wallet.type"):
                reason += ": missing wallet-type?"
            raise web.HTTPForbidden(reason=reason)
    async with ledger:
        try:
            await ledger.rotate_public_did_keypair()  # do not take seed over the wire
        except (WalletError, BadLedgerRequestError) as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})


@docs(
    tags=["ledger"],
    summary="Get the verkey for a DID from the ledger.",
)
@querystring_schema(QueryStringDIDSchema())
@response_schema(GetDIDVerkeyResponseSchema(), 200, description="")
async def get_did_verkey(request: web.BaseRequest):
    """
    Request handler for getting a verkey for a DID from the ledger.

    Args:
        request: aiohttp request object
    """
    context: AdminRequestContext = request["context"]

    did = request.query.get("did")
    if not did:
        raise web.HTTPBadRequest(reason="Request query must include DID")

    async with context.profile.session() as session:
        multitenant_mgr = session.inject_or(BaseMultitenantManager)
        if multitenant_mgr:
            ledger_exec_inst = IndyLedgerRequestsExecutor(context.profile)
        else:
            ledger_exec_inst = session.inject(IndyLedgerRequestsExecutor)
        ledger_id, ledger = await ledger_exec_inst.get_ledger_for_identifier(
            did,
            txn_record_type=GET_KEY_FOR_DID,
        )
        if not ledger:
            reason = "No ledger available"
            if not session.settings.get_value("wallet.type"):
                reason += ": missing wallet-type?"
            raise web.HTTPForbidden(reason=reason)

    async with ledger:
        try:
            result = await ledger.get_key_for_did(did)
            if not result:
                raise web.HTTPNotFound(reason=f"DID {did} is not on the ledger")
        except LedgerError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    if ledger_id:
        return web.json_response({"ledger_id": ledger_id, "verkey": result})
    else:
        return web.json_response({"verkey": result})


@docs(
    tags=["ledger"],
    summary="Get the endpoint for a DID from the ledger.",
)
@querystring_schema(QueryStringEndpointSchema())
@response_schema(GetDIDEndpointResponseSchema(), 200, description="")
async def get_did_endpoint(request: web.BaseRequest):
    """
    Request handler for getting a verkey for a DID from the ledger.

    Args:
        request: aiohttp request object
    """
    context: AdminRequestContext = request["context"]

    did = request.query.get("did")
    if not did:
        raise web.HTTPBadRequest(reason="Request query must include DID")

    async with context.profile.session() as session:
        multitenant_mgr = session.inject_or(BaseMultitenantManager)
        if multitenant_mgr:
            ledger_exec_inst = IndyLedgerRequestsExecutor(context.profile)
        else:
            ledger_exec_inst = session.inject(IndyLedgerRequestsExecutor)
        ledger_id, ledger = await ledger_exec_inst.get_ledger_for_identifier(
            did,
            txn_record_type=GET_ENDPOINT_FOR_DID,
        )
        if not ledger:
            reason = "No Indy ledger available"
            if not session.settings.get_value("wallet.type"):
                reason += ": missing wallet-type?"
            raise web.HTTPForbidden(reason=reason)
    endpoint_type = EndpointType.get(
        request.query.get("endpoint_type", EndpointType.ENDPOINT.w3c)
    )

    async with ledger:
        try:
            r = await ledger.get_endpoint_for_did(did, endpoint_type)
        except LedgerError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    if ledger_id:
        return web.json_response({"ledger_id": ledger_id, "endpoint": r})
    else:
        return web.json_response({"endpoint": r})


@docs(tags=["ledger"], summary="Fetch the current transaction author agreement, if any")
@response_schema(TAAResultSchema, 200, description="")
async def ledger_get_taa(request: web.BaseRequest):
    """
    Request handler for fetching the transaction author agreement.

    Args:
        request: aiohttp request object

    Returns:
        The TAA information including the AML

    """
    context: AdminRequestContext = request["context"]
    async with context.profile.session() as session:
        ledger = session.inject_or(BaseLedger)
        if not ledger:
            reason = "No Indy ledger available"
            if not session.settings.get_value("wallet.type"):
                reason += ": missing wallet-type?"
            raise web.HTTPForbidden(reason=reason)

    async with ledger:
        try:
            taa_info = await ledger.get_txn_author_agreement()
            accepted = None
            if taa_info["taa_required"]:
                accept_record = await ledger.get_latest_txn_author_acceptance()
                if accept_record:
                    accepted = {
                        "mechanism": accept_record["mechanism"],
                        "time": accept_record["time"],
                    }
            taa_info["taa_accepted"] = accepted
        except LedgerError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"result": taa_info})


@docs(tags=["ledger"], summary="Accept the transaction author agreement")
@request_schema(TAAAcceptSchema)
@response_schema(LedgerModulesResultSchema(), 200, description="")
async def ledger_accept_taa(request: web.BaseRequest):
    """
    Request handler for accepting the current transaction author agreement.

    Args:
        request: aiohttp request object

    Returns:
        The DID list response

    """
    context: AdminRequestContext = request["context"]
    async with context.profile.session() as session:
        ledger = session.inject_or(BaseLedger)
        if not ledger:
            reason = "No Indy ledger available"
            if not session.settings.get_value("wallet.type"):
                reason += ": missing wallet-type?"
            raise web.HTTPForbidden(reason=reason)

    accept_input = await request.json()
    LOGGER.info(">>> accepting TAA with: %s", accept_input)
    async with ledger:
        try:
            taa_info = await ledger.get_txn_author_agreement()
            if not taa_info["taa_required"]:
                raise web.HTTPBadRequest(
                    reason=f"Ledger {ledger.pool_name} TAA not available"
                )
            LOGGER.info("TAA on ledger: ", taa_info)
            # this is a bit of a hack, but the "\ufeff" code is included in the
            # ledger TAA and digest calculation, so it needs to be included in the
            # TAA text that the user is accepting
            # (if you copy the TAA text using swagger it won't include this character)
            if taa_info["taa_record"]["text"].startswith("\ufeff"):
                if not accept_input["text"].startswith("\ufeff"):
                    LOGGER.info(
                        ">>> pre-pending -endian character to TAA acceptance text"
                    )
                    accept_input["text"] = "\ufeff" + accept_input["text"]
            taa_record = {
                "version": accept_input["version"],
                "text": accept_input["text"],
                "digest": ledger.taa_digest(
                    accept_input["version"],
                    accept_input["text"],
                ),
            }
            taa_record_digest = taa_record["digest"]
            LOGGER.info(">>> accepting with digest: %s", taa_record_digest)
            await ledger.accept_txn_author_agreement(
                taa_record, accept_input["mechanism"]
            )
        except (LedgerError, StorageError) as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})


@docs(tags=["ledger"], summary="Fetch the current write ledger")
@response_schema(WriteLedgerRequestSchema, 200, description="")
async def get_write_ledger(request: web.BaseRequest):
    """
    Request handler for fetching the currently set write ledger.

    Args:
        request: aiohttp request object

    Returns:
        The write ledger identifier

    """
    context: AdminRequestContext = request["context"]
    async with context.profile.session() as session:
        multiledger_mgr = session.inject_or(BaseMultipleLedgerManager)
    if not multiledger_mgr:
        reason = "Multiple ledger support not enabled"
        raise web.HTTPForbidden(reason=reason)
    ledger_id = (await multiledger_mgr.get_write_ledger())[0]
    return web.json_response({"ledger_id": ledger_id})


@docs(
    tags=["ledger"], summary="Fetch the multiple ledger configuration currently in use"
)
@response_schema(LedgerConfigListSchema, 200, description="")
async def get_ledger_config(request: web.BaseRequest):
    """
    Request handler for fetching the ledger configuration list in use.

    Args:
        request: aiohttp request object

    Returns:
        Ledger configuration list

    """
    context: AdminRequestContext = request["context"]
    async with context.profile.session() as session:
        multiledger_mgr = session.inject_or(BaseMultipleLedgerManager)
        if not multiledger_mgr:
            reason = "Multiple ledger support not enabled"
            raise web.HTTPForbidden(reason=reason)
        ledger_config_list = session.settings.get_value("ledger.ledger_config_list")
        config_ledger_dict = {"production_ledgers": [], "non_production_ledgers": []}
        production_ledger_keys = (await multiledger_mgr.get_prod_ledgers()).keys()
        non_production_ledger_keys = (
            await multiledger_mgr.get_nonprod_ledgers()
        ).keys()
        config_ledger_ids_set = set()
        for config in ledger_config_list:
            ledger_id = config.get("id")
            config_ledger_ids_set.add(ledger_id)
            # removing genesis_transactions
            config = {
                key: val for key, val in config.items() if key != "genesis_transactions"
            }
            if ledger_id in production_ledger_keys:
                config_ledger_dict.get("production_ledgers").append(config)
            if ledger_id in non_production_ledger_keys:
                config_ledger_dict.get("non_production_ledgers").append(config)
        diff_prod_ledger_ids_set = set(production_ledger_keys) - config_ledger_ids_set
        for diff_prod_ledger_id in diff_prod_ledger_ids_set:
            config_ledger_dict.get("production_ledgers").append(
                {
                    "id": diff_prod_ledger_id,
                    "desc": "ledger configured outside --genesis-transactions-list",
                }
            )
    return web.json_response(config_ledger_dict)


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.post("/ledger/register-nym", register_ledger_nym),
            web.get("/ledger/get-nym-role", get_nym_role, allow_head=False),
            web.patch("/ledger/rotate-public-did-keypair", rotate_public_did_keypair),
            web.get("/ledger/did-verkey", get_did_verkey, allow_head=False),
            web.get("/ledger/did-endpoint", get_did_endpoint, allow_head=False),
            web.get("/ledger/taa", ledger_get_taa, allow_head=False),
            web.post("/ledger/taa/accept", ledger_accept_taa),
            web.get(
                "/ledger/multiple/get-write-ledger", get_write_ledger, allow_head=False
            ),
            web.get("/ledger/multiple/config", get_ledger_config, allow_head=False),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "ledger",
            "description": "Interaction with ledger",
            "externalDocs": {
                "description": "Overview",
                "url": (
                    "https://hyperledger-indy.readthedocs.io/projects/plenum/"
                    "en/latest/storage.html#ledger"
                ),
            },
        }
    )
