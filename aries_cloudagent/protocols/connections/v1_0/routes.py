"""Connection handling admin routes."""

import json

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)

from marshmallow import fields, validate, validates_schema

from ....connections.models.conn_record import ConnRecord, ConnRecordSchema
from ....messaging.models.base import BaseModelError
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import (
    ENDPOINT,
    INDY_DID,
    INDY_RAW_PUBLIC_KEY,
    UUIDFour,
)
from ....storage.error import StorageError, StorageNotFoundError
from ....wallet.error import WalletError

from .manager import ConnectionManager, ConnectionManagerError
from .message_types import SPEC_URI
from .messages.connection_invitation import (
    ConnectionInvitation,
    ConnectionInvitationSchema,
)

from .role import Role


class ConnectionListSchema(OpenAPISchema):
    """Result schema for connection list."""

    results = fields.List(
        fields.Nested(ConnRecordSchema()),
        description="List of connection records",
    )


class ReceiveInvitationRequestSchema(ConnectionInvitationSchema):
    """Request schema for receive invitation request."""

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Bypass middleware field validation."""


class InvitationConnectionTargetRequestSchema(OpenAPISchema):
    """Request schema for invitation connection target."""

    recipient_keys = fields.List(
        fields.Str(description="Recipient public key", **INDY_RAW_PUBLIC_KEY),
        required=False,
        description="List of recipient keys",
    )
    service_endpoint = fields.Str(
        required=False,
        description="Connection endpoint",
        example="http://192.168.56.102:8020",
    )
    routing_keys = fields.List(
        fields.Str(description="Routing key", **INDY_RAW_PUBLIC_KEY),
        required=False,
        description="List of routing keys",
    )


class InvitationResultSchema(OpenAPISchema):
    """Result schema for a new connection invitation."""

    connection_id = fields.Str(
        description="Connection identifier", example=UUIDFour.EXAMPLE
    )
    invitation = fields.Nested(ConnectionInvitationSchema())
    invitation_url = fields.Str(
        description="Invitation URL",
        example="http://192.168.56.101:8020/invite?c_i=eyJAdHlwZSI6Li4ufQ==",
    )


class ConnectionStaticRequestSchema(OpenAPISchema):
    """Request schema for a new static connection."""

    my_seed = fields.Str(description="Seed to use for the local DID", required=False)
    my_did = fields.Str(description="Local DID", required=False, **INDY_DID)
    their_seed = fields.Str(
        description="Seed to use for the remote DID", required=False
    )
    their_did = fields.Str(description="Remote DID", required=False, **INDY_DID)
    their_verkey = fields.Str(description="Remote verification key", required=False)
    their_endpoint = fields.Str(
        description="URL endpoint for the other party", required=False, **ENDPOINT
    )
    their_label = fields.Str(
        description="Label to assign to this connection", required=False
    )
    alias = fields.Str(description="Alias to assign to this connection", required=False)


class ConnectionStaticResultSchema(OpenAPISchema):
    """Result schema for new static connection."""

    my_did = fields.Str(description="Local DID", required=True, **INDY_DID)
    mv_verkey = fields.Str(
        description="My verification key", required=True, **INDY_RAW_PUBLIC_KEY
    )
    my_endpoint = fields.Str(description="My URL endpoint", required=True, **ENDPOINT)
    their_did = fields.Str(description="Remote DID", required=True, **INDY_DID)
    their_verkey = fields.Str(
        description="Remote verification key", required=True, **INDY_RAW_PUBLIC_KEY
    )
    record = fields.Nested(ConnRecordSchema, required=True)


class ConnectionsListQueryStringSchema(OpenAPISchema):
    """Parameters and validators for connections list request query string."""

    alias = fields.Str(
        description="Alias",
        required=False,
        example="Barry",
    )
    invitation_key = fields.Str(
        description="invitation key", required=False, **INDY_RAW_PUBLIC_KEY
    )
    my_did = fields.Str(description="My DID", required=False, **INDY_DID)
    state = fields.Str(
        description="Connection state",
        required=False,
        validate=validate.OneOf(
            {label for state in ConnRecord.State for label in state.value}
        ),
    )
    their_did = fields.Str(description="Their DID", required=False, **INDY_DID)
    their_role = fields.Str(
        description="Their role in the connection protocol",
        required=False,
        validate=validate.OneOf(
            [label for role in ConnRecord.Role for label in role.value]
        ),
        example=ConnRecord.Role.REQUESTER.rfc160,
    )
    tx_my_role = fields.Str(
        description=" A list of my assigned connection role (AUTHOR/ENDORSER)",
        required=False,
        example="AUTHOR",
    )
    tx_their_role = fields.Str(
        description="A list of their assigned connection role (AUTHOR/ENDORSER)",
        required=False,
        example="ENDORSER",
    )


class CreateInvitationQueryStringSchema(OpenAPISchema):
    """Parameters and validators for create invitation request query string."""

    alias = fields.Str(
        description="Alias",
        required=True,
        example="Barry",
    )
    auto_accept = fields.Boolean(
        description="Auto-accept connection (default as per configuration)",
        required=False,
    )
    public = fields.Boolean(
        description="Create invitation from public DID (default false)", required=False
    )
    multi_use = fields.Boolean(
        description="Create invitation for multiple use (default false)", required=False
    )
    my_role = fields.Str(
        description="Role",
        required=False,
        validate=validate.OneOf(
            [r.name for r in Role if isinstance(r.value[0], int)] + ["reset"]
        ),
    )



class ReceiveInvitationQueryStringSchema(OpenAPISchema):
    """Parameters and validators for receive invitation request query string."""

    alias = fields.Str(
        description="Alias",
        required=False,
        example="Barry",
    )
    auto_accept = fields.Boolean(
        description="Auto-accept connection (defaults to configuration)",
        required=False,
    )
    my_role = fields.Str(
        description="Role",
        required=False,
        validate=validate.OneOf(
            [r.name for r in Role if isinstance(r.value[0], int)] + ["reset"]
        ),
    )


class AcceptInvitationQueryStringSchema(OpenAPISchema):
    """Parameters and validators for accept invitation request query string."""

    my_endpoint = fields.Str(description="My URL endpoint", required=False, **ENDPOINT)
    my_label = fields.Str(
        description="Label for connection", required=False, example="Broker"
    )
    my_role = fields.Str(
        description="Role",
        required=False,
        validate=validate.OneOf(
            [r.name for r in Role if isinstance(r.value[0], int)] + ["reset"]
        ),
    )


class AcceptRequestQueryStringSchema(OpenAPISchema):
    """Parameters and validators for accept conn-request web-request query string."""

    my_endpoint = fields.Str(description="My URL endpoint", required=False, **ENDPOINT)
    my_role = fields.Str(
        description="Role",
        required=False,
        validate=validate.OneOf(
            [r.name for r in Role if isinstance(r.value[0], int)] + ["reset"]
        ),
    )


class ConnIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    conn_id = fields.Str(
        description="Connection identifier", required=True, example=UUIDFour.EXAMPLE
    )


class ConnIdRefIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection and ref ids."""

    conn_id = fields.Str(
        description="Connection identifier", required=True, example=UUIDFour.EXAMPLE
    )

    ref_id = fields.Str(
        description="Inbound connection identifier",
        required=True,
        example=UUIDFour.EXAMPLE,
    )


