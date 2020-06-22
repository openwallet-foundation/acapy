"""Wallet admin routes."""

import json

from aiohttp import web
from aiohttp_apispec import (
    docs,
    # match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)

from marshmallow import fields, Schema

from ..ledger.base import BaseLedger
from ..ledger.error import LedgerError
from ..messaging.valid import ENDPOINT, INDY_CRED_DEF_ID, INDY_DID, INDY_RAW_PUBLIC_KEY

from .base import DIDInfo, BaseWallet
from .error import WalletError, WalletNotFoundError


class DIDSchema(Schema):
    """Result schema for a DID."""

    did = fields.Str(description="DID of interest", **INDY_DID)
    verkey = fields.Str(description="Public verification key", **INDY_RAW_PUBLIC_KEY)
    public = fields.Boolean(description="Whether DID is public", example=False)


class DIDResultSchema(Schema):
    """Result schema for a DID."""

    result = fields.Nested(DIDSchema())


class DIDListSchema(Schema):
    """Result schema for connection list."""

    results = fields.List(fields.Nested(DIDSchema()), description="DID list")


class DIDEndpointSchema(Schema):
    """Request schema to set DID endpoint; response schema to get DID endpoint."""

    did = fields.Str(description="DID of interest", required=True, **INDY_DID)
    endpoint = fields.Str(
        description="Endpoint to set (omit to delete)", required=False, **ENDPOINT
    )


class DIDListQueryStringSchema(Schema):
    """Parameters and validators for DID list request query string."""

    did = fields.Str(description="DID of interest", required=False, **INDY_DID)
    verkey = fields.Str(
        description="Verification key of interest",
        required=False,
        **INDY_RAW_PUBLIC_KEY,
    )
    public = fields.Boolean(description="Whether DID is on the ledger", required=False)


class DIDQueryStringSchema(Schema):
    """Parameters and validators for set public DID request query string."""

    did = fields.Str(description="DID of interest", required=True, **INDY_DID)


class CredDefIdMatchInfoSchema(Schema):
    """Path parameters and validators for request taking credential definition id."""

    cred_def_id = fields.Str(
        description="Credential identifier", required=True, **INDY_CRED_DEF_ID
    )


def format_did_info(info: DIDInfo):
    """Serialize a DIDInfo object."""
    if info:
        return {
            "did": info.did,
            "verkey": info.verkey,
            "public": json.dumps(bool(info.metadata.get("public"))),
        }


@docs(
    tags=["wallet"], summary="List wallet DIDs",
)
@querystring_schema(DIDListQueryStringSchema())
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
        raise web.HTTPForbidden(reason="No wallet available")
    filter_did = request.query.get("did")
    filter_verkey = request.query.get("verkey")
    filter_public = json.loads(request.query.get("public", json.dumps(None)))
    results = []
    public_did_info = await wallet.get_public_did()

    if filter_public:  # True (contrast False or None)
        if (
            public_did_info
            and (not filter_verkey or public_did_info.verkey == filter_verkey)
            and (not filter_did or public_did_info.did == filter_did)
        ):
            results.append(format_did_info(public_did_info))
    elif filter_did:
        try:
            info = await wallet.get_local_did(filter_did)
        except WalletError:
            # badly formatted DID or record not found
            info = None
        if (
            info
            and (not filter_verkey or info.verkey == filter_verkey)
            and (filter_public is None or info != public_did_info)
        ):
            results.append(format_did_info(info))
    elif filter_verkey:
        try:
            info = await wallet.get_local_did_for_verkey(filter_verkey)
        except WalletError:
            info = None
        if info and (filter_public is None or info != public_did_info):
            results.append(format_did_info(info))
    else:
        dids = await wallet.get_local_dids()
        results = []
        for info in dids:
            if filter_public is None or info != public_did_info:
                results.append(format_did_info(info))

    results.sort(key=lambda info: info["did"])
    return web.json_response({"results": results})


@docs(tags=["wallet"], summary="Create a local DID")
@response_schema(DIDResultSchema, 200)
async def wallet_create_did(request: web.BaseRequest):
    """
    Request handler for creating a new local DID in the wallet.

    Args:
        request: aiohttp request object

    Returns:
        The DID info

    """
    context = request.app["request_context"]
    wallet: BaseWallet = await context.inject(BaseWallet, required=False)
    if not wallet:
        raise web.HTTPForbidden(reason="No wallet available")
    try:
        info = await wallet.create_local_did()
    except WalletError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"result": format_did_info(info)})


@docs(tags=["wallet"], summary="Fetch the current public DID")
@response_schema(DIDResultSchema, 200)
async def wallet_get_public_did(request: web.BaseRequest):
    """
    Request handler for fetching the current public DID.

    Args:
        request: aiohttp request object

    Returns:
        The DID info

    """
    context = request.app["request_context"]
    wallet: BaseWallet = await context.inject(BaseWallet, required=False)
    if not wallet:
        raise web.HTTPForbidden(reason="No wallet available")
    try:
        info = await wallet.get_public_did()
    except WalletError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"result": format_did_info(info)})


