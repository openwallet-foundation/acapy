"""Wallet admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, response_schema

from marshmallow import fields, Schema

from .base import DIDInfo, BaseWallet
from .error import WalletError


class DIDSchema(Schema):
    """Result schema for a DID."""

    did = fields.Str()
    verkey = fields.Str()
    public = fields.Bool()


class DIDResultSchema(Schema):
    """Result schema for a DID."""

    result = fields.Nested(DIDSchema())


class DIDListSchema(Schema):
    """Result schema for connection list."""

    results = fields.List(fields.Nested(DIDSchema()))


def format_did_info(info: DIDInfo):
    """Serialize a DIDInfo object."""
    if info:
        return {
            "did": info.did,
            "verkey": info.verkey,
            "public": info.metadata
            and info.metadata.get("public")
            and "true"
            or "false",
        }


@docs(
    tags=["wallet"],
    summary="List wallet DIDs",
    parameters=[
        {"name": "did", "in": "query", "schema": {"type": "string"}, "required": False},
        {
            "name": "verkey",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
        {
            "name": "public",
            "in": "query",
            "schema": {"type": "boolean"},
            "required": False,
        },
    ],
)
@response_schema(DIDListSchema, 200)
async def wallet_did_list(request: web.BaseRequest):
    """
    Request handler for searching wallet DIDs.

    Args:
        request: aiohttp request object

    Returns:
        The DID list response

    """
    context = request.app["request_context"]
    wallet: BaseWallet = await context.inject(BaseWallet, required=False)
    if not wallet:
        raise web.HTTPForbidden()
    filter_did = request.query.get("did")
    filter_verkey = request.query.get("verkey")
    filter_public = request.query.get("public")
    results = []

    if filter_public and filter_public == "true":
        info = await wallet.get_public_did()
        if (
            info
            and (not filter_verkey or info.verkey == filter_verkey)
            and (not filter_did or info.did == filter_did)
        ):
            results.append(format_did_info(info))
    elif filter_did:
        try:
            info = await wallet.get_local_did(filter_did)
        except WalletError:
            # badly formatted DID or record not found
            info = None
        if info and (not filter_verkey or info.verkey == filter_verkey):
            results.append(format_did_info(info))
    elif filter_verkey:
        try:
            info = await wallet.get_local_did_for_verkey(filter_verkey)
        except WalletError:
            info = None
        if info:
            results.append(format_did_info(info))
    else:
        dids = await wallet.get_local_dids()
        results = []
        for info in dids:
            results.append(format_did_info(info))
    results.sort(key=lambda info: info["did"])
    return web.json_response({"results": results})


@docs(tags=["wallet"], summary="Create a local DID")
@response_schema(DIDResultSchema, 200)
async def wallet_create_did(request: web.BaseRequest):
    """
    Request handler for creating a new wallet DID.

    Args:
        request: aiohttp request object

    Returns:
        The DID list response

    """
    context = request.app["request_context"]
    wallet: BaseWallet = await context.inject(BaseWallet, required=False)
    if not wallet:
        raise web.HTTPForbidden()
    info = await wallet.create_local_did()
    return web.json_response({"result": format_did_info(info)})


@docs(tags=["wallet"], summary="Fetch the current public DID")
@response_schema(DIDResultSchema, 200)
async def wallet_get_public_did(request: web.BaseRequest):
    """
    Request handler for fetching the current public DID.

    Args:
        request: aiohttp request object

    Returns:
        The DID list response

    """
    context = request.app["request_context"]
    wallet: BaseWallet = await context.inject(BaseWallet, required=False)
    if not wallet:
        raise web.HTTPForbidden()
    info = await wallet.get_public_did()
    return web.json_response({"result": format_did_info(info)})


@docs(
    tags=["wallet"],
    summary="Assign the current public DID",
    parameters=[
        {"name": "did", "in": "query", "schema": {"type": "string"}, "required": True}
    ],
)
@response_schema(DIDResultSchema, 200)
async def wallet_set_public_did(request: web.BaseRequest):
    """
    Request handler for setting the current public DID.

    Args:
        request: aiohttp request object

    Returns:
        The updated DID info

    """
    context = request.app["request_context"]
    wallet: BaseWallet = await context.inject(BaseWallet, required=False)
    if not wallet:
        raise web.HTTPForbidden()
    did = request.query.get("did")
    if not did:
        raise web.HTTPBadRequest()
    try:
        info = await wallet.get_local_did(did)
    except WalletError:
        # DID not found or not in valid format
        raise web.HTTPBadRequest()
    info = await wallet.set_public_did(did)
    return web.json_response({"result": format_did_info(info)})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/wallet/did", wallet_did_list),
            web.post("/wallet/did/create", wallet_create_did),
            web.get("/wallet/did/public", wallet_get_public_did),
            web.post("/wallet/did/public", wallet_set_public_did),
        ]
    )
