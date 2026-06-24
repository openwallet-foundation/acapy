"""Wallet admin routes."""

import json
import logging
from typing import List, Optional, Tuple, Union

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, request_schema, response_schema
from marshmallow import fields, validate

from ..admin.decorators.auth import tenant_authentication
from ..admin.request_context import AdminRequestContext
from ..config.injection_context import InjectionContext
from ..connections.base_manager import BaseConnectionManager
from ..connections.models.conn_record import ConnRecord
from ..core.profile import Profile
from ..messaging.jsonld.error import BadJWSHeaderError, InvalidVerificationMethod
from ..messaging.models.openapi import OpenAPISchema
from ..messaging.valid import (
    DID_POSTURE_EXAMPLE,
    DID_POSTURE_VALIDATE,
    ENDPOINT_EXAMPLE,
    ENDPOINT_TYPE_EXAMPLE,
    ENDPOINT_TYPE_VALIDATE,
    ENDPOINT_VALIDATE,
    GENERIC_DID_EXAMPLE,
    GENERIC_DID_VALIDATE,
    JWT_EXAMPLE,
    JWT_VALIDATE,
    NON_SD_LIST_EXAMPLE,
    NON_SD_LIST_VALIDATE,
    RAW_ED25519_2018_PUBLIC_KEY_EXAMPLE,
    RAW_ED25519_2018_PUBLIC_KEY_VALIDATE,
    SD_JWT_EXAMPLE,
    SD_JWT_VALIDATE,
    UNQUALIFIED_OR_INDY_DID_EXAMPLE,
    UNQUALIFIED_OR_INDY_DID_VALIDATE,
    UUID4_EXAMPLE,
    UUID4_VALIDATE,
    StrOrDictField,
    UnqualifiedOrIndyDID,
    Uri,
)
from ..protocols.coordinate_mediation.v1_0.route_manager import RouteManager
from ..resolver.base import ResolverError
from ..wallet.jwt import jwt_sign, jwt_verify
from ..wallet.sd_jwt import sd_jwt_sign, sd_jwt_verify
from .base import BaseWallet
from .did_info import DIDInfo
from .did_method import (
    INDY,
    KEY,
    PEER2,
    PEER4,
    SOV,
    DIDMethod,
    DIDMethods,
    HolderDefinedDid,
)
from .did_posture import DIDPosture
from .error import WalletError, WalletNotFoundError
from .key_type import BLS12381G2, ED25519, P256, KeyTypes

LOGGER = logging.getLogger(__name__)

WALLET_TAG_TITLE = "wallet"
UPGRADE_TAG_TITLE = "AnonCreds - Wallet Upgrade"


class WalletModuleResponseSchema(OpenAPISchema):
    """Response schema for Wallet Module."""


class DIDSchema(OpenAPISchema):
    """Result schema for a DID."""

    did = fields.Str(
        required=True,
        validate=GENERIC_DID_VALIDATE,
        metadata={"description": "DID of interest", "example": GENERIC_DID_EXAMPLE},
    )
    verkey = fields.Str(
        required=True,
        validate=RAW_ED25519_2018_PUBLIC_KEY_VALIDATE,
        metadata={
            "description": "Public verification key",
            "example": RAW_ED25519_2018_PUBLIC_KEY_EXAMPLE,
        },
    )
    posture = fields.Str(
        required=True,
        validate=DID_POSTURE_VALIDATE,
        metadata={
            "description": (
                "Whether DID is current public DID, posted to ledger but not current"
                " public DID, or local to the wallet"
            ),
            "example": DID_POSTURE_EXAMPLE,
        },
    )
    method = fields.Str(
        required=True,
        metadata={
            "description": "Did method associated with the DID",
            "example": SOV.method_name,
        },
    )
    key_type = fields.Str(
        required=True,
        validate=validate.OneOf([ED25519.key_type, BLS12381G2.key_type, P256.key_type]),
        metadata={
            "description": "Key type associated with the DID",
            "example": ED25519.key_type,
        },
    )
    metadata = fields.Dict(
        required=False,
        metadata={"description": "Additional metadata associated with the DID"},
    )


