"""coordinate mediation admin routes."""

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

from .models.mediation_record import MediationRecord, MediationRecordSchema


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
from .messages.connection_Mediation import (
    ConnectionMediation,
    ConnectionMediationSchema,
)
from aries_cloudagent.protocols.routing.v1_0.models.route_record import RouteRecordSchema


class MediationKeyListSchema(OpenAPISchema):
    """Result schema for mediation key list."""

    results = fields.List(
        fields.Nested(RouteRecordSchema()),
        description="List of mediation records",
    )


class MediationRequestSchema(MediationRequestSchema):
    """Request schema for Mediation request."""

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Bypass middleware field validation."""


class MediationGrantSchema(OpenAPISchema):
    """Result schema for a granted Mediation."""

    # connection_id = fields.Str(
    #     description="Connection identifier", example=UUIDFour.EXAMPLE
    # )
    # Mediation = fields.Nested(ConnectionMediationSchema())
    # Mediation_url = fields.Str(
    #     description="Mediation URL",
    #     example="http://192.168.56.101:8020/invite?c_i=eyJAdHlwZSI6Li4ufQ==",
    # )

class MediationDenySchema(OpenAPISchema):
    """Result schema for a denied Mediation."""

    # connection_id = fields.Str(
    #     description="Connection identifier", example=UUIDFour.EXAMPLE
    # )
    # Mediation = fields.Nested(ConnectionMediationSchema())
    # Mediation_url = fields.Str(
    #     description="Mediation URL",
    #     example="http://192.168.56.101:8020/invite?c_i=eyJAdHlwZSI6Li4ufQ==",
    # )

# class ConnectionStaticRequestSchema(OpenAPISchema):
#     """Request schema for a new static connection."""

#     my_seed = fields.Str(description="Seed to use for the local DID", required=False)
#     my_did = fields.Str(description="Local DID", required=False, **INDY_DID)
#     their_seed = fields.Str(
#         description="Seed to use for the remote DID", required=False
#     )
#     their_did = fields.Str(description="Remote DID", required=False, **INDY_DID)
#     their_verkey = fields.Str(description="Remote verification key", required=False)
#     their_endpoint = fields.Str(
#         description="URL endpoint for the other party", required=False, **ENDPOINT
#     )
#     their_role = fields.Str(
#         description="Role to assign to this connection",
#         required=False,
#         example="Point of contact",
#     )
#     their_label = fields.Str(
#         description="Label to assign to this connection", required=False
#     )
#     alias = fields.Str(description="Alias to assign to this connection", required=False)


# class ConnectionStaticResultSchema(OpenAPISchema):
#     """Result schema for new static connection."""

#     my_did = fields.Str(description="Local DID", required=True, **INDY_DID)
#     mv_verkey = fields.Str(
#         description="My verification key", required=True, **INDY_RAW_PUBLIC_KEY
#     )
#     my_endpoint = fields.Str(description="My URL endpoint", required=True, **ENDPOINT)
#     their_did = fields.Str(description="Remote DID", required=True, **INDY_DID)
#     their_verkey = fields.Str(
#         description="Remote verification key", required=True, **INDY_RAW_PUBLIC_KEY
#     )
#     record = fields.Nested(ConnectionRecordSchema, required=True)


class MediationsListQueryStringSchema(OpenAPISchema):
    """Parameters and validators for mediation record list request query string."""

    alias = fields.Str(
        description="Alias",
        required=False,
        example="Barry",
    )
    initiator = fields.Str(
        description="mediation initiator",
        required=False,
        validate=validate.OneOf(["self", "external"]),
    )
    Mediation_key = fields.Str(
        description="Mediation key", required=False, **INDY_RAW_PUBLIC_KEY
    )
    #my_did = fields.Str(description="My DID", required=False, **INDY_DID)
    state = fields.Str(
        description="Mediation state",
        required=False,
        validate=validate.OneOf(
            [
                getattr(MediationRecord, m)
                for m in vars(MediationRecord)
                if m.startswith("STATE_")
            ]
        ),
    )
    their_did = fields.Str(description="Their DID", required=False, **INDY_DID)
    # their_role = fields.Str(
    #     description="Their assigned connection role",
    #     required=False,
    #     example="Point of contact",
    # )


class CreateMediationQueryStringSchema(OpenAPISchema):
    """Parameters and validators for create Mediation request query string."""

    alias = fields.Str(
        description="Alias",
        required=False,
        example="Barry",
    )
    auto_accept = fields.Boolean(
        description="Auto-accept connection (default as per configuration)",
        required=False,
    )
    public = fields.Boolean(
        description="Create Mediation from public DID (default false)", required=False
    )
    multi_use = fields.Boolean(
        description="Create Mediation for multiple use (default false)", required=False
    )


class ReceiveMediationQueryStringSchema(OpenAPISchema):
    """Parameters and validators for receive Mediation request query string."""

    alias = fields.Str(
        description="Alias",
        required=False,
        example="Barry",
    )
    auto_accept = fields.Boolean(
        description="Auto-accept connection (defaults to configuration)",
        required=False,
    )


class AcceptMediationQueryStringSchema(OpenAPISchema):
    """Parameters and validators for accept Mediation request query string."""

    my_endpoint = fields.Str(description="My URL endpoint", required=False, **ENDPOINT)
    my_label = fields.Str(
        description="Label for connection", required=False, example="Broker"
    )


class AcceptRequestQueryStringSchema(OpenAPISchema):
    """Parameters and validators for accept conn-request web-request query string."""

    my_endpoint = fields.Str(description="My URL endpoint", required=False, **ENDPOINT)


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
    if conn["state"] == ConnectionRecord.STATE_INACTIVE:
        pfx = "2"
    elif conn["state"] == ConnectionRecord.STATE_Mediation:
        pfx = "1"
    else:
        pfx = "0"
    return pfx + conn["created_at"]


@docs(
    tags=["connection"],
    summary="Query agent-to-agent connections",
)
@querystring_schema(MediationsListQueryStringSchema())
@response_schema(ConnectionListSchema(), 200)
async def mediations_record_list(request: web.BaseRequest):
    """
    Request handler for searching mediation records.

    Args:
        request: aiohttp request object

    Returns:
        The mediation list response

    """
    context = request.app["request_context"]
    tag_filter = {}
    for param_name in (
        "Mediation_id",
        "my_did",
        "their_did",
        "request_id",
    ):
        if param_name in request.query and request.query[param_name] != "":
            tag_filter[param_name] = request.query[param_name]
    post_filter = {}
    for param_name in (
        "alias",
        "initiator",
        "state",
        "their_role",
    ):
        if param_name in request.query and request.query[param_name] != "":
            post_filter[param_name] = request.query[param_name]
    try:
        records = await ConnectionRecord.query(context, tag_filter, post_filter)
        results = [record.serialize() for record in records]
        results.sort(key=connection_sort_key)
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response({"results": results})


@docs(tags=["connection"], summary="Fetch a single connection record")
@match_info_schema(ConnIdMatchInfoSchema())
@response_schema(ConnectionRecordSchema(), 200)
async def mediations_retrieve(request: web.BaseRequest):
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
        record = await ConnectionRecord.retrieve_by_id(context, connection_id)
        result = record.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except BaseModelError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(result)


@docs(
    tags=["connection"],
    summary="Create a new connection Mediation",
)
@querystring_schema(CreateMediationQueryStringSchema())
@response_schema(MediationResultSchema(), 200)
async def request-Mediation(request: web.BaseRequest):
    """
    Request handler for creating a new connection Mediation.

    Args:
        request: aiohttp request object

    Returns:
        The connection Mediation details

    """
    context = request.app["request_context"]
    auto_accept = json.loads(request.query.get("auto_accept", "null"))
    alias = request.query.get("alias")
    public = json.loads(request.query.get("public", "false"))
    multi_use = json.loads(request.query.get("multi_use", "false"))

    if public and not context.settings.get("public_invites"):
        raise web.HTTPForbidden(
            reason="Configuration does not include public Mediations"
        )
    base_url = context.settings.get("invite_base_url")

    connection_mgr = ConnectionManager(context)
    try:
        (connection, Mediation) = await connection_mgr.create_Mediation(
            auto_accept=auto_accept, public=public, multi_use=multi_use, alias=alias
        )

        result = {
            "connection_id": connection and connection.connection_id,
            "Mediation": Mediation.serialize(),
            "Mediation_url": Mediation.to_url(base_url),
        }
    except (ConnectionManagerError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    if connection and connection.alias:
        result["alias"] = connection.alias

    return web.json_response(result)


@docs(
    tags=["connection"],
    summary="Receive a new connection Mediation",
)
@querystring_schema(ReceiveMediationQueryStringSchema())
@request_schema(ReceiveMediationRequestSchema())
@response_schema(ConnectionRecordSchema(), 200)
async def connections_receive_Mediation(request: web.BaseRequest):
    """
    Request handler for receiving a new connection Mediation.

    Args:
        request: aiohttp request object

    Returns:
        The resulting connection record details

    """
    context = request.app["request_context"]
    if context.settings.get("admin.no_receive_invites"):
        raise web.HTTPForbidden(
            reason="Configuration does not allow receipt of Mediations"
        )
    connection_mgr = ConnectionManager(context)
    Mediation_json = await request.json()

    try:
        Mediation = ConnectionMediation.deserialize(Mediation_json)
        auto_accept = json.loads(request.query.get("auto_accept", "null"))
        alias = request.query.get("alias")
        connection = await connection_mgr.receive_Mediation(
            Mediation, auto_accept=auto_accept, alias=alias
        )
        result = connection.serialize()
    except (ConnectionManagerError, StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(result)


@docs(
    tags=["connection"],
    summary="Accept a stored connection Mediation",
)
@match_info_schema(ConnIdMatchInfoSchema())
@querystring_schema(AcceptMediationQueryStringSchema())
@response_schema(ConnectionRecordSchema(), 200)
async def connections_grant_Mediation(request: web.BaseRequest):
    """
    Request handler for accepting a stored connection Mediation.

    Args:
        request: aiohttp request object

    Returns:
        The resulting connection record details

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    connection_id = request.match_info["conn_id"]

    try:
        connection = await ConnectionRecord.retrieve_by_id(context, connection_id)
        connection_mgr = ConnectionManager(context)
        my_label = request.query.get("my_label") or None
        my_endpoint = request.query.get("my_endpoint") or None
        request = await connection_mgr.create_request(connection, my_label, my_endpoint)
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
@response_schema(ConnectionRecordSchema(), 200)
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
        connection = await ConnectionRecord.retrieve_by_id(context, connection_id)
        connection_mgr = ConnectionManager(context)
        my_endpoint = request.query.get("my_endpoint") or None
        response = await connection_mgr.create_response(connection, my_endpoint)
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
        connection = await ConnectionRecord.retrieve_by_id(context, connection_id)
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
        connection = await ConnectionRecord.retrieve_by_id(context, connection_id)
        await connection.delete_record(context)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except StorageError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})


