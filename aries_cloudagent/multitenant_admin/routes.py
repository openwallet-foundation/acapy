"""Multitenant admin routes."""

from typing import cast
from marshmallow import fields, Schema, validate, validates_schema, ValidationError
from aiohttp import web
from aiohttp_apispec import docs, request_schema, match_info_schema

from .util import get_wallet_jwt
from ..messaging.valid import UUIDFour
from ..messaging.models.openapi import OpenAPISchema
from ..storage.error import StorageNotFoundError
from ..wallet.provider import WalletProvider
from ..wallet.indy import IndyWallet
from ..wallet.models.wallet_record import WalletRecord


def format_wallet_record(wallet_record: WalletRecord):
    """Serialize a WalletRecord object."""

    wallet_info = {
        "wallet_id": wallet_record.wallet_record_id,
        "wallet_type": wallet_record.wallet_config.get("type"),
        "wallet_name": wallet_record.wallet_name,
        "created_at": wallet_record.created_at,
        "updated_at": wallet_record.updated_at,
    }

    return wallet_info


class WalletIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking wallet id."""

    wallet_id = fields.Str(
        description="Subwallet identifier", required=True, example=UUIDFour.EXAMPLE
    )


class CreateWalletRequestSchema(Schema):
    """Request schema for adding a new wallet which will be registered by the agent."""

    # MTODO: wallet_name is now also required for 'basic' wallet
    # to make the CachedProvider setup easier. Should we make it optional?
    wallet_name = fields.Str(
        description="Wallet name", example="MyNewWallet", required=True
    )

    wallet_key = fields.Str(
        description="Master key used for key derivation.", example="MySecretKey123"
    )

    # MTODO: SEED
    # seed = fields.Str(
    #     description="Seed used for did derivation - 32 bytes.",
    #     example="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    # )

    wallet_type = fields.Str(
        description="Type of the wallet to create",
        example="indy",
        default="basic",
        validate=validate.OneOf(
            [wallet_type for wallet_type in WalletProvider.WALLET_TYPES]
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
            if "wallet_key" not in data:
                raise ValidationError("Missing required field", "wallet_key")


@docs(tags=["multitenancy"], summary="List all subwallets")
# MTODO: response schema
async def wallet_list(request: web.BaseRequest):
    """
    Request handler for listing all internal subwallets.

    Args:
        request: aiohttp request object
    """

    context = request.app["request_context"]

    try:
        records = await WalletRecord.query(context)
        results = [format_wallet_record(record) for record in records]
    except StorageNotFoundError:
        raise web.HTTPNotFound()
    return web.json_response({"results": results})


@docs(tags=["multitenancy"], summary="Get a single subwallet")
@match_info_schema(WalletIdMatchInfoSchema())
# TODO: response schema
async def wallet_get(request: web.BaseRequest):
    """
    Request handler for getting a single subwallet.

    Args:
        request: aiohttp request object

    Raises:
        HTTPNotFound: if wallet_id does not match any known wallets

    """

    context = request.app["request_context"]
    wallet_id = request.match_info["wallet_id"]

    try:
        wallet_record = await WalletRecord.retrieve_by_id(context, wallet_id)
        result = format_wallet_record(wallet_record)
    except StorageNotFoundError:
        raise web.HTTPNotFound()
    return web.json_response(result)


@docs(tags=["multitenancy"], summary="Create a subwallet")
@request_schema(CreateWalletRequestSchema)
# MTODO: Response schema
async def wallet_create(request: web.BaseRequest):
    """
    Request handler for adding a new subwallet for handling by the agent.

    Args:
        request: aiohttp request object
    """

    context = request.app["request_context"]
    body = await request.json()

    wallet_name = body.get("wallet_name")
    wallet_key = body.get("wallet_key")
    wallet_type = body.get("wallet_type")
    # MTODO: make mode variable. Either trough setting or body parameter
    key_management_mode = WalletRecord.MODE_MANAGED  # body.get("key_management_mode")

    wallet_config = {"type": wallet_type, "name": wallet_name}
    if key_management_mode == WalletRecord.MODE_MANAGED:
        wallet_config["key"] = wallet_key

    # MTODO: This only checks if we have a record. Not if the wallet actually exists
    # MTODO: we need to check the wallet_name is not the same as the base wallet
    # MTODO: optionally remove wallet_name input and use wallet_record_id instead
    wallet_records = await WalletRecord.query(context, {"wallet_name": wallet_name})
    if len(wallet_records) > 0:
        raise web.HTTPConflict(reason=f"Wallet with name {wallet_name} already exists")

    # create wallet record
    wallet_record = WalletRecord(
        wallet_config=wallet_config,
        key_management_mode=key_management_mode,
    )
    await wallet_record.save(context)

    # create actual wallet
    wallet_instance = await wallet_record.get_instance(context, {"key": wallet_key})
    await wallet_instance.close()

    token = get_wallet_jwt(context, wallet_record, wallet_key)
    result = {
        **format_wallet_record(wallet_record),
        "token": token,
    }
    return web.json_response(result)


@docs(
    tags=["multitenancy"],
    summary="Remove a subwallet",
)
@match_info_schema(WalletIdMatchInfoSchema())
# MTODO: response schema
# MTODO: For non-managed wallets we will need the key to unlock the wallet
async def wallet_remove(request: web.BaseRequest):
    """
    Request handler to remove a subwallet from agent and storage.

    Args:
        request: aiohttp request object.

    """

    context = request.app["request_context"]
    wallet_id = request.match_info["wallet_id"]

    try:
        # MTODO: Should be possible without cast
        wallet_record = cast(
            WalletRecord, await WalletRecord.retrieve_by_id(context, wallet_id)
        )

        # MTODO: We need to remove all instances from cache
        # We can't use auto_remove, because the wallet provider does
        #  not support it at the moment.
        wallet_instance = await wallet_record.get_instance(context)

        if wallet_instance.type == "indy":
            indy_wallet = cast(IndyWallet, wallet_instance)
            await indy_wallet.remove()

        await wallet_record.delete_record(context)
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    return web.json_response({})


# MTODO: add wallet import
# MTODO: add wallet export
# MTODO: add rotate wallet key


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/multitenancy/wallets", wallet_list, allow_head=False),
            web.get("/multitenancy/wallet/{wallet_id}", wallet_get, allow_head=False),
            web.post("/multitenancy/wallet", wallet_create),
            web.delete("/multitenancy/wallet/{wallet_id}", wallet_remove),
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
