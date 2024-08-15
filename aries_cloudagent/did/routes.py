"""DID Management Routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow.exceptions import ValidationError

from ..wallet.key_type import ED25519
from ..admin.decorators.auth import tenant_authentication
from ..admin.request_context import AdminRequestContext
from .web_requests import (
    DIDKeyRegistrationRequest,
    DIDKeyRegistrationResponse,
)
from .operators import DidKeyOperator, DidOperatorError

KEY_MAPPINGS = {"ed25519": ED25519}


@docs(tags=["did"], summary="Register Key DID")
@request_schema(DIDKeyRegistrationRequest())
@response_schema(DIDKeyRegistrationResponse(), 201, description="Register new DID key")
@tenant_authentication
async def register_did_key(request: web.BaseRequest):
    """Request handler for registering a Key DID.

    Args:
        request: aiohttp request object

    """
    body = await request.json()
    context: AdminRequestContext = request["context"]
    try:
        key_type = (
            body["key_type"]
            if "key_type" in body
            else context.profile.settings.get("wallet.key_type")
        )
        did_doc = await DidKeyOperator(context.profile).register_did(
            KEY_MAPPINGS[key_type]
        )
        return web.json_response({"didDocument": did_doc}, status=201)
    except (KeyError, ValidationError, DidOperatorError) as err:
        return web.json_response({"message": str(err)}, status=400)


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.post("/did/key", register_did_key),
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
