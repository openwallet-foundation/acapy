"""DID Management Routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow.exceptions import ValidationError

from ..wallet.key_type import ED25519
from ..admin.decorators.auth import tenant_authentication
from .web_requests import (
    DIDKeyRegistrationRequest,
    DIDKeyRegistrationResponse,
    DIDKeyBindingRequest,
    DIDKeyBindingResponse,
)
from . import DIDKey, DidOperationError

KEY_MAPPINGS = {"ed25519": ED25519}


@docs(tags=["did"], summary="Create DID Key")
@request_schema(DIDKeyRegistrationRequest())
@response_schema(DIDKeyRegistrationResponse(), 201, description="Create new DID key")
@tenant_authentication
async def create_did_key(request):
    """Request handler for registering a Key DID.

    Args:
        request: aiohttp request object

    """
    try:
        return web.json_response(
            await DIDKey().create(
                profile=request["context"].profile,
                key_type=KEY_MAPPINGS[
                    request["data"]["type"] if "type" in request["data"] else "ed25519"
                ],
                kid=request["data"]["kid"] if "kid" in request["data"] else None,
                seed=request["data"]["seed"] if "seed" in request["data"] else None,
            ),
            status=201,
        )
    except (KeyError, ValidationError, DidOperationError) as err:
        return web.json_response({"message": str(err)}, status=400)


@docs(tags=["did"], summary="Bind DID Key")
@request_schema(DIDKeyBindingRequest())
@response_schema(
    DIDKeyBindingResponse(), 201, description="Bind existing DID key to new KID"
)
@tenant_authentication
async def bind_did_key(request):
    """Request handler for binding a Key DID.

    Args:
        request: aiohttp request object

    """
    try:
        return web.json_response(
            await DIDKey().bind(
                profile=request["context"].profile,
                did=request["data"]["did"],
                kid=request["data"]["kid"],
            ),
            status=200,
        )
    except (KeyError, ValidationError, DidOperationError) as err:
        return web.json_response({"message": str(err)}, status=400)


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.post("/did/key/create", create_did_key),
            web.post("/did/key/bind", bind_did_key),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""
    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "did",
            "description": "Endpoints for managing dids",
            "externalDocs": {
                "description": "Specification",
                "url": "https://www.w3.org/TR/did-core/",
            },
        }
    )
