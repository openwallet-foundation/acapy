"""Connection handling admin routes."""

import json
from typing import cast

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)
from marshmallow import fields, validate, validates_schema

from ....admin.decorators.auth import tenant_authentication
from ....admin.request_context import AdminRequestContext
from ....cache.base import BaseCache
from ....connections.models.conn_record import ConnRecord, ConnRecordSchema
from ....connections.models.conn_peer_record import PeerwiseRecord, PeerwiseRecordSchema
from ....messaging.models.base import BaseModelError
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.models.paginated_query import PaginatedQuerySchema, get_limit_offset
from ....messaging.valid import (
    ENDPOINT_EXAMPLE,
    ENDPOINT_VALIDATE,
    GENERIC_DID_VALIDATE,
    INDY_DID_EXAMPLE,
    INDY_DID_VALIDATE,
    RAW_ED25519_2018_PUBLIC_KEY_EXAMPLE,
    RAW_ED25519_2018_PUBLIC_KEY_VALIDATE,
    UUID4_EXAMPLE,
    UUID4_VALIDATE,
)
from ....storage.error import StorageError, StorageNotFoundError
from ....wallet.error import WalletError
from .manager import ConnectionManager, ConnectionManagerError
from .message_types import SPEC_URI
from .messages.connection_invitation import (
    ConnectionInvitation,
    ConnectionInvitationSchema,
)


class ConnectionModuleResponseSchema(OpenAPISchema):
    """Response schema for connection module."""


class ConnectionListSchema(OpenAPISchema):
    """Result schema for connection list."""

    results = fields.List(
        fields.Nested(ConnRecordSchema()),
        required=True,
        metadata={"description": "List of connection records"},
    )


class ConnectionMetadataSchema(OpenAPISchema):
    """Result schema for connection metadata."""

    results = fields.Dict(
        metadata={"description": "Dictionary of metadata associated with connection."}
    )


class ConnectionMetadataSetRequestSchema(OpenAPISchema):
    """Request Schema for set metadata."""

    metadata = fields.Dict(
        required=True,
        metadata={"description": "Dictionary of metadata to set for connection."},
    )


class ConnectionMetadataQuerySchema(OpenAPISchema):
    """Query schema for metadata."""

    key = fields.Str(required=False, metadata={"description": "Key to retrieve."})


