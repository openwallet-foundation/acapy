"""Connection handling admin routes."""

import json

from aiohttp import web
from aiohttp_apispec import docs

from .manager import OutOfBandManager


@docs(
    tags=["out-of-band"], summary="Create a new connection invitation",
)
async def invitation_create(request: web.BaseRequest):
    """
    Request handler for creating a new connection invitation.

    Args:
        request: aiohttp request object

    Returns:
        The out of band invitation details

    """
    context = request.app["request_context"]
    multi_use = json.loads(request.query.get("multi_use", "false"))
    # base_url = context.settings.get("invite_base_url")

    oob_mgr = OutOfBandManager(context)
    invitation = await oob_mgr.create_invitation(multi_use=multi_use)

    return web.json_response(invitation.serialize())


async def register(app: web.Application):
    """Register routes."""
    app.add_routes(
        [
            # web.get("/out-of-band", invitation_list),
            # web.get("/out-of-band/{id}", invitation_retrieve),
            # web.post("/out-of-band/create-invitation", invitation_create),
        ]
    )
