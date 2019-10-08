"""Credential definition admin routes."""

from asyncio import shield

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema

from marshmallow import fields, Schema

from ...ledger.base import BaseLedger

from ..valid import INDY_CRED_DEF_ID, INDY_SCHEMA_ID, INDY_VERSION


class CredentialDefinitionSendRequestSchema(Schema):
    """Request schema for schema send request."""

    schema_id = fields.Str(
        description="Schema identifier",
        **INDY_SCHEMA_ID
    )


class CredentialDefinitionSendResultsSchema(Schema):
    """Results schema for schema send request."""

    credential_definition_id = fields.Str(
        description="Credential definition identifier",
        **INDY_CRED_DEF_ID
    )


class CredentialDefinitionSchema(Schema):
    """Credential definition schema."""

    ver = fields.Str(
        description="Node protocol version",
        **INDY_VERSION
    )
    ident = fields.Str(
        description="Credential definition identifier",
        data_key="id",
        **INDY_CRED_DEF_ID
    )
    schemaId = fields.Str(
        description="Schema identifier within credential definition identifier",
        example=":".join(INDY_CRED_DEF_ID["example"].split(":")[3:-1])  # long or short
    )
    typ = fields.Constant(
        constant="CL",
        description="Signature type: CL for Camenisch-Lysyanskaya",
        data_key="type",
        example="CL",
    )
    tag = fields.Str(
        description="Tag within credential definition identifier",
        example=INDY_CRED_DEF_ID["example"].split(":")[-1]
    )
    value = fields.Dict(
        description="Credential definition primary and revocation values"
    )


class CredentialDefinitionGetResultsSchema(Schema):
    """Results schema for schema get request."""

    credential_definition = fields.Nested(CredentialDefinitionSchema)


@docs(
    tags=["credential-definition"],
    summary="Sends a credential definition to the ledger",
)
@request_schema(CredentialDefinitionSendRequestSchema())
@response_schema(CredentialDefinitionSendResultsSchema(), 200)
async def credential_definitions_send_credential_definition(request: web.BaseRequest):
    """
    Request handler for sending a credential definition to the ledger.

    Args:
        request: aiohttp request object

    Returns:
        The credential offer details.

    """

    context = request.app["request_context"]

    body = await request.json()

    schema_id = body.get("schema_id")

    ledger: BaseLedger = await context.inject(BaseLedger)
    async with ledger:
        credential_definition_id = await shield(
            ledger.send_credential_definition(schema_id)
        )

    return web.json_response({"credential_definition_id": credential_definition_id})


@docs(
    tags=["credential-definition"],
    summary="Gets a credential definition from the ledger",
)
@response_schema(CredentialDefinitionGetResultsSchema(), 200)
async def credential_definitions_get_credential_definition(request: web.BaseRequest):
    """
    Request handler for getting a credential definition from the ledger.

    Args:
        request: aiohttp request object

    Returns:
        The credential offer details.

    """

    context = request.app["request_context"]

    credential_definition_id = request.match_info["id"]

    ledger: BaseLedger = await context.inject(BaseLedger)
    async with ledger:
        credential_definition = await ledger.get_credential_definition(
            credential_definition_id
        )

    return web.json_response({"credential_definition": credential_definition})


async def register(app: web.Application):
    """Register routes."""
    app.add_routes(
        [
            web.post(
                "/credential-definitions",
                credential_definitions_send_credential_definition,
            )
        ]
    )
    app.add_routes(
        [
            web.get(
                "/credential-definitions/{id}",
                credential_definitions_get_credential_definition,
            )
        ]
    )