def connection_sort_key(conn):
    """Get the sorting key for a particular connection."""

    conn_rec_state = ConnRecord.State.get(conn["state"])
    if conn_rec_state is ConnRecord.State.ABANDONED:
        pfx = "2"
    elif conn_rec_state is ConnRecord.State.INVITATION:
        pfx = "1"
    else:
        pfx = "0"

    return pfx + conn["created_at"]


@docs(
    tags=["connection"],
    summary="Query agent-to-agent connections",
)
@querystring_schema(ConnectionsListQueryStringSchema())
@response_schema(ConnectionListSchema(), 200)
async def connections_list(request: web.BaseRequest):
    """
    Request handler for searching connection records.

    Args:
        request: aiohttp request object

    Returns:
        The connection list response

    """
    context = request.app["request_context"]

    tag_filter = {}
    for param_name in (
        "invitation_id",
        "my_did",
        "their_did",
        "request_id",
    ):
        if param_name in request.query and request.query[param_name] != "":
            tag_filter[param_name] = request.query[param_name]

    post_filter = {}
    if request.query.get("alias"):
        post_filter["alias"] = request.query["alias"]
    if request.query.get("state"):
        post_filter["state"] = [
            v for v in ConnRecord.State.get(request.query["state"]).value
        ]
    if request.query.get("their_role"):
        post_filter["their_role"] = [
            v for v in ConnRecord.Role.get(request.query["their_role"]).value
        ]

    try:
        records = await ConnRecord.query(
            context, tag_filter, post_filter_positive=post_filter
        )
        results = [record.serialize() for record in records]
        results.sort(key=connection_sort_key)
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"results": results})


