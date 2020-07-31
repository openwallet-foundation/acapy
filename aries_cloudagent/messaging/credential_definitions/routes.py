"""Credential definition admin routes."""

from asyncio import ensure_future, shield

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
from ...tails.base import BaseTailsServer

from ..valid import INDY_CRED_DEF_ID, INDY_SCHEMA_ID, INDY_VERSION

from ...revocation.error import RevocationError, RevocationNotSupportedError
from ...revocation.indy import IndyRevocation

from ...ledger.error import LedgerError

from .util import CredDefQueryStringSchema, CRED_DEF_TAGS, CRED_DEF_SENT_RECORD_TYPE


class CredentialDefinitionSendRequestSchema(Schema):
    """Request schema for schema send request."""

    schema_id = fields.Str(description="Schema identifier", **INDY_SCHEMA_ID)
    support_revocation = fields.Boolean(
        required=False, description="Revocation supported flag"
    )
    revocation_registry_size = fields.Int(required=False)
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
        **INDY_CRED_DEF_ID,
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
        **INDY_CRED_DEF_ID,
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
    revocation_registry_size = body.get("revocation_registry_size")

    ledger: BaseLedger = await context.inject(BaseLedger, required=False)
    if not ledger:
        reason = "No ledger available"
        if not context.settings.get_value("wallet.type"):
            reason += ": missing wallet-type?"
        raise web.HTTPForbidden(reason=reason)

    issuer: BaseIssuer = await context.inject(BaseIssuer)
    try:
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
    except LedgerError as e:
        raise web.HTTPBadRequest(reason=e.message) from e

    # If revocation is requested, create revocation registry
    if support_revocation:
        tails_base_url = context.settings.get("tails_server_base_url")
        if not tails_base_url:
            raise web.HTTPBadRequest(reason="tails_server_base_url not configured")
        try:
            # Create registry
            issuer_did = credential_definition_id.split(":")[0]
            revoc = IndyRevocation(context)
            registry_record = await revoc.init_issuer_registry(
                credential_definition_id,
                issuer_did,
                max_cred_num=revocation_registry_size,
            )

        except RevocationNotSupportedError as e:
            raise web.HTTPBadRequest(reason=e.message) from e
        await shield(registry_record.generate_registry(context))
        try:
            await registry_record.set_tails_file_public_uri(
                context, f"{tails_base_url}/{registry_record.revoc_reg_id}"
            )
            await registry_record.publish_registry_definition(context)
            await registry_record.publish_registry_entry(context)

            tails_server: BaseTailsServer = await context.inject(BaseTailsServer)
            upload_success, reason = await tails_server.upload_tails_file(
                context, registry_record.revoc_reg_id, registry_record.tails_local_path
            )
            if not upload_success:
                raise web.HTTPInternalServerError(
                    reason=f"Tails file failed to upload: {reason}"
                )

            pending_registry_record = await revoc.init_issuer_registry(
                registry_record.cred_def_id,
                registry_record.issuer_did,
                max_cred_num=registry_record.max_cred_num,
            )
            ensure_future(
                pending_registry_record.stage_pending_registry_definition(context)
            )

        except RevocationError as e:
            raise web.HTTPBadRequest(reason=e.message) from e

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
