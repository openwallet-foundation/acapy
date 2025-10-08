"""Connection handling admin routes."""

import json

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)
from marshmallow import fields, validate

from ....admin.decorators.auth import tenant_authentication
from ....admin.request_context import AdminRequestContext
from ....connections.models.conn_record import ConnRecord, ConnRecordSchema
from ....messaging.models.base import BaseModelError
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import (
    ENDPOINT_EXAMPLE,
    ENDPOINT_VALIDATE,
    GENERIC_DID_EXAMPLE,
    GENERIC_DID_VALIDATE,
    UUID4_EXAMPLE,
    UUID4_VALIDATE,
)
from ....storage.error import StorageError, StorageNotFoundError
from ....wallet.base import BaseWallet
from ....wallet.error import WalletError
from .manager import DIDXManager, DIDXManagerError
from .message_types import DIDEX_1_0, DIDEX_1_1, SPEC_URI
from .messages.request import DIDXRequest, DIDXRequestSchema


class DIDXAcceptInvitationQueryStringSchema(OpenAPISchema):
    """Parameters and validators for accept invitation request query string."""

    my_endpoint = fields.Str(
        required=False,
        validate=ENDPOINT_VALIDATE,
        metadata={"description": "My URL endpoint", "example": ENDPOINT_EXAMPLE},
    )
    my_label = fields.Str(
        required=False,
        metadata={"description": "Label for connection request", "example": "Broker"},
    )
    use_did = fields.Str(
        required=False,
        metadata={
            "description": "The DID to use to for this connection",
            "example": "did:example:1234",
        },
    )
    use_did_method = fields.Str(
        required=False,
        validate=validate.OneOf(DIDXManager.SUPPORTED_USE_DID_METHODS),
        metadata={
            "description": "The DID method to use to generate a DID for this connection",
            "example": "did:peer:4",
        },
    )


class DIDXCreateRequestImplicitQueryStringSchema(OpenAPISchema):
    """Parameters and validators for create-request-implicit request query string."""

    their_public_did = fields.Str(
        required=True,
        allow_none=False,
        validate=GENERIC_DID_VALIDATE,
        metadata={
            "description": "Qualified public DID to which to request connection",
            "example": GENERIC_DID_EXAMPLE,
        },
    )
    alias = fields.Str(
        required=False,
        metadata={"description": "Alias for connection", "example": "Barry"},
    )
    auto_accept = fields.Boolean(
        required=False,
        metadata={"description": "Auto-accept connection (defaults to configuration)"},
    )
    my_endpoint = fields.Str(
        required=False,
        validate=ENDPOINT_VALIDATE,
        metadata={"description": "My URL endpoint", "example": ENDPOINT_EXAMPLE},
    )
    my_label = fields.Str(
        required=False,
        metadata={"description": "Label for connection request", "example": "Broker"},
    )
    mediation_id = fields.Str(
        required=False,
        validate=UUID4_VALIDATE,
        metadata={
            "description": "Identifier for active mediation record to be used",
            "example": UUID4_EXAMPLE,
        },
    )
    use_public_did = fields.Boolean(
        required=False, metadata={"description": "Use public DID for this connection"}
    )
    use_did = fields.Str(
        required=False,
        metadata={
            "description": "The DID to use to for this connection",
            "example": "did:example:1234",
        },
    )
    use_did_method = fields.Str(
        required=False,
        validate=validate.OneOf(DIDXManager.SUPPORTED_USE_DID_METHODS),
        metadata={
            "description": "The DID method to use to generate a DID for this connection",
            "example": "did:peer:4",
        },
    )
    goal_code = fields.Str(
        required=False,
        metadata={
            "description": (
                "A self-attested code the receiver may want to display to the user or"
                " use in automatically deciding what to do with the out-of-band message"
            ),
            "example": "issue-vc",
        },
    )
    goal = fields.Str(
        required=False,
        metadata={
            "description": (
                "A self-attested string that the receiver may want to display to the"
                " user about the context-specific goal of the out-of-band message"
            ),
            "example": "To issue a Faber College Graduate credential",
        },
    )
    protocol = fields.Str(
        required=False,
        validate=validate.OneOf([DIDEX_1_0, DIDEX_1_1]),
        metadata={
            "description": "Which DID Exchange Protocol version to use",
            "example": "didexchange/1.0",
        },
    )


