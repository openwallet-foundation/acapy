"""resolve did document admin routes."""


from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)
from marshmallow import fields, validate

from ....admin.request_context import AdminRequestContext
from ....messaging.models.base import BaseModelError
from ....messaging.models.openapi import OpenAPISchema
from ....storage.error import StorageError, StorageNotFoundError
from .did_resolver import Resolver
from ..messaging.valid import UUIDFour


class DIDDocSchema(OpenAPISchema):
    """Result schema for did document query."""

    pass


class DIDMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking DID."""

    did = fields.Str(
        description="decentralize identifier(DID)",
        required=True,
        example=UUIDFour.EXAMPLE,
    )


@docs(tags=["resolver"], summary="Retrieve doc for requested did")
@match_info_schema(DIDMatchInfoSchema())
#  @response_schema(DIDDocSchema(), 200)
async def resolve_did(request: web.BaseRequest):
    """Retrieve a did document."""
    context: AdminRequestContext = request["context"]

    did = request.match_info["did"]
    try:
        session = await context.session()
        resolver = session.inject(Resolver)
        document = await resolver.resolve(did)
        result = document.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (BaseModelError, StorageError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(result)


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get(
                "/resolver/resolve/{did}",
                resolve_did,
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
            "name": "resolver",
            "description": "universal resolvers",
            "externalDocs": {"description": "Specification"},  # , "url": SPEC_URI},
        }
    )
