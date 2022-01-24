"""Wallet admin routes."""

from aiohttp import web
from aiohttp_apispec import (
    docs,
    querystring_schema,
    request_schema,
    response_schema,
)
import logging
from marshmallow import fields, validate

from ..admin.request_context import AdminRequestContext
from ..core.event_bus import Event, EventBus
from ..core.profile import Profile
from ..ledger.base import BaseLedger
from ..ledger.endpoint_type import EndpointType
from ..ledger.error import LedgerConfigError, LedgerError
from ..messaging.models.openapi import OpenAPISchema
from ..messaging.valid import (
    DID_POSTURE,
    INDY_OR_KEY_DID,
    INDY_DID,
    ENDPOINT,
    ENDPOINT_TYPE,
    INDY_RAW_PUBLIC_KEY,
)
from ..multitenant.base import BaseMultitenantManager
from ..protocols.endorse_transaction.v1_0.util import (
    is_author_role,
)

from .base import BaseWallet
from .did_info import DIDInfo
from .did_posture import DIDPosture
from .did_method import DIDMethod
from .error import WalletError, WalletNotFoundError
from .key_type import KeyType
from .util import EVENT_LISTENER_PATTERN

LOGGER = logging.getLogger(__name__)


class WalletModuleResponseSchema(OpenAPISchema):
    """Response schema for Wallet Module."""


class DIDSchema(OpenAPISchema):
    """Result schema for a DID."""

    did = fields.Str(description="DID of interest", **INDY_OR_KEY_DID)
    verkey = fields.Str(description="Public verification key", **INDY_RAW_PUBLIC_KEY)
    posture = fields.Str(
        description=(
            "Whether DID is current public DID, "
            "posted to ledger but not current public DID, "
            "or local to the wallet"
        ),
        **DID_POSTURE,
    )
    method = fields.Str(
        description="Did method associated with the DID",
        example=DIDMethod.SOV.method_name,
        validate=validate.OneOf([method.method_name for method in DIDMethod]),
    )
    key_type = fields.Str(
        description="Key type associated with the DID",
        example=KeyType.ED25519.key_type,
        validate=validate.OneOf(
            [KeyType.ED25519.key_type, KeyType.BLS12381G2.key_type]
        ),
    )


class DIDResultSchema(OpenAPISchema):
    """Result schema for a DID."""

    result = fields.Nested(DIDSchema())


class DIDListSchema(OpenAPISchema):
    """Result schema for connection list."""

    results = fields.List(fields.Nested(DIDSchema()), description="DID list")


class DIDEndpointWithTypeSchema(OpenAPISchema):
    """Request schema to set DID endpoint of particular type."""

    did = fields.Str(description="DID of interest", required=True, **INDY_DID)
    endpoint = fields.Str(
        description="Endpoint to set (omit to delete)", required=False, **ENDPOINT
    )
    endpoint_type = fields.Str(
        description=(
            f"Endpoint type to set (default '{EndpointType.ENDPOINT.w3c}'); "
            "affects only public or posted DIDs"
        ),
        required=False,
        **ENDPOINT_TYPE,
    )


class DIDEndpointSchema(OpenAPISchema):
    """Request schema to set DID endpoint; response schema to get DID endpoint."""

    did = fields.Str(description="DID of interest", required=True, **INDY_DID)
    endpoint = fields.Str(
        description="Endpoint to set (omit to delete)", required=False, **ENDPOINT
    )


class DIDListQueryStringSchema(OpenAPISchema):
    """Parameters and validators for DID list request query string."""

    did = fields.Str(description="DID of interest", required=False, **INDY_OR_KEY_DID)
    verkey = fields.Str(
        description="Verification key of interest",
        required=False,
        **INDY_RAW_PUBLIC_KEY,
    )
    posture = fields.Str(
        description=(
            "Whether DID is current public DID, "
            "posted to ledger but current public DID, "
            "or local to the wallet"
        ),
        required=False,
        **DID_POSTURE,
    )
    method = fields.Str(
        required=False,
        example=DIDMethod.KEY.method_name,
        validate=validate.OneOf([DIDMethod.KEY.method_name, DIDMethod.SOV.method_name]),
        description="DID method to query for. e.g. sov to only fetch indy/sov DIDs",
    )
    key_type = fields.Str(
        required=False,
        example=KeyType.ED25519.key_type,
        validate=validate.OneOf(
            [KeyType.ED25519.key_type, KeyType.BLS12381G2.key_type]
        ),
        description="Key type to query for.",
    )