class DIDXReceiveRequestImplicitQueryStringSchema(OpenAPISchema):
    """Parameters and validators for receive-request-implicit request query string."""

    alias = fields.Str(
        required=False,
        metadata={"description": "Alias for connection", "example": "Barry"},
    )
    my_endpoint = fields.Str(
        required=False,
        validate=ENDPOINT_VALIDATE,
        metadata={"description": "My URL endpoint", "example": ENDPOINT_EXAMPLE},
    )
    auto_accept = fields.Boolean(
        required=False,
        metadata={"description": "Auto-accept connection (defaults to configuration)"},
    )
    mediation_id = fields.Str(
        required=False,
        validate=UUID4_VALIDATE,
        metadata={
            "description": "Identifier for active mediation record to be used",
            "example": UUID4_EXAMPLE,
        },
    )


class DIDXAcceptRequestQueryStringSchema(OpenAPISchema):
    """Parameters and validators for accept-request request query string."""

    my_endpoint = fields.Str(
        required=False,
        validate=ENDPOINT_VALIDATE,
        metadata={"description": "My URL endpoint", "example": ENDPOINT_EXAMPLE},
    )
    mediation_id = fields.Str(
        required=False,
        validate=UUID4_VALIDATE,
        metadata={
            "description": "Identifier for active mediation record to be used",
            "example": UUID4_EXAMPLE,
        },
    )
    use_public_did = fields.Boolean(
        required=False, metadata={"description": "Use public DID for this connection"}
    )


class DIDXConnIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    conn_id = fields.Str(
        required=True,
        metadata={"description": "Connection identifier", "example": UUID4_EXAMPLE},
    )


class DIDXConnIdRefIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection and ref ids."""

    conn_id = fields.Str(
        required=True,
        metadata={"description": "Connection identifier", "example": UUID4_EXAMPLE},
    )

    ref_id = fields.Str(
        required=True,
        metadata={
            "description": "Inbound connection identifier",
            "example": UUID4_EXAMPLE,
        },
    )


class DIDXRejectRequestSchema(OpenAPISchema):
    """Parameters and validators for reject-request request string."""

    reason = fields.Str(
        metadata={
            "description": "Reason for rejecting the DID Exchange",
            "example": "Request rejected",
        },
        required=False,
    )


@docs(
    tags=["did-exchange"],
    summary="Accept a stored connection invitation",
)
@match_info_schema(DIDXConnIdMatchInfoSchema())
@querystring_schema(DIDXAcceptInvitationQueryStringSchema())
@response_schema(ConnRecordSchema(), 200, description="")
@tenant_authentication
async def didx_accept_invitation(request: web.BaseRequest):
    """Request handler for accepting a stored connection invitation.

    Args:
        request: aiohttp request object

    Returns:
        The resulting connection record details

    """
    context: AdminRequestContext = request["context"]

    outbound_handler = request["outbound_message_router"]
    connection_id = request.match_info["conn_id"]
    my_label = request.query.get("my_label") or None
    my_endpoint = request.query.get("my_endpoint") or None
    mediation_id = request.query.get("mediation_id") or None
    use_did = request.query.get("use_did") or None
    use_did_method = request.query.get("use_did_method") or None

    if use_did and use_did_method:
        raise web.HTTPBadRequest(
            reason="use_did and use_did_method are mutually exclusive"
        )

    profile = context.profile
    didx_mgr = DIDXManager(profile)
    try:
        async with profile.session() as session:
            conn_rec = await ConnRecord.retrieve_by_id(session, connection_id)
            if use_did:
                wallet = session.inject(BaseWallet)
                did_info = await wallet.get_local_did(use_did)
                conn_rec.my_did = did_info.did
                await conn_rec.save(
                    session, reason="Set my_did from use_did on invite accept"
                )

        didx_request = await didx_mgr.create_request(
            conn_rec=conn_rec,
            my_label=my_label,
            my_endpoint=my_endpoint,
            mediation_id=mediation_id,
            use_did_method=use_did_method,
        )
        result = conn_rec.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (StorageError, WalletError, DIDXManagerError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(didx_request, connection_id=conn_rec.connection_id)

    return web.json_response(result)


@docs(
    tags=["did-exchange"],
    summary="Create and send a request against public DID's implicit invitation",
)
@querystring_schema(DIDXCreateRequestImplicitQueryStringSchema())
@response_schema(ConnRecordSchema(), 200, description="")
@tenant_authentication
async def didx_create_request_implicit(request: web.BaseRequest):
    """Request handler for creating and sending a request to an implicit invitation.

    Args:
        request: aiohttp request object

    Returns:
        The resulting connection record details

    """
    context: AdminRequestContext = request["context"]

    their_public_did = request.query["their_public_did"]
    my_label = request.query.get("my_label") or None
    my_endpoint = request.query.get("my_endpoint") or None
    mediation_id = request.query.get("mediation_id") or None
    alias = request.query.get("alias") or None
    use_public_did = json.loads(request.query.get("use_public_did", "null"))
    use_did = request.query.get("use_did") or None
    use_did_method = request.query.get("use_did_method") or None
    goal_code = request.query.get("goal_code") or None
    goal = request.query.get("goal") or None
    auto_accept = json.loads(request.query.get("auto_accept", "null"))
    protocol = request.query.get("protocol") or None

    profile = context.profile
    didx_mgr = DIDXManager(profile)
    try:
        didx_request = await didx_mgr.create_request_implicit(
            their_public_did=their_public_did,
            my_label=my_label,
            my_endpoint=my_endpoint,
            mediation_id=mediation_id,
            use_public_did=use_public_did,
            use_did=use_did,
            use_did_method=use_did_method,
            alias=alias,
            goal_code=goal_code,
            goal=goal,
            auto_accept=auto_accept,
            protocol=protocol,
        )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (StorageError, WalletError, DIDXManagerError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(didx_request.serialize())


@docs(
    tags=["did-exchange"],
    summary="Receive request against public DID's implicit invitation",
    deprecated=True,
)
@querystring_schema(DIDXReceiveRequestImplicitQueryStringSchema())
@request_schema(DIDXRequestSchema())
@response_schema(ConnRecordSchema(), 200, description="")
@tenant_authentication
async def didx_receive_request_implicit(request: web.BaseRequest):
    """Request handler for receiving a request against public DID's implicit invitation.

    Args:
        request: aiohttp request object

    Returns:
        The resulting connection record details

    """
    context: AdminRequestContext = request["context"]

    body = await request.json()
    alias = request.query.get("alias")
    auto_accept = json.loads(request.query.get("auto_accept", "null"))

    profile = context.profile
    didx_mgr = DIDXManager(profile)
    try:
        didx_request = DIDXRequest.deserialize(body)
        conn_rec = await didx_mgr.receive_request(
            request=didx_request,
            recipient_did=didx_request._thread.pthid.split(":")[-1],
            alias=alias,
            auto_accept_implicit=auto_accept,
        )
        result = conn_rec.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (StorageError, WalletError, DIDXManagerError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(result)


@docs(
    tags=["did-exchange"],
    summary="Accept a stored connection request",
)
@match_info_schema(DIDXConnIdMatchInfoSchema())
@querystring_schema(DIDXAcceptRequestQueryStringSchema())
@response_schema(ConnRecordSchema(), 200, description="")
@tenant_authentication
async def didx_accept_request(request: web.BaseRequest):
    """Request handler for accepting a stored connection request.

    Args:
        request: aiohttp request object

    Returns:
        The resulting connection record details

    """
    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]
    connection_id = request.match_info["conn_id"]
    my_endpoint = request.query.get("my_endpoint") or None
    mediation_id = request.query.get("mediation_id") or None
    use_public_did = json.loads(request.query.get("use_public_did", "null"))

    profile = context.profile
    didx_mgr = DIDXManager(profile)
    try:
        async with profile.session() as session:
            conn_rec = await ConnRecord.retrieve_by_id(session, connection_id)
        response = await didx_mgr.create_response(
            conn_rec=conn_rec,
            my_endpoint=my_endpoint,
            mediation_id=mediation_id,
            use_public_did=use_public_did,
        )
        result = conn_rec.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (StorageError, WalletError, DIDXManagerError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(response, connection_id=conn_rec.connection_id)
    return web.json_response(result)


@docs(
    tags=["did-exchange"],
    summary="Abandon or reject a DID Exchange",
)
@match_info_schema(DIDXConnIdMatchInfoSchema())
@request_schema(DIDXRejectRequestSchema())
@response_schema(ConnRecordSchema(), 200, description="")
@tenant_authentication
async def didx_reject(request: web.BaseRequest):
    """Abandon or reject a DID Exchange."""
    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]

    connection_id = request.match_info["conn_id"]
    body = await request.json()
    reason = body.get("reason")

    profile = context.profile
    didx_mgr = DIDXManager(profile)
    try:
        async with profile.session() as session:
            conn_rec = await ConnRecord.retrieve_by_id(session, connection_id)
        report = await didx_mgr.reject(conn_rec=conn_rec, reason=reason)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (StorageError, WalletError, DIDXManagerError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(report, connection_id=conn_rec.connection_id)
    result = conn_rec.serialize()
    return web.json_response(result)


async def register(app: web.Application):
    """Register routes."""
    app.add_routes(
        [
            web.post(
                "/didexchange/{conn_id}/accept-invitation",
                didx_accept_invitation,
            ),
            web.post("/didexchange/create-request", didx_create_request_implicit),
            web.post("/didexchange/receive-request", didx_receive_request_implicit),
            web.post("/didexchange/{conn_id}/accept-request", didx_accept_request),
            web.post("/didexchange/{conn_id}/reject", didx_reject),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""
    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "did-exchange",
            "description": "Connection management via DID exchange",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