class DIDResultSchema(OpenAPISchema):
    """Result schema for a DID."""

    result = fields.Nested(DIDSchema())


class DIDListSchema(OpenAPISchema):
    """Result schema for connection list."""

    results = fields.List(
        fields.Nested(DIDSchema()), metadata={"description": "DID list"}
    )


class DIDEndpointWithTypeSchema(OpenAPISchema):
    """Request schema to set DID endpoint of particular type."""

    did = fields.Str(
        required=True,
        validate=UNQUALIFIED_OR_INDY_DID_VALIDATE,
        metadata={
            "description": "DID of interest",
            "example": UNQUALIFIED_OR_INDY_DID_EXAMPLE,
        },
    )
    endpoint = fields.Str(
        required=False,
        validate=ENDPOINT_VALIDATE,
        metadata={
            "description": "Endpoint to set (omit to delete)",
            "example": ENDPOINT_EXAMPLE,
        },
    )
    endpoint_type = fields.Str(
        required=False,
        validate=ENDPOINT_TYPE_VALIDATE,
        metadata={
            "description": (
                "Endpoint type to set (default 'w3c'); affects only public or posted DIDs"
            ),
            "example": ENDPOINT_TYPE_EXAMPLE,
        },
    )
    mediation_id = fields.Str(
        required=False,
        validate=UUID4_VALIDATE,
        metadata={
            "description": "Mediation ID to use for endpoint information.",
            "example": UUID4_EXAMPLE,
        },
    )


class JWSCreateSchema(OpenAPISchema):
    """Request schema to create a jws with a particular DID."""

    headers = fields.Dict()
    payload = fields.Dict(required=True)
    did = fields.Str(
        required=False,
        validate=GENERIC_DID_VALIDATE,
        metadata={"description": "DID of interest", "example": GENERIC_DID_EXAMPLE},
    )
    verification_method = fields.Str(
        data_key="verificationMethod",
        required=False,
        validate=Uri(),
        metadata={
            "description": "Information used for proof verification",
            "example": (
                "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg34"
                "2Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
            ),
        },
    )


class SDJWSCreateSchema(JWSCreateSchema):
    """Request schema to create an sd-jws with a particular DID."""

    non_sd_list = fields.List(
        fields.Str(
            required=False,
            validate=NON_SD_LIST_VALIDATE,
            metadata={"example": NON_SD_LIST_EXAMPLE},
        )
    )


class JWSVerifySchema(OpenAPISchema):
    """Request schema to verify a jws created from a DID."""

    jwt = fields.Str(validate=JWT_VALIDATE, metadata={"example": JWT_EXAMPLE})


class SDJWSVerifySchema(OpenAPISchema):
    """Request schema to verify an sd-jws created from a DID."""

    sd_jwt = fields.Str(validate=SD_JWT_VALIDATE, metadata={"example": SD_JWT_EXAMPLE})


class JWSVerifyResponseSchema(OpenAPISchema):
    """Response schema for JWT verification result."""

    valid = fields.Bool(required=True)
    error = fields.Str(required=False, metadata={"description": "Error text"})
    kid = fields.Str(required=True, metadata={"description": "kid of signer"})
    headers = fields.Dict(
        required=True, metadata={"description": "Headers from verified JWT."}
    )
    payload = fields.Dict(
        required=True, metadata={"description": "Payload from verified JWT"}
    )


class SDJWSVerifyResponseSchema(JWSVerifyResponseSchema):
    """Response schema for SD-JWT verification result."""

    disclosures = fields.List(
        fields.List(StrOrDictField()),
        metadata={
            "description": "Disclosure arrays associated with the SD-JWT",
            "example": [
                ["fx1iT_mETjGiC-JzRARnVg", "name", "Alice"],
                [
                    "n4-t3mlh8jSS6yMIT7QHnA",
                    "street_address",
                    {"_sd": ["kLZrLK7enwfqeOzJ9-Ss88YS3mhjOAEk9lr_ix2Heng"]},
                ],
            ],
        },
    )


