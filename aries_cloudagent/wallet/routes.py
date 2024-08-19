"""Wallet admin routes."""

import asyncio
import json
import logging
from typing import List, Optional, Tuple, Union

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, request_schema, response_schema
from marshmallow import fields

from aries_cloudagent.connections.base_manager import BaseConnectionManager

from ..admin.decorators.auth import tenant_authentication
from ..admin.request_context import AdminRequestContext
from ..config.injection_context import InjectionContext
from ..connections.models.conn_record import ConnRecord
from ..core.event_bus import Event, EventBus
from ..core.profile import Profile
from ..ledger.base import BaseLedger
from ..ledger.endpoint_type import EndpointType
from ..ledger.error import LedgerConfigError, LedgerError
from ..messaging.jsonld.error import BadJWSHeaderError, InvalidVerificationMethod
from ..messaging.models.base import BaseModelError
from ..messaging.models.openapi import OpenAPISchema
from ..messaging.responder import BaseResponder
from ..messaging.valid import (
    IndyDID,
)
from ..protocols.coordinate_mediation.v1_0.route_manager import RouteManager
from ..protocols.endorse_transaction.v1_0.manager import (
    TransactionManager,
    TransactionManagerError,
)
from ..protocols.endorse_transaction.v1_0.util import (
    get_endorser_connection_id,
    is_author_role,
)
from ..resolver.base import ResolverError
from ..storage.base import BaseStorage
from ..storage.error import StorageError, StorageNotFoundError
from ..storage.record import StorageRecord
from ..storage.type import RECORD_TYPE_ACAPY_UPGRADING
from ..wallet.jwt import jwt_sign, jwt_verify
from ..wallet.sd_jwt import sd_jwt_sign, sd_jwt_verify
from ..vc.vc_di.cryptosuites import CRYPTOSUITES 
from ..vc.vc_di import DataIntegrityProofException
from .anoncreds_upgrade import (
    UPGRADING_RECORD_IN_PROGRESS,
    upgrade_wallet_to_anoncreds_if_requested,
)
from .base import BaseWallet
from .did_info import DIDInfo
from .did_method import PEER2, PEER4, DIDMethod, DIDMethods, HolderDefinedDid
from .did_posture import DIDPosture
from .error import WalletError, WalletNotFoundError
from .key_type import ED25519, KeyTypes
from .singletons import UpgradeInProgressSingleton
from .util import EVENT_LISTENER_PATTERN
from .models.web_requests import (
    WalletModuleResponseSchema,
    DIDResultSchema,
    DIDListSchema,
    DIDEndpointWithTypeSchema,
    JWSCreateSchema,
    SDJWSCreateSchema,
    JWSVerifySchema,
    SDJWSVerifySchema,
    JWSVerifyResponseSchema,
    SDJWSVerifyResponseSchema,
    DIDEndpointSchema,
    DIDListQueryStringSchema,
    DIDQueryStringSchema,
    DIDCreateSchema,
    CreateAttribTxnForEndorserOptionSchema,
    AttribConnIdMatchInfoSchema,
    MediationIDSchema,
    DISignRequestSchema,
    DIVerifyRequestSchema
)

LOGGER = logging.getLogger(__name__)

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

@docs(tags=["wallet"], summary="List wallet DIDs")
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


@docs(tags=["wallet"], summary="Create a local DID")
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


@docs(tags=["wallet"], summary="Fetch the current public DID")
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


