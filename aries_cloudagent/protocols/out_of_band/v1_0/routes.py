"""Out-of-band handling admin routes."""

import json
import logging

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, request_schema, response_schema
from marshmallow import fields
from marshmallow.exceptions import ValidationError

from ....admin.request_context import AdminRequestContext
from ....connections.models.conn_record import ConnRecordSchema
from ....messaging.models.base import BaseModelError
from ....messaging.models.openapi import OpenAPISchema
from ....storage.error import StorageError, StorageNotFoundError

from ...didexchange.v1_0.manager import DIDXManagerError

from .manager import OutOfBandManager, OutOfBandManagerError
from .messages.invitation import InvitationMessage, InvitationMessageSchema
from .message_types import SPEC_URI

LOGGER = logging.getLogger(__name__)


class OutOfBandModuleResponseSchema(OpenAPISchema):
    """Response schema for Out of Band Module."""


class InvitationCreateQueryStringSchema(OpenAPISchema):
    """Parameters and validators for create invitation request query string."""

    auto_accept = fields.Boolean(
        description="Auto-accept connection (default as per configuration)",
        required=False,
    )
    multi_use = fields.Boolean(
        description="Create invitation for multiple use (default false)",
        required=False,
    )


class InvitationCreateRequestSchema(OpenAPISchema):
    """Invitation create request Schema."""

    class AttachmentDefSchema(OpenAPISchema):
        """Attachment Schema."""

        _id = fields.String(data_key="id")
        _type = fields.String(data_key="type")

    attachments = fields.Nested(AttachmentDefSchema, many=True, required=False)
    include_handshake = fields.Boolean(default=False)
    use_public_did = fields.Boolean(default=False)
    metadata = fields.Dict(
        description="Optional metadata to attach to the connection created with "
        "the invitation",
        required=False,
    )


class InvitationReceiveQueryStringSchema(OpenAPISchema):
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


class InvitationReceiveRequestSchema(InvitationMessageSchema):
    """Invitation request schema."""

    service = fields.Field()


@docs(
    tags=["out-of-band"],
    summary="Create a new connection invitation",
)
@querystring_schema(InvitationCreateQueryStringSchema())
@request_schema(InvitationCreateRequestSchema())
@response_schema(OutOfBandModuleResponseSchema(), description="")
async def invitation_create(request: web.BaseRequest):
    """
    Request handler for creating a new connection invitation.

    Args:
        request: aiohttp request object

    Returns:
        The out of band invitation details

    """
    context: AdminRequestContext = request["context"]

    body = await request.json() if request.body_exists else {}
    attachments = body.get("attachments")
    include_handshake = body.get("include_handshake")
    use_public_did = body.get("use_public_did", False)
    metadata = body.get("metadata")

    multi_use = json.loads(request.query.get("multi_use", json.dumps(use_public_did)))
    auto_accept = json.loads(
        request.query.get("auto_accept", "false" if use_public_did else "null")
    )
    session = await context.session()
    oob_mgr = OutOfBandManager(session)
    try:
        invitation = await oob_mgr.create_invitation(
            auto_accept=auto_accept,
            public=use_public_did,
            include_handshake=include_handshake,
            multi_use=multi_use,
            attachments=attachments,
            metadata=metadata,
        )
    except (StorageNotFoundError, ValidationError, OutOfBandManagerError) as e:
        raise web.HTTPBadRequest(reason=str(e))

    return web.json_response(invitation.serialize())


@docs(
    tags=["out-of-band"],
    summary="Receive a new connection invitation",
)
@querystring_schema(InvitationReceiveQueryStringSchema())
@request_schema(InvitationReceiveRequestSchema())
@response_schema(ConnRecordSchema(), 200, description="")
async def invitation_receive(request: web.BaseRequest):
    """
    Request handler for receiving a new connection invitation.

    Args:
        request: aiohttp request object

    Returns:
        The out of band invitation details

    """

    context: AdminRequestContext = request["context"]
    if context.settings.get("admin.no_receive_invites"):
        raise web.HTTPForbidden(
            reason="Configuration does not allow receipt of invitations"
        )

    session = await context.session()
    oob_mgr = OutOfBandManager(session)

    body = await request.json()
    auto_accept = json.loads(request.query.get("auto_accept", "null"))
    alias = request.query.get("alias")

    try:
        invitation = InvitationMessage.deserialize(body)
        conn_rec = await oob_mgr.receive_invitation(
            invitation,
            auto_accept=auto_accept,
            alias=alias,
        )
        result = conn_rec.serialize()
    except (DIDXManagerError, StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(result)


async def register(app: web.Application):
    """Register routes."""
    app.add_routes(
        [
            web.post("/out-of-band/create-invitation", invitation_create),
            web.post("/out-of-band/receive-invitation", invitation_receive),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "out-of-band",
            "description": "Out-of-band connections",
            "externalDocs": {
                "description": "Design",
                "url": SPEC_URI,
            },
        }
    )
