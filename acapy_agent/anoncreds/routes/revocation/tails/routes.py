"""AnonCreds tails file routes."""

from aiohttp import web
from aiohttp_apispec import docs, match_info_schema, response_schema
from marshmallow import fields

from .....admin.decorators.auth import tenant_authentication
from .....admin.request_context import AdminRequestContext
from .....anoncreds.issuer import AnonCredsIssuerError
from .....anoncreds.routes.revocation import AnonCredsRevocationModuleResponseSchema
from .....messaging.models.openapi import OpenAPISchema
from .....messaging.valid import (
    ANONCREDS_REV_REG_ID_EXAMPLE,
    ANONCREDS_REV_REG_ID_VALIDATE,
)
from .....utils.profiles import is_not_anoncreds_profile_raise_web_exception
from ....revocation.revocation import AnonCredsRevocation
from ....util import handle_value_error
from .. import REVOCATION_TAG_TITLE


class AnonCredsRevRegIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking rev reg id."""

    rev_reg_id = fields.Str(
        required=True,
        validate=ANONCREDS_REV_REG_ID_VALIDATE,
        metadata={
            "description": "Revocation Registry identifier",
            "example": ANONCREDS_REV_REG_ID_EXAMPLE,
        },
    )


@docs(
    tags=[REVOCATION_TAG_TITLE],
    summary="Download tails file",
    produces=["application/octet-stream"],
)
@match_info_schema(AnonCredsRevRegIdMatchInfoSchema())
@response_schema(AnonCredsRevocationModuleResponseSchema, description="tails file")
@tenant_authentication
async def get_tails_file(request: web.BaseRequest) -> web.FileResponse:
    """Request handler to download tails file for revocation registry.

    Args:
        request: aiohttp request object

    Returns:
        The tails file in FileResponse

    """
    #
    # there is no equivalent of this in anoncreds.
    # do we need it there or is this only for transitions.
    #
    context: AdminRequestContext = request["context"]
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    rev_reg_id = request.match_info["rev_reg_id"]
    try:
        revocation = AnonCredsRevocation(profile)
        rev_reg_def = await revocation.get_created_revocation_registry_definition(
            rev_reg_id
        )
        if rev_reg_def is None:
            raise web.HTTPNotFound(reason="No rev reg def found")
    except AnonCredsIssuerError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e

    tails_local_path = rev_reg_def.value.tails_location
    return web.FileResponse(path=tails_local_path, status=200)


@docs(
    tags=[REVOCATION_TAG_TITLE],
    summary="Upload local tails file to server",
)
@match_info_schema(AnonCredsRevRegIdMatchInfoSchema())
@response_schema(AnonCredsRevocationModuleResponseSchema(), description="")
@tenant_authentication
async def upload_tails_file(request: web.BaseRequest):
    """Request handler to upload local tails file for revocation registry.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    rev_reg_id = request.match_info["rev_reg_id"]
    try:
        revocation = AnonCredsRevocation(profile)
        rev_reg_def = await revocation.get_created_revocation_registry_definition(
            rev_reg_id
        )
        if rev_reg_def is None:
            raise web.HTTPNotFound(reason="No rev reg def found")

        await revocation.upload_tails_file(rev_reg_def)
        return web.json_response({})
    except ValueError as e:
        handle_value_error(e)
    except AnonCredsIssuerError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e


async def register(app: web.Application) -> None:
    """Register routes."""

    app.add_routes(
        [
            web.put("/anoncreds/registry/{rev_reg_id}/tails-file", upload_tails_file),
            web.get(
                "/anoncreds/revocation/registry/{rev_reg_id}/tails-file",
                get_tails_file,
                allow_head=False,
            ),
        ]
    )
