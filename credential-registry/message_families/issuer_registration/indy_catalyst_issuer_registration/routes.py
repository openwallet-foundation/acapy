"""Issuer registration admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema

from marshmallow import fields, Schema

from indy_catalyst_agent.messaging.connections.models.connection_record import (
    ConnectionRecord,
)
from indy_catalyst_agent.storage.error import StorageNotFoundError

from .manager import IssuerRegistrationManager


class IssuerRegistrationRequestSchema(Schema):
    """Request schema for issuer registration."""

    class IssuerRegistrationNestedSchema(Schema):
        """Issuer registration nested schema."""

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

        issuer = fields.Nested(IssuerSchema, required=True)
        credential_types = fields.List(fields.Nested(CredentialType), required=False)

    issuer_registration = fields.Nested(IssuerRegistrationNestedSchema, required=True)
    connection_id = fields.Str(required=True)


@docs(tags=["issuer_registration"], summary="Send an issuer registration to a target")
@request_schema(IssuerRegistrationRequestSchema())
async def issuer_registration_send(request: web.BaseRequest):
    """
    Request handler for sending an issuer registration message to a connection.

    Args:
        request: aiohttp request object

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    body = await request.json()

    connection_id = body.get("connection_id")
    issuer_registration = body.get("issuer_registration")

    issuer_registration_manager = IssuerRegistrationManager(context)

    try:
        connection = await ConnectionRecord.retrieve_by_id(context, connection_id)
    except StorageNotFoundError:
        return web.HTTPNotFound()

    if connection.is_active:
        (
            _,
            issuer_registration_message,
        ) = await issuer_registration_manager.prepare_send(
            connection_id, issuer_registration
        )

        await outbound_handler(issuer_registration_message, connection_id=connection_id)

        await connection.log_activity(
            context, "issuer_registration", connection.DIRECTION_SENT
        )

    return web.HTTPOk()


async def register(app: web.Application):
    """Register routes."""
    app.add_routes([web.post("/issuer_registration/send", issuer_registration_send)])
