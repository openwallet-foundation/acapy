"""Key admin routes."""

import logging

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, request_schema, response_schema
from marshmallow import fields, validate

from ...admin.decorators.auth import tenant_authentication
from ...admin.request_context import AdminRequestContext
from ...messaging.models.openapi import OpenAPISchema
from .manager import MultikeyManager, MultikeyManagerError
from ...wallet.error import WalletError, WalletDuplicateError, WalletNotFoundError

LOGGER = logging.getLogger(__name__)


class CreateKeyRequestSchema(OpenAPISchema):
    """Request schema for creating a new key."""

    seed = fields.Str(
        required=False,
        metadata={
            "description": "Optional seed to generate the key pair",
            "example": "00000000000000000000000000000000",
        },
    )

    verification_method = fields.Str(
        data_key="verificationMethod",
        required=False,
        metadata={
            "description": "Optional kid to bind to the keypair",
            "example": "did:web:example.com#key-01",
        },
    )


class CreateKeyResponseSchema(OpenAPISchema):
    """Response schema from creating a new key."""

    multikey = fields.Str(
        metadata={
            "description": "The Public Key Multibase format (multikey)",
            "example": "",
        },
    )


class UpdateKeyRequestSchema(OpenAPISchema):
    """Request schema for updating an existing key pair."""

    multikey = fields.Str(
        required=True,
        metadata={
            "description": "Multikey of the key pair to update",
            "example": "",
        },
    )

    verification_method = fields.Str(
        data_key="verificationMethod",
        required=True,
        metadata={
            "description": "New kid to bind to the key pair",
            "example": "did:web:example.com#key-02",
        },
    )


class UpdateKeyResponseSchema(OpenAPISchema):
    """Response schema from updating an existing key pair."""

    multikey = fields.Str(
        metadata={
            "description": "The Public Key Multibase format (multikey)",
            "example": "",
        },
    )


class FetchKeyResponseSchema(OpenAPISchema):
    """Response schema from updating an existing key pair."""

    multikey = fields.Str(
        metadata={
            "description": "The Public Key Multibase format (multikey)",
            "example": "",
        },
    )


@docs(tags=["wallet"], summary="Fetch key info.")
@response_schema(FetchKeyResponseSchema, 200, description="")
@tenant_authentication
async def fetch_key(request: web.BaseRequest):
    """Request handler for fetching a key.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    try:
        multikey = request.match_info["multikey"]
        key_info = await MultikeyManager(context.profile).fetch(
            multikey=multikey,
        )
        print(key_info)
        return web.json_response(
            {},
            status=200,
        )
    except (MultikeyManagerError, WalletDuplicateError, WalletNotFoundError) as err:
        return web.json_response({"message": str(err)}, status=400)


@docs(tags=["wallet"], summary="Create a key pair")
@request_schema(CreateKeyRequestSchema())
@response_schema(CreateKeyResponseSchema, 200, description="")
@tenant_authentication
async def create_key(request: web.BaseRequest):
    """Request handler for creating a new key pair in the wallet.

    Args:
        request: aiohttp request object

    Returns:
        The Public Key Multibase format (multikey)

    """
    context: AdminRequestContext = request["context"]
    try:
        seed = request["data"]["seed"] if "seed" in request["data"] else None
        kid = (
            request["data"]["verification_method"]
            if "verification_method" in request["data"]
            else None
        )
        multikey = await MultikeyManager(context.profile).create(
            seed=seed,
            kid=kid,
        )
        return web.json_response(
            {"multikey": multikey},
            status=201,
        )
    except (MultikeyManagerError, WalletDuplicateError, WalletNotFoundError) as err:
        return web.json_response({"message": str(err)}, status=400)


@docs(tags=["wallet"], summary="Update a key pair's kid")
@request_schema(UpdateKeyRequestSchema())
@response_schema(UpdateKeyResponseSchema, 200, description="")
@tenant_authentication
async def update_key(request: web.BaseRequest):
    """Request handler for creating a new key pair in the wallet.

    Args:
        request: aiohttp request object

    Returns:
        The Public Key Multibase format (multikey)

    """
    context: AdminRequestContext = request["context"]
    try:
        multikey = request["data"]["multikey"]
        kid = request["data"]["verification_method"]
        await MultikeyManager(context.profile).update(
            multikey=multikey,
            kid=kid,
        )
        return web.json_response(
            {},
            status=200,
        )
    except (MultikeyManagerError, WalletDuplicateError, WalletNotFoundError) as err:
        return web.json_response({"message": str(err)}, status=400)


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/wallet/keys/{multikey}", fetch_key, allow_head=False),
            web.post("/wallet/keys", create_key),
            web.put("/wallet/keys", update_key),
        ]
    )
