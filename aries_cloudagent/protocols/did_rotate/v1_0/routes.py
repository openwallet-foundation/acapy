"""DID rotate admin routes."""

import logging

from aiohttp import web
from aiohttp_apispec import docs, json_schema, match_info_schema, response_schema
from marshmallow import fields

from ....admin.request_context import AdminRequestContext
from ....connections.models.conn_record import ConnRecord
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import DID_WEB_EXAMPLE, UUID4_EXAMPLE
from ....storage.error import StorageNotFoundError
from .manager import DIDRotateManager
from .message_types import SPEC_URI
from .messages.hangup import HangupSchema as HangupMessageSchema
from .messages.rotate import RotateSchema as RotateMessageSchema

LOGGER = logging.getLogger(__name__)


class DIDRotateConnIdMatchInfoSchema(OpenAPISchema):
    """Request to rotate a DID."""

    conn_id = fields.String(
        required=True,
        metadata={"description": "Connection identifier", "example": UUID4_EXAMPLE},
    )


class DIDRotateRequestJSONSchema(OpenAPISchema):
    """Request to rotate a DID."""

    to_did = fields.String(
        required=True,
        metadata={
            "description": "The DID the rotating party is rotating to",
            "example": DID_WEB_EXAMPLE,
        },
    )


@docs(tags=["did-rotate"], summary="Begin rotation of a DID as a rotator")
@match_info_schema(DIDRotateConnIdMatchInfoSchema())
@json_schema(DIDRotateRequestJSONSchema())
@response_schema(
    RotateMessageSchema(), 200, description="Rotate agent message for observer"
)
async def rotate(request: web.BaseRequest):
    """Request to rotate a DID."""

    LOGGER.debug("DID Rotate Rotate request >>>")

    context: AdminRequestContext = request["context"]

    profile = context.profile
    did_rotate_mgr = DIDRotateManager(profile)

    connection_id = request.match_info["conn_id"]

    body = await request.json()
    to_did = body["to_did"]

    async with context.session() as session:
        try:
            conn = await ConnRecord.retrieve_by_id(session, connection_id)
        except StorageNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err

        msg = await did_rotate_mgr.rotate_my_did(conn, to_did)

        return web.json_response(msg.serialize())


@docs(tags=["did-rotate"], summary="Send hangup of DID rotation as a rotator")
@match_info_schema(DIDRotateConnIdMatchInfoSchema())
@response_schema(
    HangupMessageSchema(), 200, description="Hangup agent message for observer"
)
async def hangup(request: web.BaseRequest):
    """Hangup a DID rotation."""

    LOGGER.debug("DID Rotate Hangup request >>>")

    context: AdminRequestContext = request["context"]

    profile = context.profile
    did_rotate_mgr = DIDRotateManager(profile)

    connection_id = request.match_info["conn_id"]

    async with context.session() as session:
        try:
            conn = await ConnRecord.retrieve_by_id(session, connection_id)
        except StorageNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err

        msg = await did_rotate_mgr.hangup(conn)

        return web.json_response(msg.serialize())


async def register(app: web.Application):
    """Register routes."""

    app.add_routes([web.post("/did-rotate/{conn_id}/rotate", rotate)])
    app.add_routes([web.post("/did-rotate/{conn_id}/hangup", hangup)])


def post_process_routes(app: web.Application):
    """Amend Swagger API."""

    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "did-rotate",
            "description": "Rotate a DID",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
