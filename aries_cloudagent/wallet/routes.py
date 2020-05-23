"""Wallet admin routes."""

import json

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)

from marshmallow import fields, Schema

from ..ledger.base import BaseLedger
from ..messaging.valid import INDY_CRED_DEF_ID, INDY_DID, INDY_RAW_PUBLIC_KEY

from .base import DIDInfo, BaseWallet
from .error import WalletError


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


class GetTagPolicyResultSchema(Schema):
    """Result schema for tagging policy get request."""

    taggables = fields.List(
        fields.Str(description="Taggable attribute", example="score"),
        description=(
            "List of attributes taggable for credential search under current policy"
        ),
    )


class SetTagPolicyRequestSchema(Schema):
    """Request schema for tagging policy set request."""

    taggables = fields.List(
        fields.Str(description="Taggable attribute", example="score"),
        description="List of attributes to set taggable for credential search",
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
        raise web.HTTPForbidden()
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
    Request handler for creating a new wallet DID.

    Args:
        request: aiohttp request object

    Returns:
        The DID info

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
        The DID info

    """
    context = request.app["request_context"]
    wallet: BaseWallet = await context.inject(BaseWallet, required=False)
    if not wallet:
        raise web.HTTPForbidden()
    info = await wallet.get_public_did()
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
        raise web.HTTPForbidden()
    did = request.query.get("did")
    if not did:
        raise web.HTTPBadRequest()
    try:
        await wallet.get_local_did(did)
    except WalletError:
        # DID not found or not in valid format
        raise web.HTTPBadRequest()
    info = await wallet.set_public_did(did)
    if info:
        # Publish endpoint if necessary
        endpoint = context.settings.get("default_endpoint")
        ledger = await context.inject(BaseLedger, required=False)
        if ledger:
            async with ledger:
                await ledger.update_endpoint_for_did(info.did, endpoint)

    return web.json_response({"result": format_did_info(info)})


@docs(tags=["wallet"], summary="Rotate keys for a local non-public DID")
@querystring_schema(DIDQueryStringSchema())
async def wallet_rotate_did_keys(request: web.BaseRequest):
    """
    Request handler for rotating local DID keys.
    """
    context = request.app["request_context"]
    wallet: BaseWallet = await context.inject(BaseWallet, required=False)
    if not wallet:
        raise web.HTTPForbidden()
    did = request.query.get("did")
    if not did:
        raise web.HTTPBadRequest()
    try:
        did_info = await wallet.get_local_did(did)
    except WalletError:
        # DID not found or not in valid format
        raise web.HTTPBadRequest()
    else:
        if did_info.metadata.get("public", False):
            # call from ledger API to propagate through ledger NYM transaction
            raise web.HTTPBadRequest()

    await wallet.rotate_did_keys_start(did)  # do not take seed over the wire
    await wallet.rotate_did_keys_apply(did)

    return web.json_response({})


@docs(tags=["wallet"], summary="Get the tagging policy for a credential definition")
@match_info_schema(CredDefIdMatchInfoSchema())
@response_schema(GetTagPolicyResultSchema())
async def wallet_get_tagging_policy(request: web.BaseRequest):
    """
    Request handler for getting the tag policy associated with a cred def.

    Args:
        request: aiohttp request object

    Returns:
        A JSON object containing the tagging policy

    """
    context = request.app["request_context"]

    credential_definition_id = request.match_info["cred_def_id"]

    wallet: BaseWallet = await context.inject(BaseWallet, required=False)
    if not wallet or wallet.WALLET_TYPE != "indy":
        raise web.HTTPForbidden()
    result = await wallet.get_credential_definition_tag_policy(credential_definition_id)
    return web.json_response({"taggables": result})


@docs(tags=["wallet"], summary="Set the tagging policy for a credential definition")
@match_info_schema(CredDefIdMatchInfoSchema())
@request_schema(SetTagPolicyRequestSchema())
async def wallet_set_tagging_policy(request: web.BaseRequest):
    """
    Request handler for setting the tag policy associated with a cred def.

    Args:
        request: aiohttp request object

    Returns:
        An empty JSON response

    """
    context = request.app["request_context"]

    credential_definition_id = request.match_info["cred_def_id"]

    body = await request.json()
    taggables = body.get("taggables")  # None for all attrs, [] for no attrs

    wallet: BaseWallet = await context.inject(BaseWallet, required=False)
    if not wallet or wallet.WALLET_TYPE != "indy":
        raise web.HTTPForbidden()
    await wallet.set_credential_definition_tag_policy(
        credential_definition_id, taggables
    )
    return web.json_response({})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/wallet/did", wallet_did_list, allow_head=False),
            web.post("/wallet/did/create", wallet_create_did),
            web.get("/wallet/did/public", wallet_get_public_did, allow_head=False),
            web.post("/wallet/did/public", wallet_set_public_did),
            web.patch("/wallet/did/local/rotate-keys", wallet_rotate_did_keys),
            web.get(
                "/wallet/tag-policy/{cred_def_id}",
                wallet_get_tagging_policy,
                allow_head=False,
            ),
            web.post("/wallet/tag-policy/{cred_def_id}", wallet_set_tagging_policy),
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
