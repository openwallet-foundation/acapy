"""Ledger admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, request_schema, response_schema

from marshmallow import fields, validate

from ..messaging.models.openapi import OpenAPISchema
from ..messaging.request_context import RequestContext
from ..messaging.valid import ENDPOINT_TYPE, INDY_DID, INDY_RAW_PUBLIC_KEY, INT_EPOCH
from ..storage.error import StorageError
from ..wallet.error import WalletError

from .base import BaseLedger
from .endpoint_type import EndpointType
from .error import BadLedgerRequestError, LedgerError, LedgerTransactionError
from .indy import Role


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
            [r.name for r in Role if isinstance(r.value[0], int)] + ["reset"]
        ),
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


@docs(
    tags=["ledger"],
    summary="Send a NYM registration to the ledger.",
)
@querystring_schema(RegisterLedgerNymQueryStringSchema())
async def register_ledger_nym(request: web.BaseRequest):
    """
    Request handler for registering a NYM with the ledger.

    Args:
        request: aiohttp request object
    """
    context: RequestContext = request.app["request_context"]
    session = await context.session()
    ledger = session.inject(BaseLedger, required=False)
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

    success = False
    async with ledger:
        try:
            await ledger.register_nym(did, verkey, alias, role)
            success = True
        except LedgerTransactionError as err:
            raise web.HTTPForbidden(reason=err.roll_up)
        except LedgerError as err:
            raise web.HTTPBadRequest(reason=err.roll_up)
        except WalletError as err:
            raise web.HTTPBadRequest(
                reason=(
                    f"Registered NYM for DID {did} on ledger but could not "
                    f"replace metadata in wallet: {err.roll_up}"
                )
            )

    return web.json_response({"success": success})


@docs(
    tags=["ledger"],
    summary="Get the role from the NYM registration of a public DID.",
)
@querystring_schema(QueryStringDIDSchema)
async def get_nym_role(request: web.BaseRequest):
    """
    Request handler for getting the role from the NYM registration of a public DID.

    Args:
        request: aiohttp request object
    """
    context: RequestContext = request.app["request_context"]
    session = await context.session()
    ledger = session.inject(BaseLedger, required=False)
    if not ledger:
        reason = "No Indy ledger available"
        if not session.settings.get_value("wallet.type"):
            reason += ": missing wallet-type?"
        raise web.HTTPForbidden(reason=reason)

    did = request.query.get("did")
    if not did:
        raise web.HTTPBadRequest(reason="Request query must include DID")

    async with ledger:
        try:
            role = await ledger.get_nym_role(did)
        except LedgerTransactionError as err:
            raise web.HTTPForbidden(reason=err.roll_up)
        except BadLedgerRequestError as err:
            raise web.HTTPNotFound(reason=err.roll_up)
        except LedgerError as err:
            raise web.HTTPBadRequest(reason=err.roll_up)
    return web.json_response({"role": role.name})


@docs(tags=["ledger"], summary="Rotate key pair for public DID.")
async def rotate_public_did_keypair(request: web.BaseRequest):
    """
    Request handler for rotating key pair associated with public DID.

    Args:
        request: aiohttp request object
    """
    context: RequestContext = request.app["request_context"]
    session = await context.session()
    ledger = session.inject(BaseLedger, required=False)
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
async def get_did_verkey(request: web.BaseRequest):
    """
    Request handler for getting a verkey for a DID from the ledger.

    Args:
        request: aiohttp request object
    """
    context: RequestContext = request.app["request_context"]
    session = await context.session()
    ledger = session.inject(BaseLedger, required=False)
    if not ledger:
        reason = "No ledger available"
        if not session.settings.get_value("wallet.type"):
            reason += ": missing wallet-type?"
        raise web.HTTPForbidden(reason=reason)

    did = request.query.get("did")
    if not did:
        raise web.HTTPBadRequest(reason="Request query must include DID")

    async with ledger:
        try:
            result = await ledger.get_key_for_did(did)
            if not result:
                raise web.HTTPNotFound(reason=f"DID {did} is not on the ledger")
        except LedgerError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"verkey": result})


@docs(
    tags=["ledger"],
    summary="Get the endpoint for a DID from the ledger.",
)
@querystring_schema(QueryStringEndpointSchema())
async def get_did_endpoint(request: web.BaseRequest):
    """
    Request handler for getting a verkey for a DID from the ledger.

    Args:
        request: aiohttp request object
    """
    context: RequestContext = request.app["request_context"]
    session = await context.session()
    ledger = session.inject(BaseLedger, required=False)
    if not ledger:
        reason = "No Indy ledger available"
        if not session.settings.get_value("wallet.type"):
            reason += ": missing wallet-type?"
        raise web.HTTPForbidden(reason=reason)

    did = request.query.get("did")
    endpoint_type = EndpointType.get(
        request.query.get("endpoint_type", EndpointType.ENDPOINT.w3c)
    )

    if not did:
        raise web.HTTPBadRequest(reason="Request query must include DID")

    async with ledger:
        try:
            r = await ledger.get_endpoint_for_did(did, endpoint_type)
        except LedgerError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"endpoint": r})


@docs(tags=["ledger"], summary="Fetch the current transaction author agreement, if any")
@response_schema(TAAResultSchema, 200)
async def ledger_get_taa(request: web.BaseRequest):
    """
    Request handler for fetching the transaction author agreement.

    Args:
        request: aiohttp request object

    Returns:
        The TAA information including the AML

    """
    context: RequestContext = request.app["request_context"]
    session = await context.session()
    ledger = session.inject(BaseLedger, required=False)
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
async def ledger_accept_taa(request: web.BaseRequest):
    """
    Request handler for accepting the current transaction author agreement.

    Args:
        request: aiohttp request object

    Returns:
        The DID list response

    """
    context: RequestContext = request.app["request_context"]
    session = await context.session()
    ledger = session.inject(BaseLedger, required=False)
    if not ledger:
        reason = "No Indy ledger available"
        if not session.settings.get_value("wallet.type"):
            reason += ": missing wallet-type?"
        raise web.HTTPForbidden(reason=reason)

    accept_input = await request.json()
    async with ledger:
        try:
            taa_info = await ledger.get_txn_author_agreement()
            if not taa_info["taa_required"]:
                raise web.HTTPBadRequest(
                    reason=f"Ledger {ledger.pool_name} TAA not available"
                )
            taa_record = {
                "version": accept_input["version"],
                "text": accept_input["text"],
                "digest": ledger.taa_digest(
                    accept_input["version"], accept_input["text"]
                ),
            }
            await ledger.accept_txn_author_agreement(
                taa_record, accept_input["mechanism"]
            )
        except (LedgerError, StorageError) as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})


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
