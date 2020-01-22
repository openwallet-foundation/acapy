"""Revocation registry admin routes."""

from asyncio import shield

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema

from marshmallow import fields, Schema

from ..messaging.credential_definitions.util import CRED_DEF_SENT_RECORD_TYPE
from ..messaging.valid import INDY_CRED_DEF_ID
from ..storage.base import BaseStorage

from .error import RevocationNotSupportedError
from .indy import IndyRevocation
from .models.issuer_revocation_record import IssuerRevocationRecordSchema
from .models.revocation_registry import RevocationRegistry


class RevRegCreateRequestSchema(Schema):
    """Request schema for revocation registry creation request."""

    credential_definition_id = fields.Str(
        description="Credential definition identifier", **INDY_CRED_DEF_ID
    )


class RevRegCreateResultSchema(Schema):
    """Result schema for revocation registry creation request."""

    result = IssuerRevocationRecordSchema()


@docs(
    tags=["revocation"], summary="Creates a new revocation registry",
)
@request_schema(RevRegCreateRequestSchema())
@response_schema(RevRegCreateResultSchema(), 200)
async def revocation_create_registry(request: web.BaseRequest):
    """
    Request handler for creating a new revocation registry.

    Args:
        request: aiohttp request object

    Returns:
        The revocation registry identifier

    """
    context = request.app["request_context"]

    body = await request.json()

    credential_definition_id = body.get("credential_definition_id")

    # check we published this cred def
    storage = await context.inject(BaseStorage)
    found = await storage.search_records(
        type_filter=CRED_DEF_SENT_RECORD_TYPE,
        tag_query={"cred_def_id": credential_definition_id},
    ).fetch_all()
    if not found:
        raise web.HTTPNotFound()

    try:
        issuer_did = credential_definition_id.split(":")[0]
        revoc = IndyRevocation(context)
        registry_record = await revoc.init_issuer_registry(
            credential_definition_id, issuer_did
        )
    except RevocationNotSupportedError as e:
        raise web.HTTPBadRequest() from e
    await shield(
        registry_record.generate_registry(context, RevocationRegistry.get_temp_dir())
    )
    print("generated tails file")
    # print(registry_record)
    await registry_record.publish_registry_definition(context)
    print("published registry definition")
    await registry_record.publish_registry_entry(context)
    print("published registry entry")

    return web.json_response({"result": registry_record.serialize()})


@docs(
    tags=["revocation"], summary="Publish current revocation registry",
)
@request_schema(RevRegCreateRequestSchema())
@response_schema(RevRegCreateResultSchema(), 200)
async def publish_current_registry(request: web.BaseRequest):
    """
    Request handler for publishing the current revocation registry.

    Args:
        request: aiohttp request object

    Returns:
        The revocation registry identifier

    """
    context = request.app["request_context"]

    body = await request.json()

    credential_definition_id = body.get("credential_definition_id")

    # check we published this cred def
    storage = await context.inject(BaseStorage)
    found = await storage.search_records(
        type_filter=CRED_DEF_SENT_RECORD_TYPE,
        tag_query={"cred_def_id": credential_definition_id},
    ).fetch_all()
    if not found:
        raise web.HTTPNotFound()

    try:
        revoc = IndyRevocation(context)
        registry_record = await revoc.get_active_issuer_revocation_record(credential_definition_id)
    except RevocationNotSupportedError as e:
        raise web.HTTPBadRequest() from e
    await shield(
        registry_record.generate_registry(context, RevocationRegistry.get_temp_dir())
    )
    print("generated tails file")
    # print(registry_record)
    await registry_record.publish_registry_definition(context)
    print("published registry definition")
    await registry_record.publish_registry_entry(context)
    print("published registry entry")

    return web.json_response({"result": registry_record.serialize()})


async def register(app: web.Application):
    """Register routes."""
    app.add_routes(
        [web.post("/revocation/create-registry", revocation_create_registry,)]
    )
