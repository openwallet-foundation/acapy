"""Ledger admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, request_schema, response_schema

from marshmallow import fields, Schema, validate

from ..messaging.valid import INDY_DID, INDY_RAW_PUBLIC_KEY
from ..storage.error import StorageError
from ..wallet.error import WalletError
from .base import BaseLedger
from .indy import Role
from .error import BadLedgerRequestError, LedgerError, LedgerTransactionError


class AMLRecordSchema(Schema):
    """Ledger AML record."""

    version = fields.Str()
    aml = fields.Dict(fields.Str(), fields.Str())
    amlContext = fields.Str()


class TAARecordSchema(Schema):
    """Ledger TAA record."""

    version = fields.Str()
    text = fields.Str()
    digest = fields.Str()


class TAAAcceptanceSchema(Schema):
    """TAA acceptance record."""

    mechanism = fields.Str()
    time = fields.Int()


class TAAInfoSchema(Schema):
    """Transaction author agreement info."""

    aml_record = fields.Nested(AMLRecordSchema())
    taa_record = fields.Nested(TAARecordSchema())
    taa_required = fields.Bool()
    taa_accepted = fields.Nested(TAAAcceptanceSchema())


class TAAResultSchema(Schema):
    """Result schema for a transaction author agreement."""

    result = fields.Nested(TAAInfoSchema())


class TAAAcceptSchema(Schema):
    """Input schema for accepting the TAA."""

    version = fields.Str()
    text = fields.Str()
    mechanism = fields.Str()


class RegisterLedgerNymQueryStringSchema(Schema):
    """Query string parameters and validators for register ledger nym request."""

    did = fields.Str(description="DID to register", required=True, **INDY_DID,)
    verkey = fields.Str(
        description="Verification key", required=True, **INDY_RAW_PUBLIC_KEY
    )
    alias = fields.Str(description="Alias", required=False, example="Barry",)
    role = fields.Str(
        description="Role",
        required=False,
        validate=validate.OneOf(
            [r.name for r in Role if isinstance(r.value[0], int)] + ["reset"]
        ),
    )


class QueryStringDIDSchema(Schema):
    """Parameters and validators for query string with DID only."""

    did = fields.Str(description="DID of interest", required=True, **INDY_DID)


@docs(
    tags=["ledger"], summary="Send a NYM registration to the ledger.",
)
@querystring_schema(RegisterLedgerNymQueryStringSchema())
async def register_ledger_nym(request: web.BaseRequest):
    """
    Request handler for registering a NYM with the ledger.

    Args:
        request: aiohttp request object
    """
    context = request.app["request_context"]
    ledger = await context.inject(BaseLedger, required=False)
    if not ledger:
        reason = "No ledger available"
        if not context.settings.get_value("wallet.type"):
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
    return web.json_response({"success": success})


@docs(tags=["ledger"], summary="Rotate key pair for public DID.")
async def rotate_public_did_keypair(request: web.BaseRequest):
    """
    Request handler for rotating key pair associated with public DID.

    Args:
        request: aiohttp request object
    """
    context = request.app["request_context"]
    ledger = await context.inject(BaseLedger, required=False)
    if not ledger:
        reason = "No ledger available"
        if not context.settings.get_value("wallet.type"):
            reason += ": missing wallet-type?"
        raise web.HTTPForbidden(reason=reason)
    async with ledger:
        try:
            await ledger.rotate_public_did_keypair()  # do not take seed over the wire
        except (WalletError, BadLedgerRequestError) as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})


@docs(
    tags=["ledger"], summary="Get the verkey for a DID from the ledger.",
)
@querystring_schema(QueryStringDIDSchema())
async def get_did_verkey(request: web.BaseRequest):
    """
    Request handler for getting a verkey for a DID from the ledger.

    Args:
        request: aiohttp request object
    """
    context = request.app["request_context"]
    ledger = await context.inject(BaseLedger, required=False)
    if not ledger:
        reason = "No ledger available"
        if not context.settings.get_value("wallet.type"):
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
    tags=["ledger"], summary="Get the endpoint for a DID from the ledger.",
)
@querystring_schema(QueryStringDIDSchema())
async def get_did_endpoint(request: web.BaseRequest):
    """
    Request handler for getting a verkey for a DID from the ledger.

    Args:
        request: aiohttp request object
    """
    context = request.app["request_context"]
    ledger = await context.inject(BaseLedger, required=False)
    if not ledger:
        reason = "No ledger available"
        if not context.settings.get_value("wallet.type"):
            reason += ": missing wallet-type?"
        raise web.HTTPForbidden(reason=reason)

    did = request.query.get("did")
    if not did:
        raise web.HTTPBadRequest(reason="Request query must include DID")

    async with ledger:
        try:
            r = await ledger.get_endpoint_for_did(did)
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
    context = request.app["request_context"]
    ledger: BaseLedger = await context.inject(BaseLedger, required=False)
    if not ledger or ledger.LEDGER_TYPE != "indy":
        reason = "No indy ledger available"
        if not context.settings.get_value("wallet.type"):
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
    context = request.app["request_context"]
    ledger: BaseLedger = await context.inject(BaseLedger, required=False)
    if not ledger or ledger.LEDGER_TYPE != "indy":
        reason = "No indy ledger available"
        if not context.settings.get_value("wallet.type"):
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
