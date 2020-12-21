"""Multitenant admin routes."""

from marshmallow import fields, validate, validates_schema, ValidationError
from aiohttp import web
from aiohttp_apispec import docs, request_schema, match_info_schema, response_schema

from ...admin.request_context import AdminRequestContext
from ...messaging.valid import JSONWebToken, UUIDFour
from ...messaging.models.openapi import OpenAPISchema
from ...storage.error import StorageNotFoundError
from ...wallet.models.wallet_record import WalletRecord, WalletRecordSchema
from ...core.error import BaseError
from ...core.profile import ProfileManagerProvider
from ..manager import MultitenantManager
from ..error import WalletKeyMissingError


def format_wallet_record(wallet_record: WalletRecord):
    """Serialize a WalletRecord object."""

    wallet_info = wallet_record.serialize()

    # Hide wallet wallet key
    if "wallet.key" in wallet_info["settings"]:
        del wallet_info["settings"]["wallet.key"]

    return wallet_info


class MultitenantModuleResponseSchema(OpenAPISchema):
    """Response schema for multitenant module."""


class WalletIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking wallet id."""

    wallet_id = fields.Str(
        description="Subwallet identifier", required=True, example=UUIDFour.EXAMPLE
    )


class CreateWalletRequestSchema(OpenAPISchema):
    """Request schema for adding a new wallet which will be registered by the agent."""

    wallet_name = fields.Str(description="Wallet name", example="MyNewWallet")

    wallet_key = fields.Str(
        description="Master key used for key derivation.", example="MySecretKey123"
    )

    wallet_type = fields.Str(
        description="Type of the wallet to create",
        example="indy",
        default="in_memory",
        validate=validate.OneOf(
            [wallet_type for wallet_type in ProfileManagerProvider.MANAGER_TYPES]
        ),
    )

    label = fields.Str(
        description="Label for this wallet. This label is publicized\
            (self-attested) to other agents as part of forming a connection.",
        example="Alice",
    )

    key_management_mode = fields.Str(
        description="Key management method to use for this wallet.",
        example=WalletRecord.MODE_MANAGED,
        default=WalletRecord.MODE_MANAGED,
        validate=validate.OneOf(
            (WalletRecord.MODE_MANAGED, WalletRecord.MODE_UNMANAGED)
        ),
    )

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """
        Validate schema fields.

        Args:
            data: The data to validate

        Raises:
            ValidationError: If any of the fields do not validate

        """

        if data.get("wallet_type") == "indy":
            for field in ("wallet_key", "wallet_name"):
                if field not in data:
                    raise ValidationError("Missing required field", field)


class CreateWalletResponseSchema(WalletRecordSchema):
    """Response schema for creating a wallet."""

    token = fields.Str(
        description="Authorization token to authenticate wallet requests",
        example=JSONWebToken.EXAMPLE,
    )


class RemoveWalletRequestSchema(OpenAPISchema):
    """Request schema for removing a wallet."""

    wallet_key = fields.Str(
        description="Master key used for key derivation. Only required for \
            unmanaged wallets.",
        example="MySecretKey123",
    )


class CreateWalletTokenRequestSchema(OpenAPISchema):
    """Request schema for creating a wallet token."""

    wallet_key = fields.Str(
        description="Master key used for key derivation. Only required for \
            unamanged wallets.",
        example="MySecretKey123",
    )


class CreateWalletTokenResponseSchema(OpenAPISchema):
    """Response schema for creating a wallet token."""

    token = fields.Str(
        description="Authorization token to authenticate wallet requests",
        example=JSONWebToken.EXAMPLE,
    )


class WalletListSchema(OpenAPISchema):
    """Result schema for wallet list."""

    results = fields.List(
        fields.Nested(WalletRecordSchema()),
        description="List of wallet records",
    )


@docs(tags=["multitenancy"], summary="List all subwallets")
@response_schema(WalletListSchema(), 200, description="")
async def wallet_list(request: web.BaseRequest):
    """
    Request handler for listing all internal subwallets.

    Args:
        request: aiohttp request object
    """

    context: AdminRequestContext = request["context"]

    async with context.session() as session:
        try:
            records = await WalletRecord.query(session)
            results = [format_wallet_record(record) for record in records]
        except StorageNotFoundError:
            raise web.HTTPNotFound()

    return web.json_response({"results": results})


@docs(tags=["multitenancy"], summary="Get a single subwallet")
@match_info_schema(WalletIdMatchInfoSchema())
@response_schema(WalletRecordSchema(), 200, description="")
async def wallet_get(request: web.BaseRequest):
    """
    Request handler for getting a single subwallet.

    Args:
        request: aiohttp request object

    Raises:
        HTTPNotFound: if wallet_id does not match any known wallets

    """

    context: AdminRequestContext = request["context"]
    wallet_id = request.match_info["wallet_id"]

    async with context.session() as session:
        try:
            wallet_record = await WalletRecord.retrieve_by_id(session, wallet_id)
            result = format_wallet_record(wallet_record)
        except StorageNotFoundError:
            raise web.HTTPNotFound()

    return web.json_response(result)


@docs(tags=["multitenancy"], summary="Create a subwallet")
@request_schema(CreateWalletRequestSchema)
@response_schema(CreateWalletResponseSchema(), 200, description="")
async def wallet_create(request: web.BaseRequest):
    """
    Request handler for adding a new subwallet for handling by the agent.

    Args:
        request: aiohttp request object
    """

    context: AdminRequestContext = request["context"]
    body = await request.json()

    key_management_mode = body.get("key_management_mode") or WalletRecord.MODE_MANAGED
    wallet_key = body.get("wallet_key")

    settings = {
        "wallet.type": body.get("wallet_type") or "in_memory",
        "wallet.name": body.get("wallet_name"),
        "wallet.key": wallet_key,
    }

    label = body.get("label")
    if label:
        settings["default_label"] = label

    async with context.session() as session:
        try:
            multitenant_mgr = session.inject(MultitenantManager)

            wallet_record = await multitenant_mgr.create_wallet(
                settings, key_management_mode
            )

            token = await multitenant_mgr.create_auth_token(wallet_record, wallet_key)
        except BaseError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    result = {
        **format_wallet_record(wallet_record),
        "token": token,
    }
    return web.json_response(result)


@docs(tags=["multitenancy"], summary="Get auth token for a subwallet")
@request_schema(CreateWalletTokenRequestSchema)
@response_schema(CreateWalletTokenResponseSchema(), 200, description="")
async def wallet_create_token(request: web.BaseRequest):
    """
    Request handler for creating an authorization token for a specific subwallet.

    Args:
        request: aiohttp request object
    """

    context: AdminRequestContext = request["context"]
    wallet_id = request.match_info["wallet_id"]
    wallet_key = None

    if request.has_body:
        body = await request.json()
        wallet_key = body.get("wallet_key")

    async with context.session() as session:
        try:
            multitenant_mgr = session.inject(MultitenantManager)
            wallet_record = await WalletRecord.retrieve_by_id(session, wallet_id)

            token = await multitenant_mgr.create_auth_token(wallet_record, wallet_key)
        except StorageNotFoundError:
            raise web.HTTPNotFound()
        except WalletKeyMissingError as e:
            raise web.HTTPUnauthorized(e.roll_up) from e

    return web.json_response({"token": token})


@docs(
    tags=["multitenancy"],
    summary="Remove a subwallet",
)
@match_info_schema(WalletIdMatchInfoSchema())
@request_schema(RemoveWalletRequestSchema)
@response_schema(MultitenantModuleResponseSchema(), 200, description="")
async def wallet_remove(request: web.BaseRequest):
    """
    Request handler to remove a subwallet from agent and storage.

    Args:
        request: aiohttp request object.

    """

    context: AdminRequestContext = request["context"]
    wallet_id = request.match_info["wallet_id"]
    wallet_key = None

    if request.has_body:
        body = await request.json()
        wallet_key = body.get("wallet_key")

    async with context.session() as session:
        try:
            multitenant_mgr = session.inject(MultitenantManager)
            await multitenant_mgr.remove_wallet(wallet_id, wallet_key)
        except StorageNotFoundError:
            raise web.HTTPNotFound()
        except WalletKeyMissingError as e:
            raise web.HTTPUnauthorized(e.message)

    return web.json_response({})


# MTODO: add wallet import route
# MTODO: add wallet export route
# MTODO: add rotate wallet key route


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/multitenancy/wallets", wallet_list, allow_head=False),
            web.post("/multitenancy/wallet", wallet_create),
            web.get("/multitenancy/wallet/{wallet_id}", wallet_get, allow_head=False),
            web.post("/multitenancy/wallet/{wallet_id}/token", wallet_create_token),
            web.post("/multitenancy/wallet/{wallet_id}/remove", wallet_remove),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {"name": "multitenancy", "description": "Multitenant wallet management"}
    )
