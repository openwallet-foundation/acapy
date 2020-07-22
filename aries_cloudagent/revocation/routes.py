"""Revocation registry admin routes."""

import logging

from asyncio import shield

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)

from marshmallow import fields, Schema, validate

from ..messaging.credential_definitions.util import CRED_DEF_SENT_RECORD_TYPE
from ..messaging.valid import INDY_CRED_DEF_ID, INDY_REV_REG_ID
from ..storage.base import BaseStorage, StorageNotFoundError

from .error import RevocationError, RevocationNotSupportedError
from .indy import IndyRevocation
from .models.issuer_rev_reg_record import IssuerRevRegRecord, IssuerRevRegRecordSchema


LOGGER = logging.getLogger(__name__)


class RevRegCreateRequestSchema(Schema):
    """Request schema for revocation registry creation request."""

    credential_definition_id = fields.Str(
        description="Credential definition identifier", **INDY_CRED_DEF_ID
    )
    max_cred_num = fields.Int(
        description="Maximum credential numbers", example=100, required=False
    )


class RevRegCreateResultSchema(Schema):
    """Result schema for revocation registry creation request."""

    result = IssuerRevRegRecordSchema()


class RevRegsCreatedSchema(Schema):
    """Result schema for request for revocation registries created."""

    rev_reg_ids = fields.List(
        fields.Str(description="Revocation Registry identifiers", **INDY_REV_REG_ID)
    )


class RevRegUpdateTailsFileUriSchema(Schema):
    """Request schema for updating tails file URI."""

    tails_public_uri = fields.Url(
        description="Public URI to the tails file",
        example=(
            "http://192.168.56.133:5000/revocation/registry/"
            f"{INDY_REV_REG_ID['example']}/tails-file"
        ),
        required=True,
    )


class RevRegsCreatedQueryStringSchema(Schema):
    """Query string parameters and validators for rev regs created request."""

    cred_def_id = fields.Str(
        description="Credential definition identifier",
        required=False,
        **INDY_CRED_DEF_ID,
    )
    state = fields.Str(
        description="Revocation registry state",
        required=False,
        validate=validate.OneOf(
            [
                getattr(IssuerRevRegRecord, m)
                for m in vars(IssuerRevRegRecord)
                if m.startswith("STATE_")
            ]
        ),
    )


class RevRegIdMatchInfoSchema(Schema):
    """Path parameters and validators for request taking rev reg id."""

    rev_reg_id = fields.Str(
        description="Revocation Registry identifier", required=True, **INDY_REV_REG_ID,
    )


class CredDefIdMatchInfoSchema(Schema):
    """Path parameters and validators for request taking cred def id."""

    cred_def_id = fields.Str(
        description="Credential definition identifier",
        required=True,
        **INDY_CRED_DEF_ID,
    )


@docs(tags=["revocation"], summary="Creates a new revocation registry")
@request_schema(RevRegCreateRequestSchema())
@response_schema(RevRegCreateResultSchema(), 200)
async def revocation_create_registry(request: web.BaseRequest):
    """
    Request handler to create a new revocation registry.

    Args:
        request: aiohttp request object

    Returns:
        The issuer revocation registry record

    """
    context = request.app["request_context"]

    body = await request.json()

    credential_definition_id = body.get("credential_definition_id")
    max_cred_num = body.get("max_cred_num")

    # check we published this cred def
    storage = await context.inject(BaseStorage)

    found = await storage.search_records(
        type_filter=CRED_DEF_SENT_RECORD_TYPE,
        tag_query={"cred_def_id": credential_definition_id},
    ).fetch_all()
    if not found:
        raise web.HTTPNotFound(
            reason=f"Not issuer of credential definition id {credential_definition_id}"
        )

    try:
        issuer_did = credential_definition_id.split(":")[0]
        revoc = IndyRevocation(context)
        registry_record = await revoc.init_issuer_registry(
            credential_definition_id, issuer_did, max_cred_num=max_cred_num,
        )
    except RevocationNotSupportedError as e:
        raise web.HTTPBadRequest(reason=e.message) from e
    await shield(registry_record.generate_registry(context))

    return web.json_response({"result": registry_record.serialize()})


@docs(
    tags=["revocation"],
    summary="Search for matching revocation registries that current agent created",
)
@querystring_schema(RevRegsCreatedQueryStringSchema())
@response_schema(RevRegsCreatedSchema(), 200)
async def revocation_registries_created(request: web.BaseRequest):
    """
    Request handler to get revocation registries that current agent created.

    Args:
        request: aiohttp request object

    Returns:
        List of identifiers of matching revocation registries.

    """
    context = request.app["request_context"]

    search_tags = [
        tag for tag in vars(RevRegsCreatedQueryStringSchema)["_declared_fields"]
    ]
    tag_filter = {
        tag: request.query[tag] for tag in search_tags if tag in request.query
    }
    found = await IssuerRevRegRecord.query(context, tag_filter)

    return web.json_response({"rev_reg_ids": [record.revoc_reg_id for record in found]})