@docs(tags=["wallet"], summary="Assign the current public DID")
@querystring_schema(DIDQueryStringSchema())
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
        raise web.HTTPForbidden(reason="No wallet available")
    did = request.query.get("did")
    if not did:
        raise web.HTTPBadRequest(reason="Request query must include DID")

    try:
        ledger = await context.inject(BaseLedger, required=False)
        if not ledger:
            reason = f"No ledger available"
            if not context.settings.get_value("wallet.type"):
                reason += ": missing wallet-type?"
            raise web.HTTPForbidden(reason=reason)

        async with ledger:
            if not await ledger.get_key_for_did(did):
                raise web.HTTPNotFound(reason=f"DID {did} is not public")

        did_info = await wallet.get_local_did(did)
        info = await wallet.set_public_did(did)
        if info:
            # Publish endpoint if necessary
            endpoint = did_info.metadata.get(
                "endpoint", context.settings.get("default_endpoint")
            )
            async with ledger:
                await ledger.update_endpoint_for_did(info.did, endpoint)
    except WalletNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (LedgerError, WalletError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"result": format_did_info(info)})


@docs(tags=["wallet"], summary="Update endpoint in wallet and, if public, on ledger")
@request_schema(DIDEndpointSchema)
async def wallet_set_did_endpoint(request: web.BaseRequest):
    """
    Request handler for setting an endpoint for a public or local DID.

    Args:
        request: aiohttp request object
    """
    context = request.app["request_context"]
    wallet: BaseWallet = await context.inject(BaseWallet, required=False)
    if not wallet:
        raise web.HTTPForbidden(reason="No wallet available")

    body = await request.json()
    did = body["did"]
    endpoint = body.get("endpoint")

    try:
        did_info = await wallet.get_local_did(did)
        metadata = {**did_info.metadata}
        if "endpoint" in metadata:
            metadata.pop("endpoint")
        metadata["endpoint"] = endpoint  # set null to clear so making public sends null

        wallet_public_didinfo = await wallet.get_public_did()
        if wallet_public_didinfo and wallet_public_didinfo.did == did:
            # if public DID, set endpoint on ledger first
            ledger = await context.inject(BaseLedger, required=False)
            if not ledger:
                reason = f"No ledger available but DID {did} is public"
                if not context.settings.get_value("wallet.type"):
                    reason += ": missing wallet-type?"
                raise web.HTTPForbidden(reason=reason)
            async with ledger:
                await ledger.update_endpoint_for_did(did, endpoint)

        await wallet.replace_local_did_metadata(did, metadata)
    except WalletNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (LedgerError, WalletError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})


@docs(tags=["wallet"], summary="Query DID endpoint in wallet")
@querystring_schema(DIDQueryStringSchema())
@response_schema(DIDEndpointSchema, 200)
async def wallet_get_did_endpoint(request: web.BaseRequest):
    """
    Request handler for getting the current DID endpoint from the wallet.

    Args:
        request: aiohttp request object

    Returns:
        The updated DID info

    """
    context = request.app["request_context"]
    wallet: BaseWallet = await context.inject(BaseWallet, required=False)
    if not wallet:
        raise web.HTTPForbidden(reason="No wallet available")
    did = request.query.get("did")
    if not did:
        raise web.HTTPBadRequest(reason="Request query must include DID")
    try:
        did_info = await wallet.get_local_did(did)
        endpoint = did_info.metadata.get("endpoint")
    except WalletNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except WalletError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"did": did, "endpoint": endpoint})


@docs(tags=["wallet"], summary="Rotate keypair for a local non-public DID")
@querystring_schema(DIDQueryStringSchema())
async def wallet_rotate_did_keypair(request: web.BaseRequest):
    """
    Request handler for rotating local DID keypair.

    Args:
        request: aiohttp request object

    Returns:
        An empty JSON response

    """
    context = request.app["request_context"]
    wallet: BaseWallet = await context.inject(BaseWallet, required=False)
    if not wallet:
        raise web.HTTPForbidden(reason="No wallet available")
    did = request.query.get("did")
    if not did:
        raise web.HTTPBadRequest(reason="Request query must include DID")
    try:
        did_info = await wallet.get_local_did(did)
        if did_info.metadata.get("public", False):
            # call from ledger API instead to propagate through ledger NYM transaction
            raise web.HTTPBadRequest(reason=f"DID {did} is public")
        await wallet.rotate_did_keypair_start(did)  # do not take seed over the wire
        await wallet.rotate_did_keypair_apply(did)
    except WalletNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except WalletError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/wallet/did", wallet_did_list, allow_head=False),
            web.post("/wallet/did/create", wallet_create_did),
            web.get("/wallet/did/public", wallet_get_public_did, allow_head=False),
            web.post("/wallet/did/public", wallet_set_public_did),
            web.post("/wallet/set-did-endpoint", wallet_set_did_endpoint),
            web.get(
                "/wallet/get-did-endpoint", wallet_get_did_endpoint, allow_head=False
            ),
            web.patch("/wallet/did/local/rotate-keypair", wallet_rotate_did_keypair),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "wallet",
            "description": "DID and tag policy management",
            "externalDocs": {
                "description": "Design",
                "url": (
                    "https://github.com/hyperledger/indy-sdk/tree/"
                    "master/docs/design/003-wallet-storage"
                ),
            },
        }
    )