class DIDEndpointSchema(OpenAPISchema):
    """Request schema to set DID endpoint; response schema to get DID endpoint."""

    did = fields.Str(
        required=True,
        validate=UNQUALIFIED_OR_INDY_DID_VALIDATE,
        metadata={
            "description": "DID of interest",
            "example": UNQUALIFIED_OR_INDY_DID_EXAMPLE,
        },
    )
    endpoint = fields.Str(
        required=False,
        validate=ENDPOINT_VALIDATE,
        metadata={
            "description": "Endpoint to set (omit to delete)",
            "example": ENDPOINT_EXAMPLE,
        },
    )


class DIDListQueryStringSchema(OpenAPISchema):
    """Parameters and validators for DID list request query string."""

    did = fields.Str(
        required=False,
        validate=GENERIC_DID_VALIDATE,
        metadata={"description": "DID of interest", "example": GENERIC_DID_EXAMPLE},
    )
    verkey = fields.Str(
        required=False,
        validate=RAW_ED25519_2018_PUBLIC_KEY_VALIDATE,
        metadata={
            "description": "Verification key of interest",
            "example": RAW_ED25519_2018_PUBLIC_KEY_EXAMPLE,
        },
    )
    posture = fields.Str(
        required=False,
        validate=DID_POSTURE_VALIDATE,
        metadata={
            "description": (
                "Whether DID is current public DID, posted to ledger but current public"
                " DID, or local to the wallet"
            ),
            "example": DID_POSTURE_EXAMPLE,
        },
    )
    method = fields.Str(
        required=False,
        metadata={
            "example": KEY.method_name,
            "description": (
                "DID method to query for. e.g. sov to only fetch indy/sov DIDs"
            ),
        },
    )
    key_type = fields.Str(
        required=False,
        validate=validate.OneOf([ED25519.key_type, BLS12381G2.key_type, P256.key_type]),
        metadata={"example": ED25519.key_type, "description": "Key type to query for."},
    )


class DIDQueryStringSchema(OpenAPISchema):
    """Parameters and validators for set public DID request query string."""

    did = fields.Str(
        required=True,
        validate=GENERIC_DID_VALIDATE,
        metadata={"description": "DID of interest", "example": GENERIC_DID_EXAMPLE},
    )


class DIDCreateOptionsSchema(OpenAPISchema):
    """Parameters and validators for create DID options."""

    key_type = fields.Str(
        required=True,
        validate=validate.OneOf([ED25519.key_type, BLS12381G2.key_type, P256.key_type]),
        metadata={
            "example": ED25519.key_type,
            "description": (
                "Key type to use for the DID keypair. "
                + "Validated with the chosen DID method's supported key types."
            ),
        },
    )

    did = fields.Str(
        required=False,
        validate=GENERIC_DID_VALIDATE,
        metadata={
            "description": (
                "Specify final value of the did (including did:<method>: prefix)"
                + "if the method supports or requires so."
            ),
            "example": GENERIC_DID_EXAMPLE,
        },
    )


class DIDCreateSchema(OpenAPISchema):
    """Parameters and validators for create DID endpoint."""

    method = fields.Str(
        required=False,
        dump_default=SOV.method_name,
        metadata={
            "example": SOV.method_name,
            "description": (
                "Method for the requested DID."
                + "Supported methods are 'key', 'sov', and any other registered method."
            ),
        },
    )

    options = fields.Nested(
        DIDCreateOptionsSchema,
        required=False,
        metadata={
            "description": (
                "To define a key type and/or a did depending on chosen DID method."
            )
        },
    )

    seed = fields.Str(
        required=False,
        metadata={
            "description": (
                "Optional seed to use for DID, Must be enabled in configuration before"
                " use."
            ),
            "example": "000000000000000000000000Trustee1",
        },
    )


class CreateAttribTxnForEndorserOptionSchema(OpenAPISchema):
    """Class for user to input whether to create a transaction for endorser or not."""

    create_transaction_for_endorser = fields.Boolean(
        required=False,
        metadata={"description": "Create Transaction For Endorser's signature"},
    )


class AttribConnIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    conn_id = fields.Str(
        required=False, metadata={"description": "Connection identifier"}
    )


class MediationIDSchema(OpenAPISchema):
    """Class for user to optionally input a mediation_id."""

    mediation_id = fields.Str(
        required=False, metadata={"description": "Mediation identifier"}
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
            "metadata": info.metadata,
        }


@docs(tags=[WALLET_TAG_TITLE], summary="List wallet DIDs")
@querystring_schema(DIDListQueryStringSchema())
@response_schema(DIDListSchema, 200, description="")
@tenant_authentication
async def wallet_did_list(request: web.BaseRequest):
    """Request handler for searching wallet DIDs.

    Args:
        request: aiohttp request object

    Returns:
        The DID list response

    """
    context: AdminRequestContext = request["context"]
    filter_did = request.query.get("did")
    filter_verkey = request.query.get("verkey")
    filter_posture = DIDPosture.get(request.query.get("posture"))
    results = []
    async with context.session() as session:
        did_methods: DIDMethods = session.inject(DIDMethods)
        filter_method: DIDMethod | None = did_methods.from_method(
            request.query.get("method")
        )
        key_types = session.inject(KeyTypes)
        filter_key_type = key_types.from_key_type(request.query.get("key_type", ""))
        wallet: BaseWallet | None = session.inject_or(BaseWallet)
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
                        filter_posture is DIDPosture.WALLET_ONLY
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

    results.sort(key=lambda info: (DIDPosture.get(info["posture"]).ordinal, info["did"]))

    return web.json_response({"results": results})


@docs(tags=[WALLET_TAG_TITLE], summary="Create a local DID")
@request_schema(DIDCreateSchema())
@response_schema(DIDResultSchema, 200, description="")
@tenant_authentication
async def wallet_create_did(request: web.BaseRequest):
    """Request handler for creating a new local DID in the wallet.

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

    seed = body.get("seed") or None
    if seed and not context.settings.get("wallet.allow_insecure_seed"):
        raise web.HTTPBadRequest(reason="Seed support is not enabled")
    info = None
    async with context.session() as session:
        did_methods = session.inject(DIDMethods)

        method = did_methods.from_method(body.get("method", "sov"))
        if not method:
            raise web.HTTPForbidden(
                reason=f"method {body.get('method')} is not supported by the agent."
            )

        # Don't support Indy DID method from this endpoint
        if method.method_name == INDY.method_name:
            raise web.HTTPBadRequest(
                reason="Indy did method is supported from /did/indy/create endpoint."
            )

        key_types = session.inject(KeyTypes)
        # set default method and key type for backwards compat
        key_type = (
            key_types.from_key_type(body.get("options", {}).get("key_type", ""))
            or ED25519
        )
        if not method.supports_key_type(key_type):
            raise web.HTTPForbidden(
                reason=(
                    f"method {method.method_name} does not"
                    f" support key type {key_type.key_type}"
                )
            )

        did = body.get("options", {}).get("did")
        if method.holder_defined_did() == HolderDefinedDid.NO and did:
            raise web.HTTPForbidden(
                reason=f"method {method.method_name} does not support user-defined DIDs"
            )
        elif method.holder_defined_did() == HolderDefinedDid.REQUIRED and not did:
            raise web.HTTPBadRequest(
                reason=f"method {method.method_name} requires a user-defined DIDs"
            )

        wallet = session.inject_or(BaseWallet)
        if not wallet:
            raise web.HTTPForbidden(reason="No wallet available")
        try:
            is_did_peer_2 = method.method_name == PEER2.method_name
            is_did_peer_4 = method.method_name == PEER4.method_name
            if is_did_peer_2 or is_did_peer_4:
                base_conn_mgr = BaseConnectionManager(context.profile)

                options = body.get("options", {})

                connection_id = options.get("conn_id")
                my_endpoint = options.get("endpoint")
                mediation_id = options.get("mediation_id")

                # FIXME:
                # This logic is duplicated in BaseConnectionManager
                # It should be refactored into one method.
                ###################################################

                my_endpoints = []
                if my_endpoint:
                    my_endpoints = [my_endpoint]
                else:
                    default_endpoint = context.profile.settings.get("default_endpoint")
                    if default_endpoint:
                        my_endpoints.append(default_endpoint)
                    my_endpoints.extend(
                        context.profile.settings.get("additional_endpoints", [])
                    )

                mediation_records = []
                if connection_id:
                    conn_rec = await ConnRecord.retrieve_by_id(session, connection_id)
                    mediation_records = await base_conn_mgr._route_manager.mediation_records_for_connection(  # noqa: E501
                        context.profile,
                        conn_rec,
                        mediation_id,
                        or_default=True,
                    )

                ###################################################

                info = (
                    await base_conn_mgr.create_did_peer_2(my_endpoints, mediation_records)
                    if is_did_peer_2
                    else await base_conn_mgr.create_did_peer_4(
                        my_endpoints, mediation_records
                    )
                )
            else:
                info = await wallet.create_local_did(
                    method=method, key_type=key_type, seed=seed, did=did
                )

        except WalletError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"result": format_did_info(info)})


@docs(tags=[WALLET_TAG_TITLE], summary="Fetch the current public DID")
@response_schema(DIDResultSchema, 200, description="")
@tenant_authentication
async def wallet_get_public_did(request: web.BaseRequest):
    """Request handler for fetching the current public DID.

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


