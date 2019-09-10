"""Ledger admin routes."""

from aiohttp import web
from aiohttp_apispec import docs

from .base import BaseLedger
from .error import LedgerTransactionError


@docs(
    tags=["ledger"],
    summary="Send a NYM registration to the ledger.",
    parameters=[
        {"name": "did", "in": "query", "schema": {"type": "string"},
         "required": True},
        {"name": "verkey", "in": "query", "schema": {"type": "string"},
         "required": True},
        {"name": "alias", "in": "query", "schema": {"type": "string"},
         "required": False},
        {"name": "role", "in": "query", "schema": {"type": "string"},
         "required": False}
    ]
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
    ]
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
    ]
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


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.post("/ledger/register-nym", register_ledger_nym),
            web.get("/ledger/did-verkey", get_did_verkey),
            web.get("/ledger/did-endpoint", get_did_endpoint)
        ]
    )
