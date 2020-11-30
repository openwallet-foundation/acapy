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

from marshmallow import fields

from ....connections.models.conn_record import ConnRecord, ConnRecordSchema
from ....messaging.models.base import BaseModelError
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import ENDPOINT, UUIDFour
from ....storage.error import StorageError, StorageNotFoundError
from ....wallet.error import WalletError

from ...out_of_band.v1_0.messages.invitation import (
    InvitationMessage as OOBInvitation,
    InvitationMessageSchema as OOBInvitationSchema,
)

from .manager import DIDXManager, DIDXManagerError
from .message_types import SPEC_URI


'''
class DIDXConnListSchema(OpenAPISchema):
    """Result schema for connection list."""

    results = fields.List(
        fields.Nested(ConnRecordSchema()),
        description="List of connection records",
    )
'''


class DIDXReceiveInvitationRequestSchema(OOBInvitationSchema):
    """Request schema for receive invitation request."""

    service = fields.Field()


'''
class DIDXConnStaticRequestSchema(OpenAPISchema):
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


class DIDXConnStaticResultSchema(OpenAPISchema):
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
'''


'''
class DIDXConnsListQueryStringSchema(OpenAPISchema):
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
        required=False,
        description="Their assigned connection role",
        validate=validate.OneOf(  # conn rec role values include names by rfcs 23, 160
            [label for role in ConnRecord.Role for label in role.value]
        ),
        example=ConnRecord.Role.REQUESTER.rfc23,
    )
'''


class DIDXReceiveInvitationQueryStringSchema(OpenAPISchema):
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


class DIDXAcceptInvitationQueryStringSchema(OpenAPISchema):
    """Parameters and validators for accept invitation request query string."""

    my_endpoint = fields.Str(description="My URL endpoint", required=False, **ENDPOINT)
    my_label = fields.Str(
        description="Label for connection", required=False, example="Broker"
    )


class DIDXAcceptRequestQueryStringSchema(OpenAPISchema):
    """Parameters and validators for accept conn-request web-request query string."""

    my_endpoint = fields.Str(description="My URL endpoint", required=False, **ENDPOINT)


class DIDXConnIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    conn_id = fields.Str(
        description="Connection identifier", required=True, example=UUIDFour.EXAMPLE
    )


class DIDXConnIdRefIdMatchInfoSchema(OpenAPISchema):
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
    conn_state = ConnRecord.State.get(conn["state"])
    if conn_state in (
        ConnRecord.State.INIT,
        ConnRecord.State.ABANDONED,
    ):
        pfx = "2"
    elif conn_state is ConnRecord.State.INVITATION:
        pfx = "1"
    else:
        pfx = "0"
    return pfx + conn["created_at"]


'''
@docs(
    tags=["did-exchange"],
    summary="Query agent-to-agent connections",
)
@querystring_schema(DIDXConnsListQueryStringSchema())
@response_schema(DIDXConnListSchema(), 200)
async def didx_connections_list(request: web.BaseRequest):
    """
    Request handler for searching DID exchange connection records.

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
            context, tag_filter, post_filter_positive=post_filter, alt=True
        )
        results = [record.serialize() for record in records]
        results.sort(key=connection_sort_key)
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"results": results})


@docs(tags=["did-exchange"], summary="Fetch a single connection record")
@match_info_schema(DIDXConnIdMatchInfoSchema())
@response_schema(ConnRecordSchema(), 200)
async def didx_retrieve_connection(request: web.BaseRequest):
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
'''