@docs(tags=["wallet"], summary="Assign the current public DID")
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

    async with context.session() as session:
        wallet = session.inject_or(BaseWallet)
        if not wallet:
            raise web.HTTPForbidden(reason="No wallet available")
    did = request.query.get("did")
    if not did:
        raise web.HTTPBadRequest(reason="Request query must include DID")

    info: DIDInfo = None

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
    except (LedgerError, WalletError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    if not create_transaction_for_endorser:
        return web.json_response({"result": format_did_info(info)})
    else:
        # DID is already posted to ledger
        if not attrib_def:
            return web.json_response({"result": format_did_info(info)})

        transaction_mgr = TransactionManager(context.profile)
        try:
            transaction = await transaction_mgr.create_record(
                messages_attach=attrib_def["signed_txn"], connection_id=connection_id
            )
        except StorageError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

        # if auto-request, send the request to the endorser
        if context.settings.get_value("endorser.auto_request"):
            try:
                transaction, transaction_request = await transaction_mgr.create_request(
                    transaction=transaction,
                    # TODO see if we need to parametrize these params
                    # expires_time=expires_time,
                )
            except (StorageError, TransactionManagerError) as err:
                raise web.HTTPBadRequest(reason=err.roll_up) from err

            await outbound_handler(transaction_request, connection_id=connection_id)

        return web.json_response({"txn": transaction.serialize()})


async def promote_wallet_public_did(
    context: Union[AdminRequestContext, InjectionContext],
    did: str,
    write_ledger: bool = False,
    profile: Profile = None,
    connection_id: str = None,
    routing_keys: List[str] = None,
    mediator_endpoint: str = None,
) -> Tuple[DIDInfo, Optional[dict]]:
    """Promote supplied DID to the wallet public DID."""
    info: DIDInfo = None
    endorser_did = None

    is_indy_did = bool(IndyDID.PATTERN.match(did))
    # write only Indy DID
    write_ledger = is_indy_did and write_ledger
    is_ctx_admin_request = True
    if isinstance(context, InjectionContext):
        is_ctx_admin_request = False
        if not profile:
            raise web.HTTPForbidden(
                reason=(
                    "InjectionContext is provided but no profile is provided. "
                    "InjectionContext does not have profile attribute but "
                    "AdminRequestContext does."
                )
            )
    ledger = (
        context.profile.inject_or(BaseLedger)
        if is_ctx_admin_request
        else profile.inject_or(BaseLedger)
    )

    if is_indy_did:
        if not ledger:
            reason = "No ledger available"
            if not context.settings.get_value("wallet.type"):
                reason += ": missing wallet-type?"
            raise PermissionError(reason)

        async with ledger:
            if not await ledger.get_key_for_did(did):
                raise LookupError(f"DID {did} is not posted to the ledger")

        is_author_profile = (
            is_author_role(context.profile)
            if is_ctx_admin_request
            else is_author_role(profile)
        )
        # check if we need to endorse
        if is_author_profile:
            # authors cannot write to the ledger
            write_ledger = False

            # author has not provided a connection id, so determine which to use
            if not connection_id:
                connection_id = (
                    await get_endorser_connection_id(context.profile)
                    if is_ctx_admin_request
                    else await get_endorser_connection_id(profile)
                )
            if not connection_id:
                raise web.HTTPBadRequest(reason="No endorser connection found")
        if not write_ledger:
            async with (
                context.session() if is_ctx_admin_request else profile.session()
            ) as session:
                try:
                    connection_record = await ConnRecord.retrieve_by_id(
                        session, connection_id
                    )
                except StorageNotFoundError as err:
                    raise web.HTTPNotFound(reason=err.roll_up) from err
                except BaseModelError as err:
                    raise web.HTTPBadRequest(reason=err.roll_up) from err
                endorser_info = await connection_record.metadata_get(
                    session, "endorser_info"
                )

            if not endorser_info:
                raise web.HTTPForbidden(
                    reason=(
                        "Endorser Info is not set up in "
                        "connection metadata for this connection record"
                    )
                )
            if "endorser_did" not in endorser_info.keys():
                raise web.HTTPForbidden(
                    reason=(
                        ' "endorser_did" is not set in "endorser_info"'
                        " in connection metadata for this connection record"
                    )
                )
            endorser_did = endorser_info["endorser_did"]

    did_info: DIDInfo = None
    attrib_def = None
    async with (
        context.session() if is_ctx_admin_request else profile.session()
    ) as session:
        wallet = session.inject_or(BaseWallet)
        did_info = await wallet.get_local_did(did)
        info = await wallet.set_public_did(did_info)

        if info:
            # Publish endpoint if necessary
            endpoint = did_info.metadata.get("endpoint")

            if is_indy_did and not endpoint:
                endpoint = mediator_endpoint or context.settings.get("default_endpoint")
                attrib_def = await wallet.set_did_endpoint(
                    info.did,
                    endpoint,
                    ledger,
                    write_ledger=write_ledger,
                    endorser_did=endorser_did,
                    routing_keys=routing_keys,
                )

    if info:
        # Route the public DID
        route_manager = (
            context.profile.inject(RouteManager)
            if is_ctx_admin_request
            else profile.inject(RouteManager)
        )
        (
            await route_manager.route_verkey(context.profile, info.verkey)
            if is_ctx_admin_request
            else await route_manager.route_verkey(profile, info.verkey)
        )

    return info, attrib_def


@docs(tags=["wallet"], summary="Update endpoint in wallet and on ledger if posted to it")
@request_schema(DIDEndpointWithTypeSchema)
@querystring_schema(CreateAttribTxnForEndorserOptionSchema())
@querystring_schema(AttribConnIdMatchInfoSchema())
@response_schema(WalletModuleResponseSchema(), description="")
@tenant_authentication
async def wallet_set_did_endpoint(request: web.BaseRequest):
    """Request handler for setting an endpoint for a DID.

    Args:
        request: aiohttp request object
    """
    context: AdminRequestContext = request["context"]

    outbound_handler = request["outbound_message_router"]

    body = await request.json()
    did = body["did"]
    endpoint = body.get("endpoint")
    endpoint_type = EndpointType.get(body.get("endpoint_type", EndpointType.ENDPOINT.w3c))

    create_transaction_for_endorser = json.loads(
        request.query.get("create_transaction_for_endorser", "false")
    )
    write_ledger = not create_transaction_for_endorser
    endorser_did = None
    connection_id = request.query.get("conn_id")
    attrib_def = None

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
            async with context.session() as session:
                connection_record = await ConnRecord.retrieve_by_id(
                    session, connection_id
                )
        except StorageNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err
        except BaseModelError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

        async with context.session() as session:
            endorser_info = await connection_record.metadata_get(session, "endorser_info")
        if not endorser_info:
            raise web.HTTPForbidden(
                reason=(
                    "Endorser Info is not set up in "
                    "connection metadata for this connection record"
                )
            )
        if "endorser_did" not in endorser_info.keys():
            raise web.HTTPForbidden(
                reason=(
                    ' "endorser_did" is not set in "endorser_info"'
                    " in connection metadata for this connection record"
                )
            )
        endorser_did = endorser_info["endorser_did"]

    async with context.session() as session:
        wallet = session.inject_or(BaseWallet)
        if not wallet:
            raise web.HTTPForbidden(reason="No wallet available")
        try:
            ledger = context.profile.inject_or(BaseLedger)
            attrib_def = await wallet.set_did_endpoint(
                did,
                endpoint,
                ledger,
                endpoint_type,
                write_ledger=write_ledger,
                endorser_did=endorser_did,
            )
        except WalletNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err
        except LedgerConfigError as err:
            raise web.HTTPForbidden(reason=err.roll_up) from err
        except (LedgerError, WalletError) as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    if not create_transaction_for_endorser:
        return web.json_response({})
    else:
        transaction_mgr = TransactionManager(context.profile)
        try:
            transaction = await transaction_mgr.create_record(
                messages_attach=attrib_def["signed_txn"], connection_id=connection_id
            )
        except StorageError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

        # if auto-request, send the request to the endorser
        if context.settings.get_value("endorser.auto_request"):
            try:
                transaction, transaction_request = await transaction_mgr.create_request(
                    transaction=transaction,
                    # TODO see if we need to parametrize these params
                    # expires_time=expires_time,
                )
            except (StorageError, TransactionManagerError) as err:
                raise web.HTTPBadRequest(reason=err.roll_up) from err

            await outbound_handler(transaction_request, connection_id=connection_id)

        return web.json_response({"txn": transaction.serialize()})


@docs(tags=["wallet"], summary="Create a EdDSA jws using did keys with a given payload")
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
    tags=["wallet"], summary="Create a EdDSA sd-jws using did keys with a given payload"
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


@docs(tags=["wallet"], summary="Verify a EdDSA jws using did keys with a given JWS")
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
    tags=["wallet"],
    summary="Verify a EdDSA sd-jws using did keys with a given SD-JWS with "
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


@docs(tags=["wallet"], summary="Add a DataIntegrityProof to a document.")
@request_schema(DISignRequestSchema())
@response_schema(WalletModuleResponseSchema(), description="")
@tenant_authentication
async def wallet_di_sign(request: web.BaseRequest):
    """Request handler for creating di proofs.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    document = body.get("document")
    options = body.get("options")
    try:
        suite = CRYPTOSUITES[options['cryptosuite']](profile=context.profile)
        secured_document = await suite.add_proof(document, options)
        return web.json_response({"securedDocument": secured_document})
    except ValueError as err:
        raise web.HTTPBadRequest(reason="Bad did or verification method") from err
    except (WalletNotFoundError, WalletError, DataIntegrityProofException) as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err


@docs(tags=["wallet"], summary="Verify a DataIntegrityProof secured document.")
@request_schema(DIVerifyRequestSchema())
@response_schema(WalletModuleResponseSchema(), description="")
@tenant_authentication
async def wallet_di_verify(request: web.BaseRequest):
    """Request handler for verifying di proofs.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    secured_document = body.get("securedDocument")

    try:
        unsecured_document = secured_document.copy()
        proofs = unsecured_document.pop('proof')
        verification_response = {
            "verifiedDocument": unsecured_document,
            "proofs": [],
        }
        for proof in proofs:
            suite = CRYPTOSUITES[proof['cryptosuite']](profile=context.profile)
            verified = await suite.verify_proof(unsecured_document, proof)
            verification_response['proofs'].append(proof | {"verified": verified})
        return web.json_response({"verificationResults": verification_response})
    except ValueError as err:
        raise web.HTTPBadRequest(reason="Bad did or verification method") from err
    except (WalletNotFoundError, WalletError, DataIntegrityProofException) as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err


@docs(tags=["wallet"], summary="Query DID endpoint in wallet")
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


@docs(tags=["wallet"], summary="Rotate keypair for a DID not posted to the ledger")
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


@docs(
    tags=["anoncreds - wallet upgrade"],
    summary="""
        Upgrade the wallet from askar to anoncreds - Be very careful with this! You 
        cannot go back! See migration guide for more information.
    """,
)
@querystring_schema(UpgradeVerificationSchema())
@response_schema(UpgradeResultSchema(), description="")
@tenant_authentication
async def upgrade_anoncreds(request: web.BaseRequest):
    """Request handler for triggering an upgrade to anoncreds.

    Args:
        request: aiohttp request object

    Returns:
        An empty JSON response

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile

    if profile.settings.get("wallet.name") != request.query.get("wallet_name"):
        raise web.HTTPBadRequest(
            reason="Wallet name parameter does not match the agent which triggered the upgrade"  # noqa: E501
        )

    if profile.settings.get("wallet.type") == "askar-anoncreds":
        raise web.HTTPBadRequest(reason="Wallet type is already anoncreds")

    async with profile.session() as session:
        storage = session.inject(BaseStorage)
        upgrading_record = StorageRecord(
            RECORD_TYPE_ACAPY_UPGRADING,
            UPGRADING_RECORD_IN_PROGRESS,
        )
        await storage.add_record(upgrading_record)
        is_subwallet = context.metadata and "wallet_id" in context.metadata
        asyncio.create_task(
            upgrade_wallet_to_anoncreds_if_requested(profile, is_subwallet)
        )
        UpgradeInProgressSingleton().set_wallet(profile.name)

    return web.json_response(
        {
            "success": True,
            "message": f"Upgrade to anoncreds has been triggered for wallet {profile.name}",  # noqa: E501
        }
    )


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
        connection_id = event.payload.get("connection_id")
        try:
            _info, attrib_def = await promote_wallet_public_did(
                context=profile.context,
                did=did,
                connection_id=connection_id,
                profile=profile,
            )
        except Exception as err:
            # log the error, but continue
            LOGGER.exception(
                "Error promoting to public DID: %s",
                err,
            )
            return

        transaction_mgr = TransactionManager(profile)
        try:
            transaction = await transaction_mgr.create_record(
                messages_attach=attrib_def["signed_txn"], connection_id=connection_id
            )
        except StorageError as err:
            # log the error, but continue
            LOGGER.exception(
                "Error accepting endorser invitation/configuring endorser"
                " connection: %s",
                err,
            )
            return

        # if auto-request, send the request to the endorser
        if profile.settings.get_value("endorser.auto_request"):
            try:
                transaction, transaction_request = await transaction_mgr.create_request(
                    transaction=transaction,
                    # TODO see if we need to parametrize these params
                    # expires_time=expires_time,
                )
            except (StorageError, TransactionManagerError) as err:
                # log the error, but continue
                LOGGER.exception(
                    "Error creating endorser transaction request: %s",
                    err,
                )

            # TODO not sure how to get outbound_handler in an event ...
            # await outbound_handler(transaction_request, connection_id=connection_id)
            responder = profile.inject_or(BaseResponder)
            if responder:
                await responder.send(
                    transaction_request,
                    connection_id=connection_id,
                )
            else:
                LOGGER.warning(
                    "Configuration has no BaseResponder: cannot update "
                    "ATTRIB record on DID: %s",
                    did,
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
            web.post("/wallet/jwt/sign", wallet_jwt_sign),
            web.post("/wallet/jwt/verify", wallet_jwt_verify),
            web.post("/wallet/sd-jwt/sign", wallet_sd_jwt_sign),
            web.post("/wallet/sd-jwt/verify", wallet_sd_jwt_verify),
            web.post("/wallet/di/add-proof", wallet_di_sign),
            web.post("/wallet/di/verify", wallet_di_verify),
            web.get(
                "/wallet/get-did-endpoint", wallet_get_did_endpoint, allow_head=False
            ),
            web.patch("/wallet/did/local/rotate-keypair", wallet_rotate_did_keypair),
            web.post("/anoncreds/wallet/upgrade", upgrade_anoncreds),
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
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "anoncreds - wallet upgrade",
            "description": "Anoncreds wallet upgrade",
            "externalDocs": {
                "description": "Specification",
                "url": "https://hyperledger.github.io/anoncreds-spec",
            },
        }
    )