class ReceiveInvitationRequestSchema(ConnectionInvitationSchema):
    """Request schema for receive invitation request."""

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Bypass middleware field validation: marshmallow has no data yet."""


class CreateInvitationRequestSchema(OpenAPISchema):
    """Request schema for invitation connection target."""

    recipient_keys = fields.List(
        fields.Str(
            validate=RAW_ED25519_2018_PUBLIC_KEY_VALIDATE,
            metadata={
                "description": "Recipient public key",
                "example": RAW_ED25519_2018_PUBLIC_KEY_EXAMPLE,
            },
        ),
        required=False,
        metadata={"description": "List of recipient keys"},
    )
    service_endpoint = fields.Str(
        required=False,
        metadata={
            "description": "Connection endpoint",
            "example": "http://192.168.56.102:8020",
        },
    )
    routing_keys = fields.List(
        fields.Str(
            validate=RAW_ED25519_2018_PUBLIC_KEY_VALIDATE,
            metadata={
                "description": "Routing key",
                "example": RAW_ED25519_2018_PUBLIC_KEY_EXAMPLE,
            },
        ),
        required=False,
        metadata={"description": "List of routing keys"},
    )
    my_label = fields.Str(
        required=False,
        metadata={
            "description": "Optional label for connection invitation",
            "example": "Bob",
        },
    )
    metadata = fields.Dict(
        required=False,
        metadata={
            "description": (
                "Optional metadata to attach to the connection created with the"
                " invitation"
            )
        },
    )
    mediation_id = fields.Str(
        required=False,
        validate=UUID4_VALIDATE,
        metadata={
            "description": "Identifier for active mediation record to be used",
            "example": UUID4_EXAMPLE,
        },
    )


class InvitationResultSchema(OpenAPISchema):
    """Result schema for a new connection invitation."""

    connection_id = fields.Str(
        required=True,
        metadata={"description": "Connection identifier", "example": UUID4_EXAMPLE},
    )
    invitation = fields.Nested(ConnectionInvitationSchema(), required=True)
    invitation_url = fields.Str(
        required=True,
        metadata={
            "description": "Invitation URL",
            "example": "http://192.168.56.101:8020/invite?c_i=eyJAdHlwZSI6Li4ufQ==",
        },
    )


class ConnectionStaticRequestSchema(OpenAPISchema):
    """Request schema for a new static connection."""

    my_seed = fields.Str(
        required=False, metadata={"description": "Seed to use for the local DID"}
    )
    my_did = fields.Str(
        required=False,
        validate=INDY_DID_VALIDATE,
        metadata={"description": "Local DID", "example": INDY_DID_EXAMPLE},
    )
    their_seed = fields.Str(
        required=False, metadata={"description": "Seed to use for the remote DID"}
    )
    their_did = fields.Str(
        required=False,
        validate=INDY_DID_VALIDATE,
        metadata={"description": "Remote DID", "example": INDY_DID_EXAMPLE},
    )
    their_verkey = fields.Str(
        required=False, metadata={"description": "Remote verification key"}
    )
    their_endpoint = fields.Str(
        required=False,
        validate=ENDPOINT_VALIDATE,
        metadata={
            "description": "URL endpoint for other party",
            "example": ENDPOINT_EXAMPLE,
        },
    )
    their_label = fields.Str(
        required=False,
        metadata={"description": "Other party's label for this connection"},
    )
    alias = fields.Str(
        required=False, metadata={"description": "Alias to assign to this connection"}
    )


class ConnectionStaticResultSchema(OpenAPISchema):
    """Result schema for new static connection."""

    my_did = fields.Str(
        required=True,
        validate=INDY_DID_VALIDATE,
        metadata={"description": "Local DID", "example": INDY_DID_EXAMPLE},
    )
    my_verkey = fields.Str(
        required=True,
        validate=RAW_ED25519_2018_PUBLIC_KEY_VALIDATE,
        metadata={
            "description": "My verification key",
            "example": RAW_ED25519_2018_PUBLIC_KEY_EXAMPLE,
        },
    )
    my_endpoint = fields.Str(
        required=True,
        validate=ENDPOINT_VALIDATE,
        metadata={"description": "My URL endpoint", "example": ENDPOINT_EXAMPLE},
    )
    their_did = fields.Str(
        required=True,
        validate=INDY_DID_VALIDATE,
        metadata={"description": "Remote DID", "example": INDY_DID_EXAMPLE},
    )
    their_verkey = fields.Str(
        required=True,
        validate=RAW_ED25519_2018_PUBLIC_KEY_VALIDATE,
        metadata={
            "description": "Remote verification key",
            "example": RAW_ED25519_2018_PUBLIC_KEY_EXAMPLE,
        },
    )
    record = fields.Nested(ConnRecordSchema(), required=True)


class ConnectionsListQueryStringSchema(PaginatedQuerySchema):
    """Parameters and validators for connections list request query string."""

    alias = fields.Str(
        required=False, metadata={"description": "Alias", "example": "Barry"}
    )
    invitation_key = fields.Str(
        required=False,
        validate=RAW_ED25519_2018_PUBLIC_KEY_VALIDATE,
        metadata={
            "description": "invitation key",
            "example": RAW_ED25519_2018_PUBLIC_KEY_EXAMPLE,
        },
    )
    my_did = fields.Str(
        required=False,
        validate=GENERIC_DID_VALIDATE,
        metadata={"description": "My DID", "example": INDY_DID_EXAMPLE},
    )
    state = fields.Str(
        required=False,
        validate=validate.OneOf(
            sorted({label for state in ConnRecord.State for label in state.value})
        ),
        metadata={"description": "Connection state"},
    )
    their_did = fields.Str(
        required=False,
        validate=GENERIC_DID_VALIDATE,
        metadata={"description": "Their DID", "example": INDY_DID_EXAMPLE},
    )
    their_public_did = fields.Str(
        required=False,
        validate=GENERIC_DID_VALIDATE,
        metadata={"description": "Their Public DID", "example": INDY_DID_EXAMPLE},
    )
    their_role = fields.Str(
        required=False,
        validate=validate.OneOf(
            [label for role in ConnRecord.Role for label in role.value]
        ),
        metadata={
            "description": "Their role in the connection protocol",
            "example": ConnRecord.Role.REQUESTER.rfc160,
        },
    )
    connection_protocol = fields.Str(
        required=False,
        validate=validate.OneOf(ConnRecord.SUPPORTED_PROTOCOLS),
        metadata={
            "description": "Connection protocol used",
            "example": "connections/1.0",
        },
    )
    invitation_msg_id = fields.Str(
        required=False,
        metadata={
            "description": "Identifier of the associated Invitation Message",
            "example": UUID4_EXAMPLE,
        },
    )


class CreateInvitationQueryStringSchema(OpenAPISchema):
    """Parameters and validators for create invitation request query string."""

    alias = fields.Str(
        required=False, metadata={"description": "Alias", "example": "Barry"}
    )
    auto_accept = fields.Boolean(
        required=False,
        metadata={"description": "Auto-accept connection (defaults to configuration)"},
    )
    public = fields.Boolean(
        required=False,
        metadata={"description": "Create invitation from public DID (default false)"},
    )
    multi_use = fields.Boolean(
        required=False,
        metadata={"description": "Create invitation for multiple use (default false)"},
    )


class ReceiveInvitationQueryStringSchema(OpenAPISchema):
    """Parameters and validators for receive invitation request query string."""

    alias = fields.Str(
        required=False, metadata={"description": "Alias", "example": "Barry"}
    )
    auto_accept = fields.Boolean(
        required=False,
        metadata={"description": "Auto-accept connection (defaults to configuration)"},
    )
    mediation_id = fields.Str(
        required=False,
        validate=UUID4_VALIDATE,
        metadata={
            "description": "Identifier for active mediation record to be used",
            "example": UUID4_EXAMPLE,
        },
    )


class AcceptInvitationQueryStringSchema(OpenAPISchema):
    """Parameters and validators for accept invitation request query string."""

    my_endpoint = fields.Str(
        required=False,
        validate=ENDPOINT_VALIDATE,
        metadata={"description": "My URL endpoint", "example": ENDPOINT_EXAMPLE},
    )
    my_label = fields.Str(
        required=False,
        metadata={"description": "Label for connection", "example": "Broker"},
    )
    mediation_id = fields.Str(
        required=False,
        validate=UUID4_VALIDATE,
        metadata={
            "description": "Identifier for active mediation record to be used",
            "example": UUID4_EXAMPLE,
        },
    )


class AcceptRequestQueryStringSchema(OpenAPISchema):
    """Parameters and validators for accept conn-request web-request query string."""

    my_endpoint = fields.Str(
        required=False,
        validate=ENDPOINT_VALIDATE,
        metadata={"description": "My URL endpoint", "example": ENDPOINT_EXAMPLE},
    )


class ConnectionsConnIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    conn_id = fields.Str(
        required=True,
        metadata={"description": "Connection identifier", "example": UUID4_EXAMPLE},
    )


class ConnIdRefIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection and ref ids."""

    conn_id = fields.Str(
        required=True,
        metadata={"description": "Connection identifier", "example": UUID4_EXAMPLE},
    )

    ref_id = fields.Str(
        required=True,
        metadata={
            "description": "Inbound connection identifier",
            "example": UUID4_EXAMPLE,
        },
    )


