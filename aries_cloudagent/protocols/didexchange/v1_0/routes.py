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

from marshmallow import fields

from ....admin.request_context import AdminRequestContext
from ....connections.models.conn_record import ConnRecord, ConnRecordSchema
from ....messaging.models.base import BaseModelError
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import ENDPOINT, UUIDFour
from ....storage.error import StorageError, StorageNotFoundError
from ....wallet.error import WalletError

from ...out_of_band.v1_0.messages.invitation import (
    InvitationMessage as OOBInvitation,
    InvitationMessageSchema as OOBInvitationSchema,
)

from .manager import DIDXManager, DIDXManagerError
from .message_types import SPEC_URI


class DIDXReceiveInvitationRequestSchema(OOBInvitationSchema):
    """Request schema for receive invitation request."""

    service = fields.Field()


class DIDXReceiveInvitationQueryStringSchema(OpenAPISchema):
    """Parameters and validators for receive invitation request query string."""

    alias = fields.Str(
        description="Alias",
        required=False,
        example="Barry",
    )
    auto_accept = fields.Boolean(
        description="Auto-accept connection (defaults to configuration)",
        required=False,
    )


class DIDXAcceptInvitationQueryStringSchema(OpenAPISchema):
    """Parameters and validators for accept invitation request query string."""

    my_endpoint = fields.Str(description="My URL endpoint", required=False, **ENDPOINT)
    my_label = fields.Str(
        description="Label for connection", required=False, example="Broker"
    )


class DIDXAcceptRequestQueryStringSchema(OpenAPISchema):
    """Parameters and validators for accept conn-request web-request query string."""

    my_endpoint = fields.Str(description="My URL endpoint", required=False, **ENDPOINT)


class DIDXConnIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    conn_id = fields.Str(
        description="Connection identifier", required=True, example=UUIDFour.EXAMPLE
    )


class DIDXConnIdRefIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection and ref ids."""

    conn_id = fields.Str(
        description="Connection identifier", required=True, example=UUIDFour.EXAMPLE
    )

    ref_id = fields.Str(
        description="Inbound connection identifier",
        required=True,
        example=UUIDFour.EXAMPLE,
    )


@docs(
    tags=["did-exchange"],
    summary="Receive a new connection invitation",
)
@querystring_schema(DIDXReceiveInvitationQueryStringSchema())
@request_schema(DIDXReceiveInvitationRequestSchema())
@response_schema(ConnRecordSchema(), 200, description="")
async def didx_receive_invitation(request: web.BaseRequest):
    """
    Request handler for receiving a new connection invitation.

    Args:
        request: aiohttp request object

    Returns:
        The resulting connection record details

    """
    context: AdminRequestContext = request["context"]
    if context.settings.get("admin.no_receive_invites"):
        raise web.HTTPForbidden(
            reason="Configuration does not allow receipt of invitations"
        )
    session = await context.session()
    didx_mgr = DIDXManager(session)
    invitation_json = await request.json()

    try:
        invitation = OOBInvitation.deserialize(invitation_json)
        auto_accept = json.loads(request.query.get("auto_accept", "null"))
        alias = request.query.get("alias")
        conn_rec = await didx_mgr.receive_invitation(
            invitation,
            auto_accept=auto_accept,
            alias=alias,
        )
        result = conn_rec.serialize()
    except (DIDXManagerError, StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(result)


@docs(
    tags=["did-exchange"],
    summary="Accept a stored connection invitation",
)
@match_info_schema(DIDXConnIdMatchInfoSchema())
@querystring_schema(DIDXAcceptInvitationQueryStringSchema())
@response_schema(ConnRecordSchema(), 200, description="")
async def didx_accept_invitation(request: web.BaseRequest):
    """
    Request handler for accepting a stored connection invitation.

    Args:
        request: aiohttp request object

    Returns:
        The resulting connection record details

    """
    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]
    connection_id = request.match_info["conn_id"]
    session = await context.session()

    try:
        conn_rec = await ConnRecord.retrieve_by_id(session, connection_id)
        didx_mgr = DIDXManager(session)
        my_label = request.query.get("my_label") or None
        my_endpoint = request.query.get("my_endpoint") or None
        request = await didx_mgr.create_request(conn_rec, my_label, my_endpoint)
        result = conn_rec.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (StorageError, WalletError, DIDXManagerError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(request, connection_id=conn_rec.connection_id)

    return web.json_response(result)


@docs(
    tags=["did-exchange"],
    summary="Accept a stored connection request",
)
@match_info_schema(DIDXConnIdMatchInfoSchema())
@querystring_schema(DIDXAcceptRequestQueryStringSchema())
@response_schema(ConnRecordSchema(), 200, description="")
async def didx_accept_request(request: web.BaseRequest):
    """
    Request handler for accepting a stored connection request.

    Args:
        request: aiohttp request object

    Returns:
        The resulting connection record details

    """
    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]
    connection_id = request.match_info["conn_id"]
    session = await context.session()

    try:
        conn_rec = await ConnRecord.retrieve_by_id(session, connection_id)
        didx_mgr = DIDXManager(session)
        my_endpoint = request.query.get("my_endpoint") or None
        response = await didx_mgr.create_response(conn_rec, my_endpoint)
        result = conn_rec.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (StorageError, WalletError, DIDXManagerError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    # TODO check if conn rec state is correct here? Maybe pass outbound into conn mgr
    await outbound_handler(response, connection_id=conn_rec.connection_id)
    return web.json_response(result)


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.post("/didexchange/receive-invitation", didx_receive_invitation),
            web.post(
                "/didexchange/{conn_id}/accept-invitation",
                didx_accept_invitation,
            ),
            web.post("/didexchange/{conn_id}/accept-request", didx_accept_request),
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
