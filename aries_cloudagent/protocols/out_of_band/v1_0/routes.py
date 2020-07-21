"""Connection handling admin routes."""

import json
import logging

from aiohttp import web
from aiohttp_apispec import docs, request_schema
from marshmallow import fields, Schema
from marshmallow.exceptions import ValidationError

from ....storage.error import StorageNotFoundError

from .manager import OutOfBandManager, OutOfBandManagerError
from .messages.invitation import InvitationSchema


LOGGER = logging.getLogger(__name__)


class InvitationCreateRequestSchema(Schema):
    """Invitation create request Schema."""

    class AttachmentDefSchema(Schema):
        """Attachment Schema."""

        _id = fields.String(data_key="id")
        _type = fields.String(data_key="type")

    attachments = fields.Nested(AttachmentDefSchema, many=True, required=False)
    include_handshake = fields.Boolean(default=False)
    use_public_did = fields.Boolean(default=False)


class InvitationSchema(InvitationSchema):
    """Invitation Schema."""

    service = fields.Field()


@docs(
    tags=["out-of-band"], summary="Create a new connection invitation",
)
@request_schema(InvitationCreateRequestSchema())
async def invitation_create(request: web.BaseRequest):
    """
    Request handler for creating a new connection invitation.

    Args:
        request: aiohttp request object

    Returns:
        The out of band invitation details

    """
    context = request.app["request_context"]

    body = await request.json()

    attachments = body.get("attachments")
    include_handshake = body.get("include_handshake")
    use_public_did = body.get("use_public_did")
    multi_use = json.loads(request.query.get("multi_use", "false"))
    oob_mgr = OutOfBandManager(context)

    try:
        invitation = await oob_mgr.create_invitation(
            multi_use=multi_use,
            attachments=attachments,
            include_handshake=include_handshake,
            use_public_did=use_public_did,
        )
    except (StorageNotFoundError, ValidationError, OutOfBandManagerError) as e:
        raise web.HTTPBadRequest(reason=str(e))

    return web.json_response(invitation.serialize())


@docs(
    tags=["out-of-band"], summary="Create a new connection invitation",
)
@request_schema(InvitationSchema())
async def invitation_receive(request: web.BaseRequest):
    """
    Request handler for creating a new connection invitation.

    Args:
        request: aiohttp request object

    Returns:
        The out of band invitation details

    """
    context = request.app["request_context"]
    body = await request.json()

    oob_mgr = OutOfBandManager(context)

    invitation = await oob_mgr.receive_invitation(invitation=body)

    return web.json_response(invitation.serialize())


async def register(app: web.Application):
    """Register routes."""
    app.add_routes(
        [
            # web.get("/out-of-band", invitation_list),
            # web.get("/out-of-band/{id}", invitation_retrieve),
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
                "url": (
                    "https://github.com/hyperledger/aries-rfcs/tree/"
                    "2da7fc4ee043effa3a9960150e7ba8c9a4628b68/features/0434-outofband"
                ),
            },
        }
    )
