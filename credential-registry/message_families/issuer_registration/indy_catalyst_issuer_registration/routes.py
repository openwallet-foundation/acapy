"""Issuer registration admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema

from marshmallow import fields, Schema

from indy_catalyst_agent.messaging.connections.models.connection_record import (
    ConnectionRecord,
)
from indy_catalyst_agent.storage.error import StorageNotFoundError

from .messages.register import IssuerRegistration


class IssuerRegistrationRequestSchema(Schema):
    """Request schema for issuer registration"""

    class IssuerSchema(Schema):
        """Isuer nested schema."""

        did = fields.Str(required=True)
        name = fields.Str(required=True)
        abbreviation = fields.Str(required=False)
        email = fields.Str(required=False)
        url = fields.Str(required=False)
        endpoint = fields.Str(required=False)
        logo_b64 = fields.Str(required=False)

    class CredentialType(Schema):
        """Isuer credential type schema."""

        name = fields.Str(required=True)
        schema = fields.Str(required=True)
        version = fields.Str(required=True)
        description = fields.Str(required=False)
        cardinality_fields = fields.List(fields.Dict, required=False)
        credential = fields.Str(required=False)
        mapping = fields.Dict(required=False)
        topic = fields.Str(required=False)
        caregory_labels = fields.List(fields.Str, required=False)
        claim_descriptions = fields.List(fields.Str, required=False)
        claim_labels = fields.List(fields.Str, required=False)
        logo_b64 = fields.Str(required=False)
        credential_def_id = fields.Str(required=True)
        endpoint = fields.Str(required=False)
        visible_fields = fields.List(fields.Str, required=False)

    fields.Nested(IssuerSchema, required=True)
    fields.List(fields.Nested(CredentialType), required=False)


@docs(tags=["issuer_registration"], summary="Send an issuer registration to a target")
@request_schema(IssuerRegistrationRequestSchema())
async def issuer_registration_send(request: web.BaseRequest):
    """
    Request handler for sending an issuer registration message to a connection.

    Args:
        request: aiohttp request object

    """
    context = request.app["request_context"]
    connection_id = request.match_info["id"]
    outbound_handler = request.app["outbound_message_router"]
    params = await request.body()

    try:
        connection = await ConnectionRecord.retrieve_by_id(context, connection_id)
    except StorageNotFoundError:
        return web.HTTPNotFound()

    if connection.is_active:
        msg = IssuerRegistration(**body)
        await outbound_handler(msg, connection_id=connection_id)

        await connection.log_activity(
            context, "issuer_registration", connection.DIRECTION_SENT
        )

    return web.HTTPOk()


async def register(app: web.Application):
    """Register routes."""
    app.add_routes([web.post("/issuer_registration/send", issuer_registration_send)])