@docs(tags=[WALLET_TAG_TITLE], summary="Assign the current public DID")
@querystring_schema(DIDQueryStringSchema())
@querystring_schema(CreateAttribTxnForEndorserOptionSchema())
@querystring_schema(AttribConnIdMatchInfoSchema())
@querystring_schema(MediationIDSchema())
@response_schema(DIDResultSchema, 200, description="")
@tenant_authentication
async def wallet_set_public_did(request: web.BaseRequest):
    """Request handler for setting the current public DID.

    Args:
        request: aiohttp request object

    Returns:
        The updated DID info

    """
    context: AdminRequestContext = request["context"]

    outbound_handler = request["outbound_message_router"]

    create_transaction_for_endorser = json.loads(
        request.query.get("create_transaction_for_endorser", "false")
    )
    write_ledger = not create_transaction_for_endorser
    connection_id = request.query.get("conn_id")
    attrib_def = None

    async with context.session() as session:
        wallet = session.inject_or(BaseWallet)
        if not wallet:
            raise web.HTTPForbidden(reason="No wallet available")
    did = request.query.get("did")
    if not did:
        raise web.HTTPBadRequest(reason="Request query must include DID")

    info: Optional[DIDInfo] = None

    mediation_id = request.query.get("mediation_id")
    profile = context.profile
    route_manager = profile.inject(RouteManager)
    mediation_record = await route_manager.mediation_record_if_id(
        profile=profile, mediation_id=mediation_id, or_default=True
    )

    routing_keys, mediator_endpoint = await route_manager.routing_info(
        profile,
        mediation_record,
    )

    try:
        info, attrib_def = await promote_wallet_public_did(
            context,
            did,
            write_ledger=write_ledger,
            connection_id=connection_id,
            routing_keys=routing_keys,
            mediator_endpoint=mediator_endpoint,
        )
    except LookupError as err:
        raise web.HTTPNotFound(reason=str(err)) from err
    except PermissionError as err:
        raise web.HTTPForbidden(reason=str(err)) from err
    except WalletNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    return web.json_response({"result": format_did_info(info)})