class EndpointsResultSchema(OpenAPISchema):
    """Result schema for connection endpoints."""

    my_endpoint = fields.Str(
        validate=ENDPOINT_VALIDATE,
        metadata={"description": "My endpoint", "example": ENDPOINT_EXAMPLE},
    )
    their_endpoint = fields.Str(
        validate=ENDPOINT_VALIDATE,
        metadata={"description": "Their endpoint", "example": ENDPOINT_EXAMPLE},
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
    tags=["connection-v2"],
    summary="Query agent-to-agent connections",
)
@querystring_schema(ConnectionsListQueryStringSchema())
@response_schema(ConnectionListSchema(), 200, description="")
@tenant_authentication
async def connections_list(request: web.BaseRequest):
    """Request handler for searching connection records.

    Args:
        request: aiohttp request object

    Returns:
        The connection list response

    """
    context: AdminRequestContext = request["context"]

    tag_filter = {}
    for param_name in (
        "invitation_id",
        "my_did",
        "their_did",
        "request_id",
        "invitation_key",
        "their_public_did",
        "invitation_msg_id",
    ):
        if param_name in request.query and request.query[param_name] != "":
            tag_filter[param_name] = request.query[param_name]

    post_filter = {}
    if request.query.get("alias"):
        post_filter["alias"] = request.query["alias"]
    if request.query.get("state"):
        post_filter["state"] = list(ConnRecord.State.get(request.query["state"]).value)
    if request.query.get("their_role"):
        post_filter["their_role"] = list(
            ConnRecord.Role.get(request.query["their_role"]).value
        )
    if request.query.get("connection_protocol"):
        post_filter["connection_protocol"] = request.query["connection_protocol"]

    limit, offset = get_limit_offset(request)

    profile = context.profile
    try:
        async with profile.session() as session:
            records = await PeerwiseRecord.query(
                session,
                tag_filter,
                limit=limit,
                offset=offset,
                post_filter_positive=post_filter,
                alt=True,
            )
        results = [record.serialize() for record in records]
        #results.sort(key=connection_sort_key)
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"results": results})


