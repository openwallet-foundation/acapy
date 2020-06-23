"""Credential definition admin routes."""

from asyncio import shield

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)

from marshmallow import fields, Schema

from ...issuer.base import BaseIssuer
from ...ledger.base import BaseLedger
from ...storage.base import BaseStorage

from ..valid import INDY_CRED_DEF_ID, INDY_SCHEMA_ID, INDY_VERSION

from .util import CredDefQueryStringSchema, CRED_DEF_TAGS, CRED_DEF_SENT_RECORD_TYPE


class CredentialDefinitionSendRequestSchema(Schema):
    """Request schema for schema send request."""

    schema_id = fields.Str(description="Schema identifier", **INDY_SCHEMA_ID)
    support_revocation = fields.Boolean(
        required=False, description="Revocation supported flag"
    )
    tag = fields.Str(
        required=False,
        description="Credential definition identifier tag",
        default="default",
        example="default",
    )


class CredentialDefinitionSendResultsSchema(Schema):
    """Results schema for schema send request."""

    credential_definition_id = fields.Str(
        description="Credential definition identifier", **INDY_CRED_DEF_ID
    )


class CredentialDefinitionSchema(Schema):
    """Credential definition schema."""

    ver = fields.Str(description="Node protocol version", **INDY_VERSION)
    ident = fields.Str(
        description="Credential definition identifier",
        data_key="id",
        **INDY_CRED_DEF_ID
    )
    schemaId = fields.Str(
        description="Schema identifier within credential definition identifier",
        example=":".join(INDY_CRED_DEF_ID["example"].split(":")[3:-1]),  # long or short
    )
    typ = fields.Constant(
        constant="CL",
        description="Signature type: CL for Camenisch-Lysyanskaya",
        data_key="type",
        example="CL",
    )
    tag = fields.Str(
        description="Tag within credential definition identifier",
        example=INDY_CRED_DEF_ID["example"].split(":")[-1],
    )
    value = fields.Dict(
        description="Credential definition primary and revocation values"
    )


class CredentialDefinitionGetResultsSchema(Schema):
    """Results schema for schema get request."""

    credential_definition = fields.Nested(CredentialDefinitionSchema)


class CredentialDefinitionsCreatedResultsSchema(Schema):
    """Results schema for cred-defs-created request."""

    credential_definition_ids = fields.List(
        fields.Str(description="Credential definition identifiers", **INDY_CRED_DEF_ID)
    )


class CredDefIdMatchInfoSchema(Schema):
    """Path parameters and validators for request taking cred def id."""

    cred_def_id = fields.Str(
        description="Credential definition identifier",
        required=True,
        **INDY_CRED_DEF_ID
    )


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
        The credential definition identifier

    """
    context = request.app["request_context"]

    body = await request.json()

    schema_id = body.get("schema_id")
    support_revocation = bool(body.get("support_revocation"))
    tag = body.get("tag")

    ledger: BaseLedger = await context.inject(BaseLedger, required=False)
    if not ledger:
        reason = "No ledger available"
        if not context.settings.get_value("wallet.type"):
            reason += ": missing wallet-type?"
        raise web.HTTPForbidden(reason=reason)

    issuer: BaseIssuer = await context.inject(BaseIssuer)
    async with ledger:
        credential_definition_id, credential_definition = await shield(
            ledger.create_and_send_credential_definition(
                issuer,
                schema_id,
                signature_type=None,
                tag=tag,
                support_revocation=support_revocation,
            )
        )

    return web.json_response({"credential_definition_id": credential_definition_id})


@docs(
    tags=["credential-definition"],
    summary="Search for matching credential definitions that agent originated",
)
@querystring_schema(CredDefQueryStringSchema())
@response_schema(CredentialDefinitionsCreatedResultsSchema(), 200)
async def credential_definitions_created(request: web.BaseRequest):
    """
    Request handler for retrieving credential definitions that current agent created.

    Args:
        request: aiohttp request object

    Returns:
        The identifiers of matching credential definitions.

    """
    context = request.app["request_context"]

    storage = await context.inject(BaseStorage)
    found = await storage.search_records(
        type_filter=CRED_DEF_SENT_RECORD_TYPE,
        tag_query={
            tag: request.query[tag] for tag in CRED_DEF_TAGS if tag in request.query
        },
    ).fetch_all()

    return web.json_response(
        {"credential_definition_ids": [record.value for record in found]}
    )


@docs(
    tags=["credential-definition"],
    summary="Gets a credential definition from the ledger",
)
@match_info_schema(CredDefIdMatchInfoSchema())
@response_schema(CredentialDefinitionGetResultsSchema(), 200)
async def credential_definitions_get_credential_definition(request: web.BaseRequest):
    """
    Request handler for getting a credential definition from the ledger.

    Args:
        request: aiohttp request object

    Returns:
        The credential definition details.

    """
    context = request.app["request_context"]

    credential_definition_id = request.match_info["cred_def_id"]

    ledger: BaseLedger = await context.inject(BaseLedger, required=False)
    if not ledger:
        reason = "No ledger available"
        if not context.settings.get_value("wallet.type"):
            reason += ": missing wallet-type?"
        raise web.HTTPForbidden(reason=reason)

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
            ),
            web.get(
                "/credential-definitions/created",
                credential_definitions_created,
                allow_head=False,
            ),
            web.get(
                "/credential-definitions/{cred_def_id}",
                credential_definitions_get_credential_definition,
                allow_head=False,
            ),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "credential-definition",
            "description": "Credential definition operations",
            "externalDocs": {
                "description": "Specification",
                "url": (
                    "https://github.com/hyperledger/indy-node/blob/master/"
                    "design/anoncreds.md#cred_def"
                ),
            },
        }
    )
