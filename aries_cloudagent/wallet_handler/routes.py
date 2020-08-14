"""Wallet handler admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
import hashlib
import re
from base64 import b64encode

from .handler import WalletHandler
from .error import WalletNotFoundError
from ..wallet.base import BaseWallet
from ..wallet.error import WalletError, WalletDuplicateError

# from ..storage.base import BaseStorage
# from ..storage.record import StorageRecord
from ..storage.error import StorageNotFoundError

from ..protocols.connections.v1_0.manager import ConnectionManager
from ..protocols.connections.v1_0.routes import (
    InvitationResultSchema,
)

from ..connections.models.connection_record import (
    ConnectionRecord,
    ConnectionRecordSchema,
)

from ..protocols.connections.v1_0.messages.connection_invitation import (
    ConnectionInvitation,
    ConnectionInvitationSchema,
)

from marshmallow import fields, Schema

WALLET_TYPES = {
    "basic": "aries_cloudagent.wallet.basic.BasicWallet",
    "indy": "aries_cloudagent.wallet.indy.IndyWallet",
}


async def create_connection_handle(wallet: BaseWallet, n: int) -> str:
    """
    Create a new path for the currently active wallet.

    Returns:
        path: path to use as postfix to add to default endpoint

    """
    id_raw = wallet.name + '_' + str(n)
    digest = hashlib.sha256(str.encode(id_raw)).digest()
    id = b64encode(digest).decode()
    # Clear all special characters
    path = re.sub('[^a-zA-Z0-9 \n]', '', id)

    return path


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


@docs(
    tags=["wallet"],
    summary="Add new wallet to be handled by this agent.",
)
@request_schema(AddWalletSchema())
async def wallet_handler_add_wallet(request: web.BaseRequest):
    """
    Request handler for adding a new wallet for handling by the agent.

    Args:
        request: aiohttp request object

    Raises:
        HTTPBadRequest: if no name is provided to identify new wallet.
        HTTPBadRequest: if a not supported wallet type is specified.

    """
    context = request.app["request_context"]

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

    return web.Response(body='created', status=201)


@docs(
    tags=["wallet"],
    summary="Get identifiers of all handled wallets.",
)
async def wallet_handler_get_wallets(request: web.BaseRequest):
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
async def wallet_handler_remove_wallet(request: web.BaseRequest):
    """
    Request handler to remove a wallet from agent and storage.

    Args:
        request: aiohttp request object.

    """
    context = request["context"]
    wallet_name = request.match_info["id"]

    wallet: BaseWallet = await context.inject(BaseWallet)

    if wallet.name != wallet_name:
        raise web.HTTPUnauthorized(reason="not owned wallet not allowed.")

    wallet_handler: WalletHandler = await context.inject(WalletHandler)

    try:
        await wallet_handler.delete_instance(wallet_name)
    #    raise web.HTTPBadRequest(reason="Wallet to delete not found.")
    except WalletNotFoundError:
        raise web.HTTPNotFound(reason=f"Requested wallet to delete not in storage.")
    except WalletError:
        raise web.HTTPError(reason=WalletError.message)

    return web.json_response({"result": "Deleted wallet {}".format(wallet_name)})

# ------------------------------------------------------------------------------
# Connection endpoint handlers.
# ------------------------------------------------------------------------------


@docs(
    tags=["connection"],
    summary="Create a new connection invitation for a specific wallet.",
    parameters=[
        {
            "name": "alias",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
        {
            "name": "accept",
            "in": "query",
            "schema": {"type": "string", "enum": ["none", "auto"]},
            "required": False,
        },
        {
            "name": "public",
            "in": "query",
            "schema": {"type": "int"},
            "required": False
        },
        {
            "name": "multi_use",
            "in": "query",
            "schema": {"type": "int"},
            "required": False
        },
    ],
)
@response_schema(InvitationResultSchema(), 200)
async def connections_create_invitation(request: web.BaseRequest):
    """
    Request handler for creating a new connection invitation for custodial agent.

    Args:
        request: aiohttp request object

    Returns:
        The connection invitation details

    """
    context = request["context"]
    alias = request.query.get("alias")
    public = request.query.get("public")
    multi_use = request.query.get("multi_use")

    if public and not context.settings.get("public_invites"):
        raise web.HTTPForbidden()
    base_url = context.settings.get("invite_base_url")

    wallet: BaseWallet = await context.inject(BaseWallet, required=False)
    wallet_handler: WalletHandler = await context.inject(WalletHandler)
    handle = await wallet_handler.generate_path_mapping(wallet.name)

    endpoint = context.settings.get("default_endpoint") + "/" + handle

    connection_mgr = ConnectionManager(context)
    connection, invitation = await connection_mgr.create_invitation(
        public=bool(public), multi_use=bool(multi_use), alias=alias,
        my_endpoint=endpoint
    )
    result = {
        "connection_id": connection and connection.connection_id,
        "invitation": invitation.serialize(),
        "invitation_url": invitation.to_url(base_url),
    }
    await wallet_handler.add_connection(connection.connection_id, wallet.name)
    await wallet_handler.add_key(connection.invitation_key, wallet.name)

    if connection and connection.alias:
        result["alias"] = connection.alias

    return web.json_response(result)


@docs(
    tags=["connection"],
    summary="Receive a new connection invitation",
    parameters=[
        {
            "name": "alias",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
        {
            "name": "accept",
            "in": "query",
            "schema": {"type": "string", "enum": ["none", "auto"]},
            "required": False,
        },
    ],
)
@request_schema(ConnectionInvitationSchema())
@response_schema(ConnectionRecordSchema(), 200)
async def connections_receive_invitation(request: web.BaseRequest):
    """
    Request handler for receiving a new connection invitation.

    Args:
        request: aiohttp request object

    Returns:
        The resulting connection record details

    """
    context = request["context"]
    if context.settings.get("admin.no_receive_invites"):
        raise web.HTTPForbidden()
    connection_mgr = ConnectionManager(context)
    invitation_json = await request.json()
    invitation = ConnectionInvitation.deserialize(invitation_json)
    alias = request.query.get("alias")
    connection = await connection_mgr.receive_invitation(
        invitation, alias=alias
    )
    wallet_handler: WalletHandler = await context.inject(WalletHandler)
    wallet: BaseWallet = await context.inject(BaseWallet, required=False)
    await wallet_handler.add_connection(connection.connection_id, wallet.name)
    return web.json_response(connection.serialize())


@docs(
    tags=["connection"],
    summary="Accept a stored connection invitation",
    parameters=[
        {
            "name": "my_endpoint",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
        {
            "name": "my_label",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
    ],
)
@response_schema(ConnectionRecordSchema(), 200)
async def connections_accept_invitation(request: web.BaseRequest):
    """
    Request handler for accepting a stored connection invitation.

    Args:
        request: aiohttp request object

    Returns:
        The resulting connection record details

    """
    context = request["context"]
    outbound_handler = request.app["outbound_message_router"]
    connection_id = request.match_info["id"]
    try:
        connection = await ConnectionRecord.retrieve_by_id(
            context, connection_id)
    except StorageNotFoundError:
        raise web.HTTPNotFound()
    connection_mgr = ConnectionManager(context)
    my_label = request.query.get("my_label") or None
    my_endpoint = request.query.get("my_endpoint") or None

    wallet_handler: WalletHandler = await context.inject(WalletHandler)
    wallet: BaseWallet = await context.inject(BaseWallet)

    did_info = await wallet.create_local_did()
    connection.my_did = did_info.did

    if not my_endpoint:
        path = await wallet_handler.generate_path_mapping(
            wallet.name, did=did_info.did)
        await wallet_handler.add_key(did_info.verkey, wallet.name)
        my_endpoint = context.settings.get("default_endpoint") + "/" + path
    else:
        raise web.HTTPNotImplemented(
            reason="Self defined endpoints not implemented yet.")

    request = await connection_mgr.create_request(
        connection, my_label, my_endpoint)

    await outbound_handler(request, connection_id=connection.connection_id)
    return web.json_response(connection.serialize())


@docs(
    tags=["connection"],
    summary="Accept a stored connection request",
    parameters=[
        {
            "name": "my_endpoint",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        }
    ],
)
@response_schema(ConnectionRecordSchema(), 200)
async def connections_accept_request(request: web.BaseRequest):
    """
    Request handler for accepting a stored connection request.

    Args:
        request: aiohttp request object

    Returns:
        The resulting connection record details

    """
    context = request["context"]
    outbound_handler = request.app["outbound_message_router"]
    connection_id = request.match_info["id"]
    try:
        connection = await ConnectionRecord.retrieve_by_id(context, connection_id)
    except StorageNotFoundError:
        raise web.HTTPNotFound()
    wallet: BaseWallet = await context.inject(BaseWallet)
    did_info = await wallet.create_local_did()
    connection.my_did = did_info.did
    my_endpoint = request.query.get("my_endpoint") or None
    # TODO: handle user specified endpoints.
    wallet_handler: WalletHandler = await context.inject(WalletHandler)
    if not my_endpoint:
        handle = await wallet_handler.generate_path_mapping(
            wallet.name, did=did_info.did)
        await wallet_handler.add_key(did_info.verkey, wallet.name)
        my_endpoint = context.settings.get("default_endpoint") + "/" + handle
    else:
        raise web.HTTPNotImplemented(
            reason="Self defined endpoints not implemented yet.")

    connection_mgr = ConnectionManager(context)
    response = await connection_mgr.create_response(connection, my_endpoint)

    await outbound_handler(response, connection_id=connection.connection_id)
    return web.json_response(connection.serialize())


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/wallet", wallet_handler_get_wallets),
            web.post("/wallet", wallet_handler_add_wallet),
            web.post("/wallet/{id}/remove", wallet_handler_remove_wallet),
            web.post("/connections/invite-with-endpoint",
                     connections_create_invitation),
            web.post("/connections/receive-invitation-with-endpoint",
                     connections_receive_invitation),
            web.post("/connections/{id}/accept-invitation-with-endpoint",
                     connections_accept_invitation),
            web.post("/connections/{id}/accept-request-with-endpoint",
                     connections_accept_request),
        ]
    )
