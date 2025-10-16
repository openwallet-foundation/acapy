"""AnonCreds revocation list routes."""

import logging
from asyncio import shield

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema

from .....admin.decorators.auth import tenant_authentication
from ....models.revocation import RevListResultSchema
from ....revocation.revocation import AnonCredsRevocation
from ...common.utils import get_request_body_with_profile_check
from .. import REVOCATION_TAG_TITLE
from .models import RevListCreateRequestSchema

LOGGER = logging.getLogger(__name__)


@docs(
    tags=[REVOCATION_TAG_TITLE],
    summary="Create and publish a revocation status list on the connected datastore",
)
@request_schema(RevListCreateRequestSchema())
@response_schema(RevListResultSchema(), 200, description="")
@tenant_authentication
async def rev_list_post(request: web.BaseRequest):
    """Request handler for creating registering a revocation list."""
    _, profile, body, options = await get_request_body_with_profile_check(request)

    rev_reg_def_id = body["rev_reg_def_id"]  # required in request schema

    revocation = AnonCredsRevocation(profile)
    result = await shield(
        revocation.create_and_register_revocation_list(rev_reg_def_id, options=options)
    )
    if isinstance(result, str):  # if it's a string, it's an error message
        raise web.HTTPBadRequest(reason=result)

    LOGGER.debug("published revocation list for: %s", rev_reg_def_id)
    return web.json_response(result.serialize())


async def register(app: web.Application) -> None:
    """Register routes."""
    app.add_routes(
        [
            web.post("/anoncreds/revocation-list", rev_list_post),
        ]
    )