@docs(tags=["connection-v2"], summary="Fetch a single connection record")
@match_info_schema(ConnectionsConnIdMatchInfoSchema())
@response_schema(ConnRecordSchema(), 200, description="")
@tenant_authentication
async def connections_retrieve(request: web.BaseRequest):
    """Request handler for fetching a single connection record.

    Args:
        request: aiohttp request object

    Returns:
        The connection record response

    """
    context: AdminRequestContext = request["context"]
    connection_id = request.match_info["conn_id"]

    profile = context.profile
    try:
        async with profile.session() as session:
            record = await PeerwiseRecord.retrieve_by_id(session, connection_id)
        result = record.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except BaseModelError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(result)


@docs(tags=["connection-v2"], summary="Fetch connection remote endpoint")
@match_info_schema(ConnectionsConnIdMatchInfoSchema())
@response_schema(EndpointsResultSchema(), 200, description="")
@tenant_authentication
async def connections_endpoints(request: web.BaseRequest):
    """Request handler for fetching connection endpoints.

    Args:
        request: aiohttp request object

    Returns:
        The endpoints response

    """
    context: AdminRequestContext = request["context"]
    connection_id = request.match_info["conn_id"]

    profile = context.profile
    connection_mgr = ConnectionManager(profile)
    try:
        endpoints = await connection_mgr.get_endpoints(connection_id)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (BaseModelError, StorageError, WalletError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(dict(zip(("my_endpoint", "their_endpoint"), endpoints)))


@docs(
    tags=["connection-v2"],
    summary="Accept a stored connection request",
    deprecated=True,
)
@match_info_schema(ConnectionsConnIdMatchInfoSchema())
@querystring_schema(AcceptRequestQueryStringSchema())
@response_schema(ConnRecordSchema(), 200, description="")
@tenant_authentication
async def connections_accept_request(request: web.BaseRequest):
    """Request handler for accepting a stored connection request.

    Args:
        request: aiohttp request object

    Returns:
        The resulting connection record details

    """
    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]
    connection_id = request.match_info["conn_id"]

    profile = context.profile
    try:
        async with profile.session() as session:
            connection = await ConnRecord.retrieve_by_id(session, connection_id)
        connection_mgr = ConnectionManager(profile)
        my_endpoint = request.query.get("my_endpoint") or None
        response = await connection_mgr.create_response(connection, my_endpoint)
        result = connection.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (StorageError, WalletError, ConnectionManagerError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(response, connection_id=connection.connection_id)
    return web.json_response(result)


@docs(tags=["connection-v2"], summary="Remove an existing connection record")
@match_info_schema(ConnectionsConnIdMatchInfoSchema())
@response_schema(ConnectionModuleResponseSchema, 200, description="")
@tenant_authentication
async def connections_remove(request: web.BaseRequest):
    """Request handler for removing a connection record.

    Args:
        request: aiohttp request object
    """
    context: AdminRequestContext = request["context"]
    connection_id = request.match_info["conn_id"]
    profile = context.profile

    try:
        async with profile.session() as session:
            connection = await PeerwiseRecord.retrieve_by_id(session, connection_id)
            await connection.delete_record(session)
            cache = session.inject_or(BaseCache)
            if cache:
                await cache.clear(f"conn_rec_state::{connection_id}")
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except StorageError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})


@docs(tags=["connection-v2"], summary="Create a new static connection")
@request_schema(ConnectionStaticRequestSchema())
@response_schema(ConnectionStaticResultSchema(), 200, description="")
@tenant_authentication
async def connections_create_static(request: web.BaseRequest):
    """Request handler for creating a new static connection.

    Args:
        request: aiohttp request object

    Returns:
        The new connection record

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()

    profile = context.profile
    connection_mgr = ConnectionManager(profile)
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
            web.get("/connections-v2", connections_list, allow_head=False),
            web.get("/connections-v2/{conn_id}", connections_retrieve, allow_head=False),
            web.get(
                "/connections-v2/{conn_id}/endpoints",
                connections_endpoints,
                allow_head=False,
            ),
            web.post("/connections-v2/create-static", connections_create_static),
            web.delete("/connections-v2/{conn_id}", connections_remove),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "connection-v2",
            "description": "Connection management V2",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
