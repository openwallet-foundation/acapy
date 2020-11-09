import json

from aiohttp import web
from aiohttp_apispec import (
    docs,
    request_schema, response_schema, querystring_schema, match_info_schema,
)

from ...messaging.valid import UUIDFour
from ...wallet_handler import WalletHandler
from marshmallow import fields, Schema

from ...wallet.models.wallet_record import WalletRecord, WalletRecordSchema
from ...messaging.models.openapi import OpenAPISchema

from ..error import WalletError, WalletDuplicateError
from ..error import WalletAccessError
from ..error import WalletNotFoundError


class WalletAddSchema(Schema):
    """Request schema for adding a new wallet which will be registered by the agent."""

    name = fields.Str(required=True, description="Wallet name", example='faber',)
    key = fields.Str(required=True, description="Master key used for key derivation", example='faber.key.123',)
    type = fields.Str(required=True, description="Type of wallet [basic | indy]", example='indy',)
    label = fields.Str(required=False, description="Optional label when connection is established", example='faber',)
    image_url = fields.Str(required=False, description="Optional image URL for connection invitation",
                           example="http://image_url/logo.jpg",)
    webhook_urls = fields.List(
        fields.Str(required=False, description="Optional webhook URL to receive webhook messages",
                   example="http://localhost:8022/webhooks",))


class WalletRecordListQueryStringSchema(OpenAPISchema):
    """Parameters and validators for wallet list request query string."""

    wallet_id = fields.Str(required=False, description="Wallet identifier",
                           example=UUIDFour.EXAMPLE,)
    name = fields.Str(required=False, description="Wallet name of interest", example="faber")
    label = fields.Str(required=False, description="Label when connection is established", example='faber',)
    image_url = fields.Str(required=False, description="Image URL for connection invitation",
                           example="http://image_url/logo.jpg",)
    webhook_urls = fields.Str(required=False, description="Webhook URLs to receive webhook messages",
                              example="http://localhost:8022/webhooks",)


class WalletRecordListSchema(Schema):
    """Schema for a list of wallets."""

    results = fields.List(fields.Nested(WalletRecordSchema()), description="a list of wallet")


class WalletIdMatchInfoSchema(Schema):
    """Path parameters and validators for request taking wallet id."""

    wallet_id = fields.Str(description="wallet identifier", example=UUIDFour.EXAMPLE,)


class WalletUpdateSchema(Schema):
    """schema for updating a wallet."""

    label = fields.Str(required=False, description="Label when connection is established", example='faber',)
    image_url = fields.Str(required=False, description="Image URL for connection invitation",
                           example="http://image_url/logo.jpg",)
    webhook_urls = fields.List(
        fields.Str(required=False, description="Webhook URL to receive webhook messages",
                   example="http://localhost:8022/webhooks",))


WALLET_TYPES = {
    "basic": "aries_cloudagent.wallet.basic.BasicWallet",
    "indy": "aries_cloudagent.wallet.indy.IndyWallet",
}


@docs(tags=["wallet"], summary="Add new wallet to be handled by this agent",)
@request_schema(WalletAddSchema())
@response_schema(WalletRecordSchema(), 201)
async def add_wallet(request: web.BaseRequest):
    """
    Request handler for adding a new wallet for handling by the agent.

    Args:
        request: aiohttp request object

    Raises:
        HTTPBadRequest: if a not supported wallet type is specified.
        HTTPBadRequest: if webhook_urls is not list type.

    """
    context = request["context"]
    body = await request.json()

    config = {"name": body.get("name"), "key": body.get("key"), "type": body.get("type")}
    label = body.get("label", "")
    image_url = body.get("image_url", "")
    webhook_urls = body.get("webhook_urls", [])

    if config["type"] not in WALLET_TYPES:
        raise web.HTTPBadRequest(reason="Specified wallet type is not supported.")
    if type(webhook_urls) != list:
        raise web.HTTPBadRequest(reason="webhook_urls must be list")

    wallet_handler: WalletHandler = await context.inject(WalletHandler, required=False)
    try:
        wallet_record = await wallet_handler.add_wallet(
            config=config, label=label, image_url=image_url, webhook_urls=webhook_urls
        )
    except WalletDuplicateError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(wallet_record.serialize(), status=201)


@docs(tags=["wallet"], summary="Get information of wallets (base wallet only)",)
@querystring_schema(WalletRecordListQueryStringSchema())
@response_schema(WalletRecordListSchema(), 200)
async def get_wallets(request: web.BaseRequest):
    """
    Request handler to obtain all identifiers of the handled wallets.

    Args:
        request: aiohttp request object.

    """
    context = request["context"]
    wallet_name = context.settings.get_value("wallet.id")

    # base wallet only can do this
    if wallet_name != context.settings.get_value("wallet.name"):
        raise web.HTTPUnauthorized(reason="Only base wallet allowed.")

    wallet_handler: WalletHandler = await context.inject(WalletHandler, required=False)
    if request.query.get("webhook_id"):
        wallet_records = [await wallet_handler.get_wallet(request.query.get("webhook_id"))]
    else:
        query = {}
        for param_name in ("name", "label", "image_url"):
            if param_name in request.query:
                query[param_name] = request.query[param_name]
        if "webhook_urls" in request.query:
            query["webhook_urls"] = json.loads(request.query["webhook_urls"])

        wallet_records = await wallet_handler.get_wallets(query)

    results = []
    for wallet_record in wallet_records:
        results.append(wallet_record.serialize())
    return web.json_response({"results": results}, status=200)