class DIDQueryStringSchema(OpenAPISchema):
    """Parameters and validators for set public DID request query string."""

    did = fields.Str(description="DID of interest", required=True, **INDY_DID)


class DIDCreateOptionsSchema(OpenAPISchema):
    """Parameters and validators for create DID options."""

    key_type = fields.Str(
        required=True,
        example=KeyType.ED25519.key_type,
        validate=validate.OneOf(
            [KeyType.ED25519.key_type, KeyType.BLS12381G2.key_type]
        ),
    )


class DIDCreateSchema(OpenAPISchema):
    """Parameters and validators for create DID endpoint."""

    method = fields.Str(
        required=False,
        default=DIDMethod.SOV.method_name,
        example=DIDMethod.SOV.method_name,
        validate=validate.OneOf([DIDMethod.KEY.method_name, DIDMethod.SOV.method_name]),
    )

    options = fields.Nested(
        DIDCreateOptionsSchema,
        required=False,
        description="To define a key type for a did:key",
    )


def format_did_info(info: DIDInfo):
    """Serialize a DIDInfo object."""
    if info:
        return {
            "did": info.did,
            "verkey": info.verkey,
            "posture": DIDPosture.get(info.metadata).moniker,
            "key_type": info.key_type.key_type,
            "method": info.method.method_name,
        }


@docs(tags=["wallet"], summary="List wallet DIDs")
@querystring_schema(DIDListQueryStringSchema())
@response_schema(DIDListSchema, 200, description="")
async def wallet_did_list(request: web.BaseRequest):
    """
    Request handler for searching wallet DIDs.

    Args:
        request: aiohttp request object

    Returns:
        The DID list response

    """
    context: AdminRequestContext = request["context"]
    filter_did = request.query.get("did")
    filter_verkey = request.query.get("verkey")
    filter_method = DIDMethod.from_method(request.query.get("method"))
    filter_posture = DIDPosture.get(request.query.get("posture"))
    filter_key_type = KeyType.from_key_type(request.query.get("key_type"))
    results = []
    async with context.session() as session:
        wallet = session.inject_or(BaseWallet)
        if not wallet:
            raise web.HTTPForbidden(reason="No wallet available")
        if filter_posture is DIDPosture.PUBLIC:
            public_did_info = await wallet.get_public_did()
            if (
                public_did_info
                and (not filter_verkey or public_did_info.verkey == filter_verkey)
                and (not filter_did or public_did_info.did == filter_did)
                and (not filter_method or public_did_info.method == filter_method)
                and (not filter_key_type or public_did_info.key_type == filter_key_type)
            ):
                results.append(format_did_info(public_did_info))
        elif filter_posture is DIDPosture.POSTED:
            results = []
            posted_did_infos = await wallet.get_posted_dids()
            for info in posted_did_infos:
                if (
                    (not filter_verkey or info.verkey == filter_verkey)
                    and (not filter_did or info.did == filter_did)
                    and (not filter_method or info.method == filter_method)
                    and (not filter_key_type or info.key_type == filter_key_type)
                ):
                    results.append(format_did_info(info))
        elif filter_did:
            try:
                info = await wallet.get_local_did(filter_did)
            except WalletError:
                # badly formatted DID or record not found
                info = None
            if (
                info
                and (not filter_verkey or info.verkey == filter_verkey)
                and (not filter_method or info.method == filter_method)
                and (not filter_key_type or info.key_type == filter_key_type)
                and (
                    filter_posture is None
                    or (
                        filter_posture is DIDPosture.WALLET_ONLY
                        and not info.metadata.get("posted")
                    )
                )
            ):
                results.append(format_did_info(info))
        elif filter_verkey:
            try:
                info = await wallet.get_local_did_for_verkey(filter_verkey)
            except WalletError:
                info = None
            if (
                info
                and (not filter_method or info.method == filter_method)
                and (not filter_key_type or info.key_type == filter_key_type)
                and (
                    filter_posture is None
                    or (
                        filter_posture is DID_POSTURE.WALLET_ONLY
                        and not info.metadata.get("posted")
                    )
                )
            ):
                results.append(format_did_info(info))
        else:
            dids = await wallet.get_local_dids()
            results = [
                format_did_info(info)
                for info in dids
                if (
                    filter_posture is None
                    or DIDPosture.get(info.metadata) is DIDPosture.WALLET_ONLY
                )
                and (not filter_method or info.method == filter_method)
                and (not filter_key_type or info.key_type == filter_key_type)
            ]

    results.sort(
        key=lambda info: (DIDPosture.get(info["posture"]).ordinal, info["did"])
    )

    return web.json_response({"results": results})