@docs(
    tags=["did-exchange"],
    summary="Receive a new connection invitation",
)
@querystring_schema(DIDXReceiveInvitationQueryStringSchema())
@request_schema(DIDXReceiveInvitationRequestSchema())
@response_schema(ConnRecordSchema(), 200)
async def didx_receive_invitation(request: web.BaseRequest):
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
    didx_mgr = DIDXManager(context)
    invitation_json = await request.json()

    try:
        invitation = OOBInvitation.deserialize(invitation_json)
        auto_accept = json.loads(request.query.get("auto_accept", "null"))
        alias = request.query.get("alias")
        conn_rec = await didx_mgr.receive_invitation(
            invitation,
            auto_accept=auto_accept,
            alias=alias,
        )
        result = conn_rec.serialize()
    except (DIDXManagerError, StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(result)


@docs(
    tags=["did-exchange"],
    summary="Accept a stored connection invitation",
)
@match_info_schema(DIDXConnIdMatchInfoSchema())
@querystring_schema(DIDXAcceptInvitationQueryStringSchema())
@response_schema(ConnRecordSchema(), 200)
async def didx_accept_invitation(request: web.BaseRequest):
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
        conn_rec = await ConnRecord.retrieve_by_id(context, connection_id)
        didx_mgr = DIDXManager(context)
        my_label = request.query.get("my_label") or None
        my_endpoint = request.query.get("my_endpoint") or None
        request = await didx_mgr.create_request(conn_rec, my_label, my_endpoint)
        result = conn_rec.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (StorageError, WalletError, DIDXManagerError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(request, connection_id=conn_rec.connection_id)

    return web.json_response(result)


@docs(
    tags=["did-exchange"],
    summary="Accept a stored connection request",
)
@match_info_schema(DIDXConnIdMatchInfoSchema())
@querystring_schema(DIDXAcceptRequestQueryStringSchema())
@response_schema(ConnRecordSchema(), 200)
async def didx_accept_request(request: web.BaseRequest):
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
        conn_rec = await ConnRecord.retrieve_by_id(context, connection_id)
        didx_mgr = DIDXManager(context)
        my_endpoint = request.query.get("my_endpoint") or None
        response = await didx_mgr.create_response(conn_rec, my_endpoint)
        result = conn_rec.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (StorageError, WalletError, DIDXManagerError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    # TODO check if conn rec state is correct here? Maybe pass outbound into conn mgr
    await outbound_handler(response, connection_id=conn_rec.connection_id)
    return web.json_response(result)


'''
@docs(
    tags=["did-exchange"], summary="Assign another connection as the inbound connection"
)
@match_info_schema(DIDXConnIdRefIdMatchInfoSchema())
async def didx_establish_inbound(request: web.BaseRequest):
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
        conn_rec = await ConnRecord.retrieve_by_id(context, connection_id)
        didx_mgr = DIDXManager(context)
        await didx_mgr.establish_inbound(
            conn_rec, inbound_connection_id, outbound_handler
        )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (StorageError, WalletError, DIDXManagerError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})
'''


'''
@docs(tags=["did-exchange"], summary="Remove an existing connection record")
@match_info_schema(DIDXConnIdMatchInfoSchema())
async def didx_remove_connection(request: web.BaseRequest):
    """
    Request handler for removing a connection record.

    Args:
        request: aiohttp request object
    """
    context = request.app["request_context"]
    connection_id = request.match_info["conn_id"]

    try:
        conn_rec = await ConnRecord.retrieve_by_id(context, connection_id)
        await conn_rec.delete_record(context)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except StorageError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})
'''


'''
@docs(tags=["did-exchange"], summary="Create a new static connection")
@request_schema(DIDXConnStaticRequestSchema())
@response_schema(DIDXConnStaticResultSchema(), 200)
async def didx_create_static(request: web.BaseRequest):
    """
    Request handler for creating a new static connection.

    Args:
        request: aiohttp request object

    Returns:
        The new connection record

    """
    context = request.app["request_context"]
    body = await request.json()

    didx_mgr = DIDXManager(context)
    try:
        (my_info, their_info, conn_rec,) = await didx_mgr.create_static_connection(
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
            "record": conn_rec.serialize(),
        }
    except (WalletError, StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(response)
'''


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            # web.get(
            #     "/didexchange/connections",
            #     didx_connections_list,
            #     allow_head=False,
            # ),
            # web.get(
            #     "/didexchange/connections/{conn_id}",
            #     didx_retrieve_connection,
            #     allow_head=False,
            # ),
            # web.post("/didexchange/create-static", didx_create_static),
            web.post("/didexchange/receive-invitation", didx_receive_invitation),
            web.post(
                "/didexchange/{conn_id}/accept-invitation",
                didx_accept_invitation,
            ),
            web.post("/didexchange/{conn_id}/accept-request", didx_accept_request),
            # web.post(
            #     "/didexchange/{conn_id}/establish-inbound/{ref_id}",
            #     didx_establish_inbound,
            # ),
            # web.post("/didexchange/{conn_id}/remove", didx_remove_connection),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "did-exchange",
            "description": "Connection management via DID exchange",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
