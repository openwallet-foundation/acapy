"""Revocation registry admin routes."""

from asyncio import shield

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema

import logging

from marshmallow import fields, Schema

from ..messaging.credential_definitions.util import CRED_DEF_SENT_RECORD_TYPE
from ..messaging.valid import INDY_CRED_DEF_ID, IndyRevRegId
from ..storage.base import BaseStorage, StorageNotFoundError

from .error import RevocationNotSupportedError
from .indy import IndyRevocation
from .models.issuer_rev_reg_record import IssuerRevRegRecordSchema
from .models.revocation_registry import RevocationRegistry

LOGGER = logging.getLogger(__name__)


class RevRegCreateRequestSchema(Schema):
    """Request schema for revocation registry creation request."""

    credential_definition_id = fields.Str(
        description="Credential definition identifier", **INDY_CRED_DEF_ID
    )
    issuance_by_default = fields.Boolean(
        description="Create registry with all indexes issued",
        required=False,
        default=True,
    )
    max_cred_num = fields.Int(
        description="Maximum credential numbers", example=100, required=False
    )


class RevRegCreateResultSchema(Schema):
    """Result schema for revocation registry creation request."""

    result = IssuerRevRegRecordSchema()


class RevRegUpdateTailsFileUriSchema(Schema):
    """Request schema for updating tails file URI."""

    tails_public_uri = fields.Url(
        description="Public URI to the tails file",
        example=(
            "http://192.168.56.133:5000/revocation/registry/"
            f"{IndyRevRegId.EXAMPLE}/tails-file"
        ),
        required=True,
    )


@docs(tags=["revocation"], summary="Creates a new revocation registry")
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
    max_cred_num = body.get("max_cred_num")
    issuance_by_default = body.get("issuance_by_default", True)

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
            credential_definition_id,
            issuer_did,
            issuance_by_default=issuance_by_default,
            max_cred_num=max_cred_num,
        )
    except RevocationNotSupportedError as e:
        raise web.HTTPBadRequest(reason=e.message) from e
    await shield(
        registry_record.generate_registry(context, RevocationRegistry.get_temp_dir())
    )

    return web.json_response({"result": registry_record.serialize()})


@docs(
    tags=["revocation"],
    summary="Get revocation registry by credential definition id",
    parameters=[{"in": "path", "name": "id", "description": "revocation registry id"}],
)
@response_schema(RevRegCreateResultSchema(), 200)
async def get_registry(request: web.BaseRequest):
    """
    Request handler for getting a revocation registry by identifier.

    Args:
        request: aiohttp request object

    Returns:
        The revocation registry

    """
    context = request.app["request_context"]

    registry_id = request.match_info["id"]

    try:
        revoc = IndyRevocation(context)
        revoc_registry = await revoc.get_issuer_rev_reg_record(registry_id)
    except StorageNotFoundError as e:
        raise web.HTTPNotFound() from e

    return web.json_response({"result": revoc_registry.serialize()})


@docs(
    tags=["revocation"],
    summary="Get an active revocation registry by credential definition id",
    parameters=[
        {"in": "path", "name": "cred_def_id", "description": "credential definition id"}
    ],
)
@response_schema(RevRegCreateResultSchema(), 200)
async def get_active_registry(request: web.BaseRequest):
    """
    Request handler for getting an active revocation registry by cred def id.

    Args:
        request: aiohttp request object

    Returns:
        The revocation registry identifier

    """
    context = request.app["request_context"]

    cred_def_id = request.match_info["cred_def_id"]

    try:
        revoc = IndyRevocation(context)
        revoc_registry = await revoc.get_active_issuer_rev_reg_record(cred_def_id)
    except StorageNotFoundError as e:
        raise web.HTTPNotFound() from e

    return web.json_response({"result": revoc_registry.serialize()})


@docs(
    tags=["revocation"],
    summary="Download the tails file of revocation registry",
    produces="application/octet-stream",
    parameters=[{"in": "path", "name": "id", "description": "revocation registry id"}],
    responses={200: {"description": "tails file", "schema": {"type": "file"}}},
)
async def get_tails_file(request: web.BaseRequest) -> web.FileResponse:
    """
    Request handler for downloading the tails file of the revocation registry.

    Args:
        request: aiohttp request object

    Returns:
        The tails file in FileResponse

    """
    context = request.app["request_context"]

    registry_id = request.match_info["id"]

    try:
        revoc = IndyRevocation(context)
        revoc_registry = await revoc.get_issuer_rev_reg_record(registry_id)
    except StorageNotFoundError as e:
        raise web.HTTPNotFound() from e

    return web.FileResponse(path=revoc_registry.tails_local_path, status=200)


@docs(
    tags=["revocation"],
    summary="Publish a given revocation registry",
    parameters=[{"in": "path", "name": "id", "description": "revocation registry id"}],
)
@response_schema(RevRegCreateResultSchema(), 200)
async def publish_registry(request: web.BaseRequest):
    """
    Request handler for publishing a revocation registry based on the registry id.

    Args:
        request: aiohttp request object

    Returns:
        The revocation registry record

    """
    context = request.app["request_context"]
    registry_id = request.match_info["id"]

    try:
        revoc = IndyRevocation(context)
        revoc_registry = await revoc.get_issuer_rev_reg_record(registry_id)
    except StorageNotFoundError as e:
        raise web.HTTPNotFound() from e

    await revoc_registry.publish_registry_definition(context)
    LOGGER.debug("published registry definition: %s", registry_id)
    await revoc_registry.publish_registry_entry(context)
    LOGGER.debug("published registry entry: %s", registry_id)

    return web.json_response({"result": revoc_registry.serialize()})


@docs(
    tags=["revocation"],
    summary="Update revocation registry with new public URI to the tails file.",
    parameters=[
        {"in": "path", "name": "id", "description": "revocation registry identifier",}
    ],
)
@request_schema(RevRegUpdateTailsFileUriSchema())
@response_schema(RevRegCreateResultSchema(), 200)
async def update_registry(request: web.BaseRequest):
    """
    Request handler for updating a revocation registry based on the registry id.

    Args:
        request: aiohttp request object

    Returns:
        The revocation registry record

    """
    context = request.app["request_context"]

    body = await request.json()
    tails_public_uri = body.get("tails_public_uri")

    registry_id = request.match_info["id"]

    try:
        revoc = IndyRevocation(context)
        revoc_registry = await revoc.get_issuer_rev_reg_record(registry_id)
    except StorageNotFoundError as e:
        raise web.HTTPNotFound() from e

    await revoc_registry.set_tails_file_public_uri(context, tails_public_uri)

    return web.json_response({"result": revoc_registry.serialize()})


async def register(app: web.Application):
    """Register routes."""
    app.add_routes(
        [
            web.post("/revocation/create-registry", revocation_create_registry),
            web.get("/revocation/registry/{id}", get_registry),
            web.get("/revocation/active-registry/{cred_def_id}", get_active_registry),
            web.get("/revocation/registry/{id}/tails-file", get_tails_file),
            web.patch("/revocation/registry/{id}", update_registry),
            web.post("/revocation/registry/{id}/publish", publish_registry),
        ]
    )