async def promote_wallet_public_did(
    context: Union[AdminRequestContext, InjectionContext],
    did: str,
    write_ledger: bool = False,
    profile: Optional[Profile] = None,
    connection_id: Optional[str] = None,
    routing_keys: Optional[List[str]] = None,
    mediator_endpoint: Optional[str] = None,
) -> Tuple[DIDInfo, Optional[dict]]:
    """Promote supplied DID to the wallet public DID."""
    LOGGER.debug("Starting promotion of DID %s to wallet public DID", did)
    info: Optional[DIDInfo] = None
    endorser_did = None

    is_indy_did = bool(UnqualifiedOrIndyDID.PATTERN.match(did))
    # write only Indy DID
    write_ledger = is_indy_did and write_ledger
    is_ctx_admin_request = True
    if isinstance(context, InjectionContext):
        is_ctx_admin_request = False
        if not profile:
            LOGGER.error("InjectionContext provided without profile")
            raise web.HTTPForbidden(
                reason=(
                    "InjectionContext is provided but no profile is provided. "
                    "InjectionContext does not have profile attribute but "
                    "AdminRequestContext does."
                )
            )

    did_info: Optional[DIDInfo] = None
    attrib_def = None
    async with (
        context.session() if is_ctx_admin_request else profile.session()
    ) as session:
        wallet = session.inject(BaseWallet)
        did_info = await wallet.get_local_did(did)
        info = await wallet.set_public_did(did_info)
        LOGGER.info("DID %s set as public DID", info.did)

    if info:
        LOGGER.debug("Routing public DID %s", info.did)
        if is_ctx_admin_request:
            profile = context.profile
        route_manager = profile.inject(RouteManager)
        await route_manager.route_verkey(profile, info.verkey)
        LOGGER.info(
            "Routing set up for public DID %s with verkey %s", info.did, info.verkey
        )

    LOGGER.debug("Completed promotion of DID %s", did)
    return info, attrib_def


@docs(tags=[WALLET_TAG_TITLE], summary="Create a jws using did keys with a given payload")
@request_schema(JWSCreateSchema)
@response_schema(WalletModuleResponseSchema(), description="")
@tenant_authentication
async def wallet_jwt_sign(request: web.BaseRequest):
    """Request handler for jws creation using did.

    Args:
        request (web.BaseRequest): The HTTP request object.

    Returns:
        web.Response: The HTTP response containing the signed JWS.

    Raises:
        web.HTTPBadRequest: If the provided DID or verification method is invalid.
        web.HTTPNotFound: If the wallet is not found.
        web.HTTPBadRequest: If there is an error with the wallet.

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    did = body.get("did")
    verification_method = body.get("verificationMethod")
    headers = body.get("headers", {})
    payload = body.get("payload", {})

    try:
        jws = await jwt_sign(context.profile, headers, payload, did, verification_method)
    except ValueError as err:
        raise web.HTTPBadRequest(reason="Bad did or verification method") from err
    except WalletNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except WalletError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(jws)


@docs(
    tags=[WALLET_TAG_TITLE],
    summary="Create an sd-jws using did keys with a given payload",
)
@request_schema(SDJWSCreateSchema)
@response_schema(WalletModuleResponseSchema(), description="")
@tenant_authentication
async def wallet_sd_jwt_sign(request: web.BaseRequest):
    """Request handler for sd-jws creation using did.

    Args:
        request (web.BaseRequest): The HTTP request object.

    Returns:
        web.Response: The HTTP response object.
            Contains the signed sd-jws.

    Raises:
        web.HTTPBadRequest: If the provided did or verification method is invalid.
        web.HTTPNotFound: If the wallet is not found.
        web.HTTPBadRequest: If there is an error with the wallet.

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    did = body.get("did")
    verification_method = body.get("verificationMethod")
    headers = body.get("headers", {})
    payload = body.get("payload", {})
    non_sd_list = body.get("non_sd_list", [])

    try:
        sd_jws = await sd_jwt_sign(
            context.profile, headers, payload, non_sd_list, did, verification_method
        )
    except ValueError as err:
        raise web.HTTPBadRequest(reason="Bad did or verification method") from err
    except WalletNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except WalletError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(sd_jws)


