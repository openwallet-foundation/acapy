"""
Resolve did document admin routes.

"/resolver/resolve/{did}": {
    "get": {
        "responses": {
            "200": {
                "schema": {
                    "$ref": "#/definitions/DIDDoc"
                },
                "description": null
            }
        },
        "parameters": [
            {
                "in": "path",
                "name": "did",
                "required": true,
                "type": "string",
                "pattern": "did:([a-z]+):((?:[a-zA-Z0-9._-]*:)*[a-zA-Z0-9._-]+)",
                "description": "decentralize identifier(DID)",
                "example": "did:ted:WgWxqztrNooG92RXvxSTWv"
            }
        ],
        "tags": [ "resolver" ],
        "summary": "Retrieve doc for requested did",
        "produces": [ "application/json" ]
    }
}
"""

from aiohttp import web
from aiohttp_apispec import docs, match_info_schema, response_schema
from marshmallow import fields, validate

from ..admin.request_context import AdminRequestContext
from ..messaging.models.openapi import OpenAPISchema
from .base import DIDMethodNotSupported, DIDNotFound, ResolverError
from .did import DID_PATTERN
from .did_resolver import DIDResolver


class W3cDIDDoc(validate.Regexp):
    """Validate value against w3c DID document."""

    EXAMPLE = "*"
    PATTERN = DID_PATTERN

    def __init__(self):
        """Initializer."""

        super().__init__(
            W3cDIDDoc.PATTERN,
            error="Value {input} is not a w3c decentralized identifier (DID) doc.",
        )


_W3cDIDDoc = {"validate": W3cDIDDoc(), "example": W3cDIDDoc.EXAMPLE}


class DIDDocSchema(OpenAPISchema):
    """Result schema for did document query."""

    did_doc = fields.Str(
        description="decentralize identifier(DID) document", required=True, **_W3cDIDDoc
    )


class W3cDID(validate.Regexp):
    """Validate value against w3c DID."""

    EXAMPLE = "did:ted:WgWxqztrNooG92RXvxSTWv"
    PATTERN = DID_PATTERN

    def __init__(self):
        """Initializer."""

        super().__init__(
            W3cDID.PATTERN,
            error="Value {input} is not a w3c decentralized identifier (DID)",
        )


_W3cDID = {"validate": W3cDID(), "example": W3cDID.EXAMPLE}


class DIDMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking DID."""

    did = fields.Str(
        description="decentralize identifier(DID)", required=True, **_W3cDID
    )


@docs(tags=["resolver"], summary="Retrieve doc for requested did")
@match_info_schema(DIDMatchInfoSchema())
@response_schema(DIDDocSchema(), 200)
async def resolve_did(request: web.BaseRequest):
    """Retrieve a did document."""
    context: AdminRequestContext = request["context"]

    did = request.match_info["did"]
    try:
        session = await context.session()
        resolver = session.inject(DIDResolver)
        document = await resolver.resolve(context.profile, did)
        result = document.serialize()
    except DIDNotFound as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except DIDMethodNotSupported as err:
        raise web.HTTPNotImplemented(reason=err.roll_up) from err
    except ResolverError as err:
        raise web.HTTPInternalServerError(reason=err.roll_up) from err
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
            "description": "did resolver interface.",
            "externalDocs": {"description": "Specification"},  # , "url": SPEC_URI},
        }
    )