# @docs(tags=["connection"], summary="Create a new static connection")
# @request_schema(ConnectionStaticRequestSchema())
# @response_schema(ConnectionStaticResultSchema(), 200)
# async def connections_create_static(request: web.BaseRequest):
#     """
#     Request handler for creating a new static connection.

#     Args:
#         request: aiohttp request object

#     Returns:
#         The new connection record

#     """
    # context = request.app["request_context"]
    # body = await request.json()

    # connection_mgr = ConnectionManager(context)
    # try:
    #     (
    #         my_info,
    #         their_info,
    #         connection,
    #     ) = await connection_mgr.create_static_connection(
    #         my_seed=body.get("my_seed") or None,
    #         my_did=body.get("my_did") or None,
    #         their_seed=body.get("their_seed") or None,
    #         their_did=body.get("their_did") or None,
    #         their_verkey=body.get("their_verkey") or None,
    #         their_endpoint=body.get("their_endpoint") or None,
    #         their_role=body.get("their_role") or None,
    #         their_label=body.get("their_label") or None,
    #         alias=body.get("alias") or None,
    #     )
    #     response = {
    #         "my_did": my_info.did,
    #         "my_verkey": my_info.verkey,
    #         "my_endpoint": context.settings.get("default_endpoint"),
    #         "their_did": their_info.did,
    #         "their_verkey": their_info.verkey,
    #         "record": connection.serialize(),
    #     }
    # except (WalletError, StorageError, BaseModelError) as err:
    #     raise web.HTTPBadRequest(reason=err.roll_up) from err

    # return web.json_response(response)


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/mediations", mediations_record_list, allow_head=False),
            web.get("/mediations/{conn_id}", mediations_retrieve, allow_head=False),
            web.get("/mediations/keylist", mediations_keylist, allow_head=False),
            web.get("/mediations/keylist/{conn_id}", mediations_keylist_retrieve, allow_head=False),
            web.post("/mediations/request-Mediation/{conn_id}", request-Mediation),
            web.post("/mediations/keylist-update/{conn_id}", keylist_update_Mediation),
            web.post(
                "/mediations/{conn_id}/grant-Mediation",
                connections_grant_Mediation,
            ),
            web.post("/mediations/{conn_id}/remove", connections_remove),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "mediation",
            "description": "mediation management",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