@docs(tags=[WALLET_TAG_TITLE], summary="Verify a jws using did keys with a given JWS")
@request_schema(JWSVerifySchema())
@response_schema(JWSVerifyResponseSchema(), 200, description="")
@tenant_authentication
async def wallet_jwt_verify(request: web.BaseRequest):
    """Request handler for jws validation using did.

    Args:
        request (web.BaseRequest): The HTTP request object.
            "jwt": { ... }

    Returns:
        web.Response: The HTTP response containing the validation result.

    Raises:
        web.HTTPBadRequest: If there is an error with the JWS header or verification
            method.
        web.HTTPNotFound: If there is an error resolving the JWS.

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    jwt = body["jwt"]
    try:
        result = await jwt_verify(context.profile, jwt)
    except (BadJWSHeaderError, InvalidVerificationMethod) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    except ResolverError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    return web.json_response(
        {
            "valid": result.valid,
            "headers": result.headers,
            "payload": result.payload,
            "kid": result.kid,
        }
    )


@docs(
    tags=[WALLET_TAG_TITLE],
    summary="Verify an sd-jws using did keys with a given SD-JWS with "
    "optional key binding",
)
@request_schema(SDJWSVerifySchema())
@response_schema(SDJWSVerifyResponseSchema(), 200, description="")
@tenant_authentication
async def wallet_sd_jwt_verify(request: web.BaseRequest):
    """Request handler for sd-jws validation using did.

    Args:
        request: The web request object.
            "sd-jwt": { ... }

    Returns:
        A JSON response containing the result of the sd-jwt verification.

    Raises:
        web.HTTPBadRequest: If there is an error with the JWS header or verification
            method.
        web.HTTPNotFound: If there is an error resolving the verification method.

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    sd_jwt = body["sd_jwt"]
    try:
        result = await sd_jwt_verify(context.profile, sd_jwt)
    except (BadJWSHeaderError, InvalidVerificationMethod) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    except ResolverError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    return web.json_response(result.serialize())


@docs(tags=[WALLET_TAG_TITLE], summary="Query DID endpoint in wallet")
@querystring_schema(DIDQueryStringSchema())
@response_schema(DIDEndpointSchema, 200, description="")
@tenant_authentication
async def wallet_get_did_endpoint(request: web.BaseRequest):
    """Request handler for getting the current DID endpoint from the wallet.

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


@docs(
    tags=[WALLET_TAG_TITLE], summary="Rotate keypair for a DID not posted to the ledger"
)
@querystring_schema(DIDQueryStringSchema())
@response_schema(WalletModuleResponseSchema(), description="")
@tenant_authentication
async def wallet_rotate_did_keypair(request: web.BaseRequest):
    """Request handler for rotating local DID keypair.

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
            did_info: Optional[DIDInfo] = None
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


class UpgradeVerificationSchema(OpenAPISchema):
    """Parameters and validators for triggering an upgrade to anoncreds."""

    wallet_name = fields.Str(
        required=True,
        metadata={
            "description": "Name of wallet to upgrade to anoncreds",
            "example": "base-wallet",
        },
    )


class UpgradeResultSchema(OpenAPISchema):
    """Result schema for upgrade."""


async def register(app: web.Application):
    """Register routes."""
    app.add_routes(
        [
            web.get("/wallet/did", wallet_did_list, allow_head=False),
            web.post("/wallet/did/create", wallet_create_did),
            web.get("/wallet/did/public", wallet_get_public_did, allow_head=False),
            web.post("/wallet/did/public", wallet_set_public_did),
            web.post("/wallet/jwt/sign", wallet_jwt_sign),
            web.post("/wallet/jwt/verify", wallet_jwt_verify),
            web.post("/wallet/sd-jwt/sign", wallet_sd_jwt_sign),
            web.post("/wallet/sd-jwt/verify", wallet_sd_jwt_verify),
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
            "name": WALLET_TAG_TITLE,
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
    app._state["swagger_dict"]["tags"].append(
        {
            "name": UPGRADE_TAG_TITLE,
            "description": "AnonCreds wallet upgrade",
            "externalDocs": {
                "description": "Specification",
                "url": "https://hyperledger.github.io/anoncreds-spec",
            },
        }
    )
