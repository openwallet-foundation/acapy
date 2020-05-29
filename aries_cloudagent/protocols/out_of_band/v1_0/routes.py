"""Connection handling admin routes."""

import json
import logging

from aiohttp import web
from aiohttp_apispec import docs, request_schema

from marshmallow import fields, Schema

from .manager import OutOfBandManager

LOGGER = logging.getLogger(__name__)


class InvitationCreateRequestSchema(Schema):
    class AttachmentDefSchema(Schema):
        _id = fields.String(data_key="id")
        _type = fields.String(data_key="type")

    attachments = fields.Nested(AttachmentDefSchema, many=True, required=False)


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

    multi_use = json.loads(request.query.get("multi_use", "false"))
    # base_url = context.settings.get("invite_base_url")

    oob_mgr = OutOfBandManager(context)
    invitation = await oob_mgr.create_invitation(
        multi_use=multi_use, attachments=attachments
    )

    return web.json_response(invitation.serialize())


async def register(app: web.Application):
    """Register routes."""
    app.add_routes(
        [
            # web.get("/out-of-band", invitation_list),
            # web.get("/out-of-band/{id}", invitation_retrieve),
            web.post("/out-of-band/create-invitation", invitation_create),
        ]
    )