@docs(tags=["connection"], summary="Fetch a single connection record")
@match_info_schema(ConnIdMatchInfoSchema())
@response_schema(ConnRecordSchema(), 200)
async def connections_retrieve(request: web.BaseRequest):
    """
    Request handler for fetching a single connection record.

    Args:
        request: aiohttp request object

    Returns:
        The connection record response

    """
    context = request.app["request_context"]
    connection_id = request.match_info["conn_id"]

    try:
        record = await ConnRecord.retrieve_by_id(context, connection_id)
        result = record.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except BaseModelError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(result)


@docs(
    tags=["connection"],
    summary="Create a new connection invitation",
)
@querystring_schema(CreateInvitationQueryStringSchema())
@request_schema(InvitationConnectionTargetRequestSchema())
@response_schema(InvitationResultSchema(), 200)
async def connections_create_invitation(request: web.BaseRequest):
    """
    Request handler for creating a new connection invitation.

    Args:
        request: aiohttp request object

    Returns:
        The connection invitation details

    """
    context = request.app["request_context"]
    auto_accept = json.loads(request.query.get("auto_accept", "null"))
    alias = request.query.get("alias")
    public = json.loads(request.query.get("public", "false"))
    multi_use = json.loads(request.query.get("multi_use", "false"))
    body = await request.json()
    recipient_keys = body.get("recipient_keys")
    service_endpoint = body.get("service_endpoint")
    routing_keys = body.get("routing_keys")

    tx_my_role = request.query.get("my_role")

    if public and not context.settings.get("public_invites"):
        raise web.HTTPForbidden(
            reason="Configuration does not include public invitations"
        )
    base_url = context.settings.get("invite_base_url")

    connection_mgr = ConnectionManager(context)
    try:
        (connection, invitation) = await connection_mgr.create_invitation(
            auto_accept=auto_accept, public=public, multi_use=multi_use,
            alias=alias, recipient_keys=recipient_keys, my_endpoint=service_endpoint,
            routing_keys=routing_keys, tx_my_role=tx_my_role
        )

        result = {
            "connection_id": connection and connection.connection_id,
            "invitation": invitation.serialize(),
            "invitation_url": invitation.to_url(base_url),
        }
    except (ConnectionManagerError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    if connection and connection.alias:
        result["alias"] = connection.alias


    return web.json_response(result)


@docs(
    tags=["connection"],
    summary="Receive a new connection invitation",
)
@querystring_schema(ReceiveInvitationQueryStringSchema())
@request_schema(ReceiveInvitationRequestSchema())
@response_schema(ConnRecordSchema(), 200)
async def connections_receive_invitation(request: web.BaseRequest):
    """
    Request handler for receiving a new connection invitation.

    Args:
        request: aiohttp request object

    Returns:
        The resulting connection record details

    """
    context = request.app["request_context"]
    if context.settings.get("admin.no_receive_invites"):
        raise web.HTTPForbidden(
            reason="Configuration does not allow receipt of invitations"
        )
    connection_mgr = ConnectionManager(context)
    invitation_json = await request.json()
    tx_my_role = request.query.get("my_role")

    try:
        invitation = ConnectionInvitation.deserialize(invitation_json)
        auto_accept = json.loads(request.query.get("auto_accept", "null"))
        alias = request.query.get("alias")
        connection = await connection_mgr.receive_invitation(
            invitation, auto_accept=auto_accept, alias=alias, tx_my_role=tx_my_role,
        )
        result = connection.serialize()
    except (ConnectionManagerError, StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err


    return web.json_response(result)


@docs(
    tags=["connection"],
    summary="Accept a stored connection invitation",
)
@match_info_schema(ConnIdMatchInfoSchema())
@querystring_schema(AcceptInvitationQueryStringSchema())
@response_schema(ConnRecordSchema(), 200)
async def connections_accept_invitation(request: web.BaseRequest):
    """
    Request handler for accepting a stored connection invitation.

    Args:
        request: aiohttp request object

    Returns:
        The resulting connection record details

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    connection_id = request.match_info["conn_id"]

    try:
        connection = await ConnRecord.retrieve_by_id(context, connection_id)
        connection_mgr = ConnectionManager(context)
        my_label = request.query.get("my_label") or None
        my_endpoint = request.query.get("my_endpoint") or None
        my_role = request.query.get("my_role")
        request = await connection_mgr.create_request(connection, my_label, my_endpoint, my_role)
        result = connection.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (StorageError, WalletError, ConnectionManagerError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(request, connection_id=connection.connection_id)
    return web.json_response(result)


@docs(
    tags=["connection"],
    summary="Accept a stored connection request",
)
@match_info_schema(ConnIdMatchInfoSchema())
@querystring_schema(AcceptRequestQueryStringSchema())
@response_schema(ConnRecordSchema(), 200)
async def connections_accept_request(request: web.BaseRequest):
    """
    Request handler for accepting a stored connection request.

    Args:
        request: aiohttp request object

    Returns:
        The resulting connection record details

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    connection_id = request.match_info["conn_id"]

    try:
        connection = await ConnRecord.retrieve_by_id(context, connection_id)
        connection_mgr = ConnectionManager(context)
        my_endpoint = request.query.get("my_endpoint") or None
        my_role = request.query.get("my_role")
        response = await connection_mgr.create_response(connection, my_endpoint, my_role)
        result = connection.serialize()       
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (StorageError, WalletError, ConnectionManagerError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(response, connection_id=connection.connection_id)
    return web.json_response(result)


@docs(
    tags=["connection"], summary="Assign another connection as the inbound connection"
)
@match_info_schema(ConnIdRefIdMatchInfoSchema())
async def connections_establish_inbound(request: web.BaseRequest):
    """
    Request handler for setting the inbound connection on a connection record.

    Args:
        request: aiohttp request object
    """
    context = request.app["request_context"]
    connection_id = request.match_info["conn_id"]
    outbound_handler = request.app["outbound_message_router"]
    inbound_connection_id = request.match_info["ref_id"]

    try:
        connection = await ConnRecord.retrieve_by_id(context, connection_id)
        connection_mgr = ConnectionManager(context)
        await connection_mgr.establish_inbound(
            connection, inbound_connection_id, outbound_handler
        )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (StorageError, WalletError, ConnectionManagerError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})


@docs(tags=["connection"], summary="Remove an existing connection record")
@match_info_schema(ConnIdMatchInfoSchema())
async def connections_remove(request: web.BaseRequest):
    """
    Request handler for removing a connection record.

    Args:
        request: aiohttp request object
    """
    context = request.app["request_context"]
    connection_id = request.match_info["conn_id"]

    try:
        connection = await ConnRecord.retrieve_by_id(context, connection_id)
        await connection.delete_record(context)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except StorageError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})


