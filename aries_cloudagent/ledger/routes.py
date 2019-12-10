"""Ledger admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema

from marshmallow import fields, Schema

from .base import BaseLedger
from .error import LedgerTransactionError


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


@docs(
    tags=["ledger"],
    summary="Send a NYM registration to the ledger.",
    parameters=[
        {"name": "did", "in": "query", "schema": {"type": "string"}, "required": True},
        {
            "name": "verkey",
            "in": "query",
            "schema": {"type": "string"},
            "required": True,
        },
        {
            "name": "alias",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
        {
            "name": "role",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
    ],
)
async def register_ledger_nym(request: web.BaseRequest):
    """
    Request handler for registering a NYM with the ledger.

    Args:
        request: aiohttp request object
    """
    context = request.app["request_context"]
    ledger = await context.inject(BaseLedger, required=False)
    if not ledger:
        raise web.HTTPForbidden()

    did = request.query.get("did")
    verkey = request.query.get("verkey")
    if not did or not verkey:
        raise web.HTTPBadRequest()

    alias, role = request.query.get("alias"), request.query.get("role")
    success = False
    async with ledger:
        try:
            await ledger.register_nym(did, verkey, alias, role)
            success = True
        except LedgerTransactionError as e:
            raise web.HTTPForbidden(text=e.message)
    return web.json_response({"success": success})


@docs(
    tags=["ledger"],
    summary="Get the verkey for a DID from the ledger.",
    parameters=[
        {"name": "did", "in": "query", "schema": {"type": "string"}, "required": True}
    ],
)
async def get_did_verkey(request: web.BaseRequest):
    """
    Request handler for getting a verkey for a DID from the ledger.

    Args:
        request: aiohttp request object
    """
    context = request.app["request_context"]
    ledger = await context.inject(BaseLedger, required=False)
    if not ledger:
        raise web.HTTPForbidden()

    did = request.query.get("did")
    if not did:
        raise web.HTTPBadRequest()

    async with ledger:
        r = await ledger.get_key_for_did(did)
    return web.json_response({"verkey": r})


@docs(
    tags=["ledger"],
    summary="Get the endpoint for a DID from the ledger.",
    parameters=[
        {"name": "did", "in": "query", "schema": {"type": "string"}, "required": True}
    ],
)
async def get_did_endpoint(request: web.BaseRequest):
    """
    Request handler for getting a verkey for a DID from the ledger.

    Args:
        request: aiohttp request object
    """
    context = request.app["request_context"]
    ledger = await context.inject(BaseLedger, required=False)
    if not ledger:
        raise web.HTTPForbidden()

    did = request.query.get("did")
    if not did:
        raise web.HTTPBadRequest()

    async with ledger:
        r = await ledger.get_endpoint_for_did(did)
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
        raise web.HTTPForbidden()

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
        raise web.HTTPForbidden()

    accept_input = await request.json()
    taa_info = await ledger.get_txn_author_agreement()
    if not taa_info["taa_required"]:
        raise web.HTTPBadRequest()
    taa_record = {
        "version": accept_input["version"],
        "text": accept_input["text"],
        "digest": ledger.taa_digest(accept_input["version"], accept_input["text"]),
    }
    await ledger.accept_txn_author_agreement(taa_record, accept_input["mechanism"])
    return web.json_response({})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.post("/ledger/register-nym", register_ledger_nym),
            web.get("/ledger/did-verkey", get_did_verkey),
            web.get("/ledger/did-endpoint", get_did_endpoint),
            web.get("/ledger/taa", ledger_get_taa),
            web.post("/ledger/taa/accept", ledger_accept_taa),
        ]
    )
