"""Out-of-band handling admin routes."""

import json
import logging

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, request_schema, response_schema

from marshmallow import fields, validate
from marshmallow.exceptions import ValidationError

from ....admin.request_context import AdminRequestContext
from ....messaging.models.base import BaseModelError
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import UUID4_EXAMPLE, UUID4_VALIDATE
from ....storage.error import StorageError, StorageNotFoundError
from ...didcomm_prefix import DIDCommPrefix
from ...didexchange.v1_0.manager import DIDXManagerError
from .manager import OutOfBandManager, OutOfBandManagerError
from .message_types import SPEC_URI
from .messages.invitation import HSProto, InvitationMessage, InvitationMessageSchema
from .models.invitation import InvitationRecordSchema
from .models.oob_record import OobRecordSchema

LOGGER = logging.getLogger(__name__)


class OutOfBandModuleResponseSchema(OpenAPISchema):
    """Response schema for Out of Band Module."""


class InvitationCreateQueryStringSchema(OpenAPISchema):
    """Parameters and validators for create invitation request query string."""

    auto_accept = fields.Boolean(
        required=False,
        metadata={"description": "Auto-accept connection (defaults to configuration)"},
    )
    multi_use = fields.Boolean(
        required=False,
        metadata={"description": "Create invitation for multiple use (default false)"},
    )


class InvitationCreateRequestSchema(OpenAPISchema):
    """Invitation create request Schema."""

    class AttachmentDefSchema(OpenAPISchema):
        """Attachment Schema."""

        _id = fields.Str(
            data_key="id",
            metadata={
                "description": "Attachment identifier",
                "example": "attachment-0",
            },
        )
        _type = fields.Str(
            data_key="type",
            validate=validate.OneOf(["credential-offer", "present-proof"]),
            metadata={"description": "Attachment type", "example": "present-proof"},
        )

    attachments = fields.Nested(
        AttachmentDefSchema,
        many=True,
        required=False,
        metadata={"description": "Optional invitation attachments"},
    )
    handshake_protocols = fields.List(
        fields.Str(
            validate=lambda hsp: HSProto.get(hsp) is not None,
            metadata={
                "description": "Handshake protocol to specify in invitation",
                "example": DIDCommPrefix.qualify_current(HSProto.RFC23.name),
            },
        ),
        required=False,
    )
    accept = fields.List(
        fields.Str(),
        required=False,
        metadata={
            "description": (
                "List of mime type in order of preference that should be use in"
                " responding to the message"
            ),
            "example": ["didcomm/aip1", "didcomm/aip2;env=rfc19"],
        },
    )
    use_public_did = fields.Boolean(
        dump_default=False,
        metadata={
            "description": "Whether to use public DID in invitation",
            "example": False,
        },
    )
    metadata = fields.Dict(
        required=False,
        metadata={
            "description": (
                "Optional metadata to attach to the connection created with the"
                " invitation"
            )
        },
    )
    my_label = fields.Str(
        required=False,
        metadata={
            "description": "Label for connection invitation",
            "example": "Invitation to Barry",
        },
    )
    protocol_version = fields.Str(
        required=False,
        metadata={"description": "OOB protocol version", "example": "1.1"},
    )
    alias = fields.Str(
        required=False,
        metadata={"description": "Alias for connection", "example": "Barry"},
    )
    mediation_id = fields.Str(
        required=False,
        validate=UUID4_VALIDATE,
        metadata={
            "description": "Identifier for active mediation record to be used",
            "example": UUID4_EXAMPLE,
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


class InvitationReceiveQueryStringSchema(OpenAPISchema):
    """Parameters and validators for receive invitation request query string."""

    alias = fields.Str(
        required=False,
        metadata={"description": "Alias for connection", "example": "Barry"},
    )
    auto_accept = fields.Boolean(
        required=False,
        metadata={"description": "Auto-accept connection (defaults to configuration)"},
    )
    use_existing_connection = fields.Boolean(
        required=False,
        dump_default=True,
        metadata={"description": "Use an existing connection, if possible"},
    )
    mediation_id = fields.Str(
        required=False,
        validate=UUID4_VALIDATE,
        metadata={
            "description": "Identifier for active mediation record to be used",
            "example": UUID4_EXAMPLE,
        },
    )


@docs(
    tags=["out-of-band"],
    summary="Create a new connection invitation",
)
@querystring_schema(InvitationCreateQueryStringSchema())
@request_schema(InvitationCreateRequestSchema())
@response_schema(InvitationRecordSchema(), description="")
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
    handshake_protocols = body.get("handshake_protocols", [])
    service_accept = body.get("accept")
    use_public_did = body.get("use_public_did", False)
    metadata = body.get("metadata")
    my_label = body.get("my_label")
    alias = body.get("alias")
    mediation_id = body.get("mediation_id")
    protocol_version = body.get("protocol_version")
    goal_code = body.get("goal_code")
    goal = body.get("goal")

    multi_use = json.loads(request.query.get("multi_use", "false"))
    auto_accept = json.loads(request.query.get("auto_accept", "null"))

    profile = context.profile
    oob_mgr = OutOfBandManager(profile)
    try:
        invi_rec = await oob_mgr.create_invitation(
            my_label=my_label,
            auto_accept=auto_accept,
            public=use_public_did,
            hs_protos=[
                h for h in [HSProto.get(hsp) for hsp in handshake_protocols] if h
            ],
            multi_use=multi_use,
            attachments=attachments,
            metadata=metadata,
            alias=alias,
            mediation_id=mediation_id,
            service_accept=service_accept,
            protocol_version=protocol_version,
            goal_code=goal_code,
            goal=goal,
        )
    except (StorageNotFoundError, ValidationError, OutOfBandManagerError) as e:
        raise web.HTTPBadRequest(reason=e.roll_up)

    return web.json_response(invi_rec.serialize())


@docs(
    tags=["out-of-band"],
    summary="Receive a new connection invitation",
)
@querystring_schema(InvitationReceiveQueryStringSchema())
@request_schema(InvitationMessageSchema())
@response_schema(OobRecordSchema(), 200, description="")
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

    profile = context.profile
    oob_mgr = OutOfBandManager(profile)

    body = await request.json()
    auto_accept = json.loads(request.query.get("auto_accept", "null"))
    alias = request.query.get("alias")
    # By default, try to use an existing connection
    use_existing_conn = json.loads(request.query.get("use_existing_connection", "true"))
    mediation_id = request.query.get("mediation_id")
    try:
        invitation = InvitationMessage.deserialize(body)
        result = await oob_mgr.receive_invitation(
            invitation,
            auto_accept=auto_accept,
            alias=alias,
            use_existing_connection=use_existing_conn,
            mediation_id=mediation_id,
        )
    except (DIDXManagerError, StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(result.serialize())


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