@docs(tags=["wallet"], summary="Get information of my wallet",)
@response_schema(WalletRecordSchema(), 200)
async def get_my_wallet(request: web.BaseRequest):
    """
    Request handler to obtain all identifiers of the handled wallets.

    Args:
        request: aiohttp request object.

    """
    context = request["context"]
    wallet_name = context.settings.get_value("wallet.id")

    wallet_handler: WalletHandler = await context.inject(WalletHandler, required=False)
    query = {"name": wallet_name}
    wallet_records = await wallet_handler.get_wallets(query)
    if len(wallet_records) < 1:
        raise web.HTTPNotFound(reason=f"No record for wallet {wallet_name} found.")
    elif len(wallet_records) > 1:
        raise web.HTTPError(reason=f"Found multiple records for wallet with name {wallet_name}.")
    wallet_record: WalletRecord = wallet_records[0]

    return web.json_response(wallet_record.serialize(), status=200)


@docs(tags=["wallet"], summary="Remove a wallet (base wallet only)",)
@match_info_schema(WalletIdMatchInfoSchema())
async def remove_wallet(request: web.BaseRequest):
    """
    Request handler to remove a wallet from agent and storage.

    Args:
        request: aiohttp request object.

    """
    context = request["context"]
    wallet_name = context.settings.get_value("wallet.id")
    wallet_id = request.match_info["wallet_id"]

    # base wallet only can do this
    if wallet_name != context.settings.get_value("wallet.name"):
        raise web.HTTPUnauthorized(reason="Only base wallet allowed.")

    wallet_handler: WalletHandler = await context.inject(WalletHandler, required=False)

    try:
        await wallet_handler.remove_wallet(wallet_id=wallet_id)
    except WalletNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except WalletAccessError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    except WalletError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.Response(status=204)


@docs(tags=["wallet"], summary="Remove my wallet",)
async def remove_my_wallet(request: web.BaseRequest):
    """
    Request handler to remove a wallet from agent and storage.

    Args:
        request: aiohttp request object.

    """
    context = request["context"]
    wallet_name = context.settings.get_value("wallet.id")

    wallet_handler: WalletHandler = await context.inject(WalletHandler, required=False)

    try:
        await wallet_handler.remove_wallet(wallet_name=wallet_name)
    except WalletNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except WalletAccessError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    except WalletError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.Response(status=204)


@docs(tags=["wallet"], summary="Update information of a wallet (base wallet only)",)
@match_info_schema(WalletIdMatchInfoSchema())
@request_schema(WalletUpdateSchema())
@response_schema(WalletRecordSchema(), 200)
async def update_wallet(request: web.BaseRequest):
    """
    Request handler to update a wallet from storage.

    Args:
        request: aiohttp request object.

    """
    context = request["context"]
    wallet_name = context.settings.get_value("wallet.id")
    wallet_id = request.match_info["wallet_id"]
    body = await request.json()

    # base wallet only can do this
    if wallet_name != context.settings.get_value("wallet.name"):
        raise web.HTTPUnauthorized(reason="Only base wallet allowed.")

    label = body.get("label")
    image_url = body.get("image_url")
    webhook_urls = body.get("webhook_urls")
    if label is None and image_url is None and webhook_urls is None:
        raise web.HTTPBadRequest(reason="At least one parameter is required.")
    if webhook_urls is not None and type(webhook_urls) != list:
        raise web.HTTPBadRequest(reason="Webhook_urls must be list")

    wallet_handler: WalletHandler = await context.inject(WalletHandler, required=False)
    try:
        wallet_record = await wallet_handler.update_wallet(
            wallet_id=wallet_id,
            label=label,
            image_url=image_url,
            webhook_urls=webhook_urls
        )
    except WalletNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    return web.json_response(wallet_record.serialize())


@docs(tags=["wallet"], summary="Update information of my wallet",)
@request_schema(WalletUpdateSchema())
@response_schema(WalletRecordSchema(), 200)
async def update_my_wallet(request: web.BaseRequest):
    """
    Request handler to update my wallet from storage.

    Args:
        request: aiohttp request object.

    """
    context = request["context"]
    wallet_name = context.settings.get_value("wallet.id")
    body = await request.json()

    label = body.get("label")
    image_url = body.get("image_url")
    webhook_urls = body.get("webhook_urls")
    if label is None and image_url is None and webhook_urls is None:
        raise web.HTTPBadRequest(reason="At least one parameter is required.")
    if webhook_urls is not None and type(webhook_urls) != list:
        raise web.HTTPBadRequest(reason="Webhook_urls must be list")

    wallet_handler: WalletHandler = await context.inject(WalletHandler, required=False)
    try:
        wallet_record = await wallet_handler.update_wallet(
            wallet_name=wallet_name,
            label=label,
            image_url=image_url,
            webhook_urls=webhook_urls
        )
    except WalletNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    return web.json_response(wallet_record.serialize())


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/wallet", get_wallets, allow_head=False),
            web.get("/wallet/me", get_my_wallet, allow_head=False),
            web.post("/wallet", add_wallet),
            web.put("/wallet/me", update_my_wallet),
            web.put("/wallet/{wallet_id}", update_wallet),
            web.delete("/wallet/me", remove_my_wallet),
            web.delete("/wallet/{wallet_id}", remove_wallet),
        ]
    )
