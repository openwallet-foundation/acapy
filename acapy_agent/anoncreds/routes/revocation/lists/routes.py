"""AnonCreds revocation list routes."""

import logging
from asyncio import shield

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema

from .....admin.decorators.auth import tenant_authentication
from .....admin.request_context import AdminRequestContext
from .....storage.error import StorageNotFoundError
from .....utils.profiles import is_not_anoncreds_profile_raise_web_exception
from ....models.revocation import RevListResultSchema
from ....revocation.revocation import AnonCredsRevocation, AnonCredsRevocationError
from ....util import handle_value_error
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
    context: AdminRequestContext = request["context"]
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    body = await request.json()
    rev_reg_def_id = body.get("rev_reg_def_id")
    options = body.get("options", {})

    try:
        revocation = AnonCredsRevocation(profile)
        result = await shield(
            revocation.create_and_register_revocation_list(
                rev_reg_def_id,
                options,
            )
        )
        LOGGER.debug("published revocation list for: %s", rev_reg_def_id)
        return web.json_response(result.serialize())
    except ValueError as e:
        handle_value_error(e)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except AnonCredsRevocationError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err


async def register(app: web.Application) -> None:
    """Register routes."""

    app.add_routes(
        [
            web.post("/anoncreds/revocation-list", rev_list_post),
        ]
    )