@docs(tags=["wallet"], summary="Create a local DID")
@request_schema(DIDCreateSchema())
@response_schema(DIDResultSchema, 200, description="")
async def wallet_create_did(request: web.BaseRequest):
    """
    Request handler for creating a new local DID in the wallet.

    Args:
        request: aiohttp request object

    Returns:
        The DID info

    """
    context: AdminRequestContext = request["context"]

    try:
        body = await request.json()
    except Exception:
        body = {}

    # set default method and key type for backwards compat
    key_type = (
        KeyType.from_key_type(body.get("options", {}).get("key_type"))
        or KeyType.ED25519
    )
    method = DIDMethod.from_method(body.get("method")) or DIDMethod.SOV

    if not method.supports_key_type(key_type):
        raise web.HTTPForbidden(
            reason=(
                f"method {method.method_name} does not"
                f" support key type {key_type.key_type}"
            )
        )
    info = None
    async with context.session() as session:
        wallet = session.inject_or(BaseWallet)
        if not wallet:
            raise web.HTTPForbidden(reason="No wallet available")
        try:
            info = await wallet.create_local_did(method=method, key_type=key_type)

        except WalletError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"result": format_did_info(info)})


@docs(tags=["wallet"], summary="Fetch the current public DID")
@response_schema(DIDResultSchema, 200, description="")
async def wallet_get_public_did(request: web.BaseRequest):
    """
    Request handler for fetching the current public DID.

    Args:
        request: aiohttp request object

    Returns:
        The DID info

    """
    context: AdminRequestContext = request["context"]
    info = None
    async with context.session() as session:
        wallet = session.inject_or(BaseWallet)
        if not wallet:
            raise web.HTTPForbidden(reason="No wallet available")
        try:
            info = await wallet.get_public_did()
        except WalletError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"result": format_did_info(info)})


@docs(tags=["wallet"], summary="Assign the current public DID")
@querystring_schema(DIDQueryStringSchema())
@response_schema(DIDResultSchema, 200, description="")
async def wallet_set_public_did(request: web.BaseRequest):
    """
    Request handler for setting the current public DID.

    Args:
        request: aiohttp request object

    Returns:
        The updated DID info

    """
    context: AdminRequestContext = request["context"]
    async with context.session() as session:
        wallet = session.inject_or(BaseWallet)
        if not wallet:
            raise web.HTTPForbidden(reason="No wallet available")

    did = request.query.get("did")
    if not did:
        raise web.HTTPBadRequest(reason="Request query must include DID")

    info: DIDInfo = None
    try:
        info = await promote_wallet_public_did(
            context.profile, context, context.session, did
        )
    except LookupError as err:
        raise web.HTTPNotFound(reason=str(err)) from err
    except PermissionError as err:
        raise web.HTTPForbidden(reason=str(err)) from err
    except WalletNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (LedgerError, WalletError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"result": format_did_info(info)})


async def promote_wallet_public_did(
    profile: Profile, context: AdminRequestContext, session_fn, did: str
) -> DIDInfo:
    """Promote supplied DID to the wallet public DID."""

    # if running in multitenant mode this will be the sub-wallet
    wallet_id = context.settings.get("wallet.id")

    info: DIDInfo = None
    ledger = profile.inject_or(BaseLedger)
    if not ledger:
        reason = "No ledger available"
        if not context.settings.get_value("wallet.type"):
            reason += ": missing wallet-type?"
        raise PermissionError(reason)

    async with ledger:
        if not await ledger.get_key_for_did(did):
            raise LookupError(f"DID {did} is not posted to the ledger")
    did_info: DIDInfo = None
    async with session_fn() as session:
        wallet = session.inject_or(BaseWallet)
        did_info = await wallet.get_local_did(did)
        info = await wallet.set_public_did(did_info)
    if info:
        # Publish endpoint if necessary
        endpoint = did_info.metadata.get("endpoint")

        if not endpoint:
            async with session_fn() as session:
                wallet = session.inject_or(BaseWallet)
                endpoint = context.settings.get("default_endpoint")
                await wallet.set_did_endpoint(info.did, endpoint, ledger)

        async with ledger:
            await ledger.update_endpoint_for_did(info.did, endpoint)

        # Multitenancy setup
        multitenant_mgr = profile.inject_or(BaseMultitenantManager)
        # Add multitenant relay mapping so implicit invitations are still routed
        if multitenant_mgr and wallet_id:
            await multitenant_mgr.add_key(wallet_id, info.verkey, skip_if_exists=True)

    return info


