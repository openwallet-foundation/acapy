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

from marshmallow import fields, Schema, validate, validates_schema

from aries_cloudagent.connections.models.connection_record import (
    ConnectionRecord,
    ConnectionRecordSchema,
)
from aries_cloudagent.messaging.valid import (
    ENDPOINT,
    INDY_DID,
    INDY_RAW_PUBLIC_KEY,
    UUIDFour,
)
from aries_cloudagent.storage.error import StorageNotFoundError

from .manager import OutOfBandManager
from .messages.connection_invitation import (
    ConnectionInvitation,
    ConnectionInvitationSchema,
)


# @docs(
#     tags=["out-of-band"], summary="Query for out of band invitation",
# )
# async def invitation_list(request: web.BaseRequest):
#     """
#     Request handler for searching connection records.

#     Args:
#         request: aiohttp request object

#     Returns:
#         The connection list response

#     """
#     context = request.app["request_context"]
#     tag_filter = {}
#     for param_name in (
#         "invitation_id",
#         "my_did",
#         "their_did",
#         "request_id",
#     ):
#         if param_name in request.query and request.query[param_name] != "":
#             tag_filter[param_name] = request.query[param_name]
#     post_filter = {}
#     for param_name in (
#         "alias",
#         "initiator",
#         "state",
#         "their_role",
#     ):
#         if param_name in request.query and request.query[param_name] != "":
#             post_filter[param_name] = request.query[param_name]
#     records = await ConnectionRecord.query(context, tag_filter, post_filter)
#     results = [record.serialize() for record in records]
#     results.sort(key=connection_sort_key)
#     return web.json_response({"results": results})


# @docs(tags=["connection"], summary="Fetch a single connection record")
# async def invitation_retrieve(request: web.BaseRequest):
#     """
#     Request handler for fetching a single connection record.

#     Args:
#         request: aiohttp request object

#     Returns:
#         The connection record response

#     """
#     context = request.app["request_context"]
#     connection_id = request.match_info["conn_id"]
#     try:
#         record = await ConnectionRecord.retrieve_by_id(context, connection_id)
#     except StorageNotFoundError:
#         raise web.HTTPNotFound()
#     return web.json_response(record.serialize())


@docs(
    tags=["connection"], summary="Create a new connection invitation",
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
    base_url = context.settings.get("invite_base_url")

    oob_mgr = OutOfBandManager(context)
    invitation = await oob_mgr.create_invitation(multi_use=multi_use)
    
    return web.json_response(invitation.serialize())


async def register(app: web.Application):
    """Register routes."""
    app.add_routes(
        [
            # web.get("/out-of-band", invitation_list),
            # web.get("/out-of-band/{id}", invitation_retrieve),
            web.post("/connections/create-invitation", invitation_create),
        ]
    )