@docs(tags=["connection"], summary="Create a new static connection")
@request_schema(ConnectionStaticRequestSchema())
@response_schema(ConnectionStaticResultSchema(), 200)
async def connections_create_static(request: web.BaseRequest):
    """
    Request handler for creating a new static connection.

    Args:
        request: aiohttp request object

    Returns:
        The new connection record

    """
    context = request.app["request_context"]
    body = await request.json()

    connection_mgr = ConnectionManager(context)
    try:
        (
            my_info,
            their_info,
            connection,
        ) = await connection_mgr.create_static_connection(
            my_seed=body.get("my_seed") or None,
            my_did=body.get("my_did") or None,
            their_seed=body.get("their_seed") or None,
            their_did=body.get("their_did") or None,
            their_verkey=body.get("their_verkey") or None,
            their_endpoint=body.get("their_endpoint") or None,
            their_label=body.get("their_label") or None,
            alias=body.get("alias") or None,
        )
        response = {
            "my_did": my_info.did,
            "my_verkey": my_info.verkey,
            "my_endpoint": context.settings.get("default_endpoint"),
            "their_did": their_info.did,
            "their_verkey": their_info.verkey,
            "record": connection.serialize(),
        }
    except (WalletError, StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(response)


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/connections", connections_list, allow_head=False),
            web.get("/connections/{conn_id}", connections_retrieve, allow_head=False),
            web.post("/connections/create-static", connections_create_static),
            web.post("/connections/create-invitation", connections_create_invitation),
            web.post("/connections/receive-invitation", connections_receive_invitation),
            web.post(
                "/connections/{conn_id}/accept-invitation",
                connections_accept_invitation,
            ),
            web.post(
                "/connections/{conn_id}/accept-request", connections_accept_request
            ),
            web.post(
                "/connections/{conn_id}/establish-inbound/{ref_id}",
                connections_establish_inbound,
            ),
            web.delete("/connections/{conn_id}", connections_remove),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "connection",
            "description": "Connection management",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