@docs(
    tags=["wallet"], summary="Update endpoint in wallet and on ledger if posted to it"
)
@request_schema(DIDEndpointWithTypeSchema)
@response_schema(WalletModuleResponseSchema(), description="")
async def wallet_set_did_endpoint(request: web.BaseRequest):
    """
    Request handler for setting an endpoint for a DID.

    Args:
        request: aiohttp request object
    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    did = body["did"]
    endpoint = body.get("endpoint")
    endpoint_type = EndpointType.get(
        body.get("endpoint_type", EndpointType.ENDPOINT.w3c)
    )
    async with context.session() as session:
        wallet = session.inject_or(BaseWallet)
        if not wallet:
            raise web.HTTPForbidden(reason="No wallet available")

        try:
            ledger = context.profile.inject_or(BaseLedger)
            await wallet.set_did_endpoint(did, endpoint, ledger, endpoint_type)
        except WalletNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err
        except LedgerConfigError as err:
            raise web.HTTPForbidden(reason=err.roll_up) from err
        except (LedgerError, WalletError) as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})


@docs(tags=["wallet"], summary="Query DID endpoint in wallet")
@querystring_schema(DIDQueryStringSchema())
@response_schema(DIDEndpointSchema, 200, description="")
async def wallet_get_did_endpoint(request: web.BaseRequest):
    """
    Request handler for getting the current DID endpoint from the wallet.

    Args:
        request: aiohttp request object

    Returns:
        The updated DID info

    """
    context: AdminRequestContext = request["context"]
    async with context.session() as session:
        wallet = session.inject_or(BaseWallet)
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


@docs(tags=["wallet"], summary="Rotate keypair for a DID not posted to the ledger")
@querystring_schema(DIDQueryStringSchema())
@response_schema(WalletModuleResponseSchema(), description="")
async def wallet_rotate_did_keypair(request: web.BaseRequest):
    """
    Request handler for rotating local DID keypair.

    Args:
        request: aiohttp request object

    Returns:
        An empty JSON response

    """
    context: AdminRequestContext = request["context"]
    did = request.query.get("did")
    if not did:
        raise web.HTTPBadRequest(reason="Request query must include DID")

    async with context.session() as session:
        wallet = session.inject_or(BaseWallet)
        if not wallet:
            raise web.HTTPForbidden(reason="No wallet available")
        try:
            did_info: DIDInfo = None
            did_info = await wallet.get_local_did(did)
            if did_info.metadata.get("posted", False):
                # call from ledger API instead to propagate through ledger NYM transaction
                raise web.HTTPBadRequest(reason=f"DID {did} is posted to the ledger")
            await wallet.rotate_did_keypair_start(did)  # do not take seed over the wire
            await wallet.rotate_did_keypair_apply(did)
        except WalletNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err
        except WalletError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})


def register_events(event_bus: EventBus):
    """Subscribe to any events we need to support."""
    event_bus.subscribe(EVENT_LISTENER_PATTERN, on_register_nym_event)


async def on_register_nym_event(profile: Profile, event: Event):
    """Handle any events we need to support."""

    # after the nym record is written, promote to wallet public DID
    if is_author_role(profile) and profile.context.settings.get_value(
        "endorser.auto_promote_author_did"
    ):
        did = event.payload["did"]
        try:
            await promote_wallet_public_did(
                profile, profile.context, profile.session, did
            )
        except Exception:
            # log the error, but continue
            LOGGER.exception(
                "Error accepting endorser invitation/configuring endorser connection: %s",
            )


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