@docs(
    tags=["revocation"], summary="Get revocation registry by revocation registry id",
)
@match_info_schema(RevRegIdMatchInfoSchema())
@response_schema(RevRegCreateResultSchema(), 200)
async def get_registry(request: web.BaseRequest):
    """
    Request handler to get a revocation registry by identifier.

    Args:
        request: aiohttp request object

    Returns:
        The revocation registry

    """
    context = request.app["request_context"]

    registry_id = request.match_info["rev_reg_id"]

    try:
        revoc = IndyRevocation(context)
        revoc_registry = await revoc.get_issuer_rev_reg_record(registry_id)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    return web.json_response({"result": revoc_registry.serialize()})


@docs(
    tags=["revocation"],
    summary="Get an active revocation registry by credential definition id",
)
@match_info_schema(CredDefIdMatchInfoSchema())
@response_schema(RevRegCreateResultSchema(), 200)
async def get_active_registry(request: web.BaseRequest):
    """
    Request handler to get an active revocation registry by cred def id.

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
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    return web.json_response({"result": revoc_registry.serialize()})


@docs(
    tags=["revocation"],
    summary="Download the tails file of revocation registry",
    produces="application/octet-stream",
    responses={200: {"description": "tails file"}},
)
@match_info_schema(RevRegIdMatchInfoSchema())
async def get_tails_file(request: web.BaseRequest) -> web.FileResponse:
    """
    Request handler to download the tails file of the revocation registry.

    Args:
        request: aiohttp request object

    Returns:
        The tails file in FileResponse

    """
    context = request.app["request_context"]

    registry_id = request.match_info["rev_reg_id"]

    try:
        revoc = IndyRevocation(context)
        revoc_registry = await revoc.get_issuer_rev_reg_record(registry_id)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    return web.FileResponse(path=revoc_registry.tails_local_path, status=200)


@docs(
    tags=["revocation"], summary="Publish a given revocation registry",
)
@match_info_schema(RevRegIdMatchInfoSchema())
@response_schema(RevRegCreateResultSchema(), 200)
async def publish_registry(request: web.BaseRequest):
    """
    Request handler to publish a revocation registry based on the registry id.

    Args:
        request: aiohttp request object

    Returns:
        The revocation registry record

    """
    context = request.app["request_context"]
    registry_id = request.match_info["rev_reg_id"]

    try:
        revoc = IndyRevocation(context)
        revoc_registry = await revoc.get_issuer_rev_reg_record(registry_id)

        await revoc_registry.publish_registry_definition(context)
        LOGGER.debug("published registry definition: %s", registry_id)

        await revoc_registry.publish_registry_entry(context)
        LOGGER.debug("published registry entry: %s", registry_id)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except RevocationError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"result": revoc_registry.serialize()})


@docs(
    tags=["revocation"],
    summary="Update revocation registry with new public URI to the tails file.",
)
@match_info_schema(RevRegIdMatchInfoSchema())
@request_schema(RevRegUpdateTailsFileUriSchema())
@response_schema(RevRegCreateResultSchema(), 200)
async def update_registry(request: web.BaseRequest):
    """
    Request handler to update a revocation registry based on the registry id.

    Args:
        request: aiohttp request object

    Returns:
        The revocation registry record

    """
    context = request.app["request_context"]

    body = await request.json()
    tails_public_uri = body.get("tails_public_uri")

    registry_id = request.match_info["rev_reg_id"]

    try:
        revoc = IndyRevocation(context)
        revoc_registry = await revoc.get_issuer_rev_reg_record(registry_id)
        await revoc_registry.set_tails_file_public_uri(context, tails_public_uri)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except RevocationError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"result": revoc_registry.serialize()})


async def register(app: web.Application):
    """Register routes."""
    app.add_routes(
        [
            web.post("/revocation/create-registry", revocation_create_registry),
            web.get(
                "/revocation/registries/created",
                revocation_registries_created,
                allow_head=False,
            ),
            web.get(
                "/revocation/registry/{rev_reg_id}", get_registry, allow_head=False
            ),
            web.get(
                "/revocation/active-registry/{cred_def_id}",
                get_active_registry,
                allow_head=False,
            ),
            web.get(
                "/revocation/registry/{rev_reg_id}/tails-file",
                get_tails_file,
                allow_head=False,
            ),
            web.patch("/revocation/registry/{rev_reg_id}", update_registry),
            web.post("/revocation/registry/{rev_reg_id}/publish", publish_registry),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "revocation",
            "description": "Revocation registry management",
            "externalDocs": {
                "description": "Overview",
                "url": (
                    "https://github.com/hyperledger/indy-hipe/tree/"
                    "master/text/0011-cred-revocation"
                ),
            },
        }
    )

    # aio_http-apispec polite API only works on schema for JSON objects, not files yet
    methods = app._state["swagger_dict"]["paths"].get(
        "/revocation/registry/{rev_reg_id}/tails-file"
    )
    if methods:
        methods["get"]["responses"]["200"]["schema"] = {
            "type": "string",
            "format": "binary",
        }
