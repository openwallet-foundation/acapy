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

from marshmallow import fields

from ...indy.issuer import IndyIssuer
from ...ledger.base import BaseLedger
from ...storage.base import BaseStorage
from ...tails.base import BaseTailsServer

from ..models.openapi import OpenAPISchema
from ..valid import INDY_CRED_DEF_ID, INDY_REV_REG_SIZE, INDY_SCHEMA_ID, INDY_VERSION

from ...revocation.error import RevocationError, RevocationNotSupportedError
from ...revocation.indy import IndyRevocation

from ...ledger.error import LedgerError

from .util import CredDefQueryStringSchema, CRED_DEF_TAGS, CRED_DEF_SENT_RECORD_TYPE


class CredentialDefinitionSendRequestSchema(OpenAPISchema):
    """Request schema for schema send request."""

    schema_id = fields.Str(description="Schema identifier", **INDY_SCHEMA_ID)
    support_revocation = fields.Boolean(
        required=False, description="Revocation supported flag"
    )
    revocation_registry_size = fields.Int(
        description="Revocation registry size",
        required=False,
        strict=True,
        **INDY_REV_REG_SIZE,
    )
    tag = fields.Str(
        required=False,
        description="Credential definition identifier tag",
        default="default",
        example="default",
    )


class CredentialDefinitionSendResultsSchema(OpenAPISchema):
    """Results schema for schema send request."""

    credential_definition_id = fields.Str(
        description="Credential definition identifier", **INDY_CRED_DEF_ID
    )


class CredentialDefinitionSchema(OpenAPISchema):
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


class CredentialDefinitionGetResultsSchema(OpenAPISchema):
    """Results schema for schema get request."""

    credential_definition = fields.Nested(CredentialDefinitionSchema)


class CredentialDefinitionsCreatedResultsSchema(OpenAPISchema):
    """Results schema for cred-defs-created request."""

    credential_definition_ids = fields.List(
        fields.Str(description="Credential definition identifiers", **INDY_CRED_DEF_ID)
    )


class CredDefIdMatchInfoSchema(OpenAPISchema):
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
    rev_reg_size = body.get("revocation_registry_size")

    session = await context.session()
    ledger = session.inject(BaseLedger, required=False)
    if not ledger:
        reason = "No ledger available"
        if not session.settings.get_value("wallet.type"):
            reason += ": missing wallet-type?"
        raise web.HTTPForbidden(reason=reason)

    issuer = session.inject(IndyIssuer)
    try:  # even if in wallet, send it and raise if erroneously so
        async with ledger:
            (cred_def_id, cred_def, novel) = await shield(
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

    # If revocation is requested and cred def is novel, create revocation registry
    if support_revocation and novel:
        tails_base_url = session.settings.get("tails_server_base_url")
        if not tails_base_url:
            raise web.HTTPBadRequest(reason="tails_server_base_url not configured")
        try:
            # Create registry
            revoc = IndyRevocation(session)
            registry_record = await revoc.init_issuer_registry(
                cred_def_id,
                max_cred_num=rev_reg_size,
            )

        except RevocationNotSupportedError as e:
            raise web.HTTPBadRequest(reason=e.message) from e
        await shield(registry_record.generate_registry(session))
        try:
            await registry_record.set_tails_file_public_uri(
                session, f"{tails_base_url}/{registry_record.revoc_reg_id}"
            )
            await registry_record.send_def(session)
            await registry_record.send_entry(session)

            # stage pending registry independent of whether tails server is OK
            pending_registry_record = await revoc.init_issuer_registry(
                registry_record.cred_def_id,
                max_cred_num=registry_record.max_cred_num,
            )
            ensure_future(
                pending_registry_record.stage_pending_registry(session, max_attempts=16)
            )

            tails_server = session.inject(BaseTailsServer)
            (upload_success, reason) = await tails_server.upload_tails_file(
                session,
                registry_record.revoc_reg_id,
                registry_record.tails_local_path,
                interval=0.8,
                backoff=-0.5,
                max_attempts=5,  # heuristic: respect HTTP timeout
            )
            if not upload_success:
                raise web.HTTPInternalServerError(
                    reason=(
                        f"Tails file for rev reg {registry_record.revoc_reg_id} "
                        f"failed to upload: {reason}"
                    )
                )

        except RevocationError as e:
            raise web.HTTPBadRequest(reason=e.message) from e

    return web.json_response({"credential_definition_id": cred_def_id})


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

    session = await context.session()
    storage = session.inject(BaseStorage)
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

    cred_def_id = request.match_info["cred_def_id"]

    session = await context.session()
    ledger = session.inject(BaseLedger, required=False)
    if not ledger:
        reason = "No ledger available"
        if not session.settings.get_value("wallet.type"):
            reason += ": missing wallet-type?"
        raise web.HTTPForbidden(reason=reason)

    async with ledger:
        cred_def = await ledger.get_credential_definition(cred_def_id)

    return web.json_response({"credential_definition": cred_def})


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
