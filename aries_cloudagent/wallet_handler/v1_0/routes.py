from aiohttp import web
from aiohttp_apispec import (
    docs,
    # match_info_schema,
    request_schema,
)
from ...storage.base import BaseStorage
from ...wallet_handler import WalletHandler
from marshmallow import fields, Schema

from ...wallet.models.wallet_record import WalletRecord
from ...wallet.error import WalletError, WalletNotFoundError, WalletDuplicateError
from ...ledger.base import BaseLedger


class AddWalletSchema(Schema):
    """Request schema for adding a new wallet which will be registered by the agent."""

    wallet_name = fields.Str(
        description="Wallet identifier.",
        example='MyNewWallet'
    )
    wallet_key = fields.Str(
        description="Master key used for key derivation.",
        example='MySecretKey123'
    )
    seed = fields.Str(
        description="Seed used for did derivation.",
        example='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
    )
    wallet_type = fields.Str(
        description="Type the newly generated wallet should be [basic | indy].",
        example='indy',
        default='indy'
    )


WALLET_TYPES = {
    "basic": "aries_cloudagent.wallet.basic.BasicWallet",
    "indy": "aries_cloudagent.wallet.indy.IndyWallet",
}


@docs(
    tags=["wallet"],
    summary="Add new wallet to be handled by this agent.",
)
@request_schema(AddWalletSchema())
async def add_wallet(request: web.BaseRequest):
    """
    Request handler for adding a new wallet for handling by the agent.

    Args:
        request: aiohttp request object

    Raises:
        HTTPBadRequest: if no name is provided to identify new wallet.
        HTTPBadRequest: if a not supported wallet type is specified.

    """
    context = request["context"]

    body = await request.json()

    config = {}
    if body.get("wallet_name"):
        config["name"] = body.get("wallet_name")
    else:
        raise web.HTTPBadRequest(reason="Name needs to be provided to create a wallet.")
    config["key"] = body.get("wallet_key")
    wallet_type = body.get("wallet_type")
    if wallet_type not in WALLET_TYPES:
        raise web.HTTPBadRequest(reason="Specified wallet type is not supported.")
    config["type"] = wallet_type

    wallet_handler: WalletHandler = await context.inject(WalletHandler, required=False)

    try:
        await wallet_handler.add_instance(config, context)
    except WalletDuplicateError:
        raise web.HTTPBadRequest(reason="Wallet with specified name already exists.")

    wallet_record = WalletRecord(wallet_config=config, wallet_name=config['name'])
    await wallet_record.save(context)

    return web.Response(body='{"result": "created"}', status=201)


@docs(
    tags=["wallet"],
    summary="Get identifiers of all handled wallets.",
)
async def get_wallets(request: web.BaseRequest):
    """
    Request handler to obtain all identifiers of the handled wallets.

    Args:
        request: aiohttp request object.

    """
    context = request["context"]

    wallet_handler: WalletHandler = await context.inject(WalletHandler, required=False)
    wallet_names = await wallet_handler.get_instances()

    return web.json_response({"result": wallet_names})


@docs(
    tags=["wallet"],
    summary="Remove a wallet from handled wallets and delete it from storage.",
    parameters=[{"in": "path", "name": "id", "description": "Identifier of wallet."}],
)
async def remove_wallet(request: web.BaseRequest):
    """
    Request handler to remove a wallet from agent and storage.

    Args:
        request: aiohttp request object.

    """
    context = request["context"]
    wallet_name = request.match_info["id"]

    wallet_handler: WalletHandler = await context.inject(WalletHandler)

    # Remove wallet record. Because wallet_records are only stored in storage
    # of base wallet right know, only base wallet can remove wallets.
    post_filter = {"wallet_name": wallet_name}
    wallet_records = await WalletRecord.query(context, post_filter_positive=post_filter)
    if len(wallet_records) < 1:
        raise web.HTTPNotFound(reason=f"No record for wallet {wallet_name} found.")
    elif len(wallet_records) > 1:
        raise web.HTTPError(
            reason=f"Found multiple records for wallet with name {wallet_name}.")
    await wallet_records[0].delete_record(context)

    try:
        await wallet_handler.delete_instance(wallet_name)
        ledger = context.injector._providers[BaseLedger]._instances.pop(wallet_name)
        context.injector._providers[BaseStorage]._instances.pop(wallet_name)
        await ledger.close()
    except WalletNotFoundError:
        raise web.HTTPNotFound(reason="Requested wallet to delete not in storage.")
    except WalletError:
        raise web.HTTPError(reason=WalletError.message)

    return web.json_response({"result": "Deleted wallet {}".format(wallet_name)})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/wallet", get_wallets),
            web.post("/wallet", add_wallet),
            web.post("/wallet/{id}/remove", remove_wallet)
        ]
    )
