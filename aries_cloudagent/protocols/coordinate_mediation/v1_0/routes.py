"""coordinate mediation admin routes."""

# https://github.com/hyperledger/aries-rfcs/tree/master/features/0211-route-coordination#0211-mediator-coordination-protocol

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)

from marshmallow import fields, validate

from .models.mediation_record import (MediationRecord,
                                      MediationRecordSchema,
                                      )
from .models.mediation_schemas import (CONNECTION_ID_SCHEMA,
                                       MEDIATION_ID_SCHEMA,
                                       MEDIATION_STATE_SCHEMA,
                                       MEDIATOR_TERMS_SCHEMA,
                                       RECIPIENT_TERMS_SCHEMA,
                                       ROLE_SCHEMA
                                       # ENDPOINT_SCHEMA,
                                       # ROUTING_KEYS_SCHEMA
                                       )

from .messages.mediate_request import MediationRequest
from .messages.mediate_grant import MediationGrantSchema
from .messages.mediate_deny import MediationDenySchema
from .messages.keylist_update import KeylistUpdate
from .manager import MediationManager as M_Manager
from ....messaging.models.base import BaseModelError
from ....messaging.models.openapi import OpenAPISchema

from ...connections.v1_0.routes import (InvitationResultSchema)
from ...problem_report.v1_0 import internal_error
from ....storage.error import StorageError, StorageNotFoundError
from ....utils.tracing import get_timer

from .message_types import SPEC_URI
from operator import itemgetter
from .messages.inner.keylist_update_rule import KeylistUpdateRule
from .manager import MediationManager, MediationManagerError
from ...routing.v1_0.models.route_record import RouteRecord, RouteRecordSchema
from .messages.keylist_update_response import KeylistUpdateResponseSchema
from aries_cloudagent.wallet.base import BaseWallet, DIDInfo
import json
from ...connections.v1_0.manager import ConnectionManager, ConnectionManagerError
from ...connections.v1_0.routes import (
    AcceptInvitationQueryStringSchema,
    ConnRecordSchema,
    ReceiveInvitationRequestSchema
)
from ...connections.v1_0.messages.connection_invitation import ConnectionInvitation
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.connections.models.diddoc.diddoc import (DIDDoc,
                                                               PublicKey,
                                                               PublicKeyType,
                                                               Service,
                                                               )
from ...connections.v1_0.models.connection_detail import ConnectionDetail
from ....connections.models.conn_record import ConnRecord
from ...connections.v1_0.messages.connection_request import ConnectionRequest
from aries_cloudagent.wallet.error import WalletError


class CreateMediationInvitationQueryStringSchema(OpenAPISchema):
    """Parameters and validators for create invitation request query string."""

    alias = fields.Str(
        description="Alias",
        required=False,
        example="Barry",
    )
    auto_accept = fields.Boolean(
        description="Auto-accept connection (default as per configuration)",
        required=False,
    )
    multi_use = fields.Boolean(
        description="Create invitation for multiple use (default false)", required=False
    )


class MediationListSchema(OpenAPISchema):
    """Result schema for mediation list query."""

    results = fields.List(
        fields.Nested(MediationRecordSchema),
        description="List of mediation records",
    )


class MediationListQueryStringSchema(OpenAPISchema):
    """Parameters and validators for mediation record list request query string."""

    conn_id = CONNECTION_ID_SCHEMA
    mediator_terms = MEDIATOR_TERMS_SCHEMA
    recipient_terms = RECIPIENT_TERMS_SCHEMA
    state = MEDIATION_STATE_SCHEMA


class MediationCreateSchema(OpenAPISchema):
    """Parameters and validators for create Mediation request query string."""

    # conn_id = CONNECTION_ID_SCHEMA
    # mediation_id = MEDIATION_ID_SCHEMA
    # state = MEDIATION_STATE_SCHEMA
    role = ROLE_SCHEMA
    mediator_terms = MEDIATOR_TERMS_SCHEMA
    recipient_terms = RECIPIENT_TERMS_SCHEMA


class AdminMediationDenySchema(OpenAPISchema):
    """Parameters and validators for Mediation deny admin request query string."""

    # conn_id = CONNECTION_ID_SCHEMA
    # mediation_id = MEDIATION_ID_SCHEMA
    # state = MEDIATION_STATE_SCHEMA
    mediator_terms = MEDIATOR_TERMS_SCHEMA
    recipient_terms = RECIPIENT_TERMS_SCHEMA


class MediationIdSchema(OpenAPISchema):
    """Path parameters and validators for request taking mediation id."""

    mediation_id = MEDIATION_ID_SCHEMA


def mediation_sort_key(mediation):
    """Get the sorting key for a particular mediation."""
    if mediation["state"] == MediationRecord.STATE_DENIED:
        pfx = "2"
    elif mediation["state"] == MediationRecord.STATE_REQUEST_RECEIVED:
        pfx = "1"
    else:  # GRANTED
        pfx = "0"
    return pfx + mediation["created_at"]


async def _receive_request(context,
                           role,
                           conn_id,
                           mediator_terms,
                           recipient_terms
                           ) -> MediationRecord:
    if await MediationRecord.exists_for_connection_id(context, conn_id):
        raise MediationManagerError('Mediation Record already exists for connection')
    # TODO: Determine if terms are acceptable
    record = MediationRecord(
        role=role,
        connection_id=conn_id,
        mediator_terms=mediator_terms,
        recipient_terms=recipient_terms
    )
    await record.save(context, reason="New mediation request record",
                      webhook=True)
    return record


async def _prepare_handler(request: web.BaseRequest):
    # TODO: check that request origination point
    r_time = get_timer()
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    body = {}
    if request.body_exists:
        body = await request.json()
    if request.match_info:
        mediation_id = request.match_info.get("mediation_id") or body.get("mediation_id")
        conn_id = request.match_info.get("conn_id") or body.get("conn_id")
    else:
        mediation_id = body.get("mediation_id")
        conn_id = body.get("conn_id")
    state = body.get("state", "granted")
    mediator_terms = body.get("mediator_terms")
    recipient_terms = body.get("recipient_terms")
    role = body.get("role")
    results = {
        'r_time': r_time,
        'context': context,
        'outbound_handler': outbound_handler,
        'conn_id': conn_id,
        'mediation_id': mediation_id,
        'state': state,
        'mediator_terms': mediator_terms,
        'recipient_terms': recipient_terms,
        'role': role,
    }
    return results


@docs(
    tags=["mediation"],
    summary="Query mediation requests, returns list of all mediation records.",
)
@querystring_schema(MediationListQueryStringSchema())
@response_schema(MediationListSchema(), 200)  # TODO: return list of mediation reports
async def mediation_records_list(request: web.BaseRequest):
    """
    Request handler for searching mediation records.

    Args:
        request: aiohttp request object

    Returns:
        The mediation list response

    """
    context = request.app["request_context"]
    tag_filter = {}
    # "hack the main frame!"
    parameters = {"conn_id": "connection_id", "state": "state"}
    for param_name in parameters.keys():
        if param_name in request.query and request.query[param_name] != "":
            tag_filter[parameters[param_name]] = request.query[param_name]
    try:
        records = await MediationRecord.query(context, tag_filter)
        results = [record.serialize() for record in records]
        results.sort(key=mediation_sort_key)
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response(results)


class MediationIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking mediation request id."""

    mediation_id = MEDIATION_ID_SCHEMA


class ConnIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    conn_id = CONNECTION_ID_SCHEMA


@docs(tags=["mediation"], summary="mediation request, returns a single mediation record.")
@match_info_schema(MediationIdMatchInfoSchema())
@response_schema(MediationRecordSchema(), 200)  # TODO: return mediation report
async def mediation_record_retrieve(request: web.BaseRequest):
    """
    Request handler for fetching single mediation request record.

    Args:
        request: aiohttp request object

    Returns:
        The credential exchange record

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    _id = request.match_info["mediation_id"]
    try:
        _record = await MediationRecord.retrieve_by_id(
            context, _id
        )
        result = _record.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (BaseModelError, StorageError) as err:
        await internal_error(err, web.HTTPBadRequest, _record, outbound_handler)

    return web.json_response(result)


async def check_mediation_record(context, conn_id):
    """Check if connection has mediation, raise exception if exists."""
    try:
        record = await MediationRecord.retrieve_by_connection_id(
            context, conn_id
        )
    except StorageError:
        pass  # no mediation record found will raise a storage error.
        # which is the desired state
    else:
        raise web.HTTPBadRequest(
            reason=f"connection already has mediation"
            f"({record.mediation_id}) record associated.")


@docs(tags=["mediation"], summary="create mediation request record.")
@match_info_schema(ConnIdMatchInfoSchema())
@request_schema(MediationCreateSchema())
@response_schema(MediationRecordSchema(), 201)  # TODO: return mediation report
async def mediation_record_create(request: web.BaseRequest):
    """
    Request handler for creating a mediation record locally.

    The internal mediation record will be created without the request
    being sent to any connection. This can be used in conjunction with
    the `oob` protocols to bind messages to an out of band message.

    Args:
        request: aiohttp request object

    """
    args = ['r_time', 'context', 'conn_id', 'mediator_terms', 'recipient_terms', 'role']
    (r_time, context, conn_id, mediator_terms,
     recipient_terms, role) = itemgetter(*args)(await _prepare_handler(request))
    try:
        connection_record = await ConnRecord.retrieve_by_id(
            context, conn_id
        )
        if not connection_record.is_ready:
            raise web.HTTPBadRequest(
                reason="connection identifier must be from a valid connection.")
        await check_mediation_record(context, conn_id)
        _record = await _receive_request(
            context=context,
            role=role,
            conn_id=conn_id,
            mediator_terms=mediator_terms,
            recipient_terms=recipient_terms,
        )
        result = _record.serialize()
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response(result, status=201)


@docs(tags=["mediation"], summary="create and send mediation request.")
@match_info_schema(ConnIdMatchInfoSchema())
@request_schema(MediationCreateSchema())
@response_schema(MediationRecordSchema(), 201)  # TODO: return mediation report
async def mediation_record_send_create(request: web.BaseRequest):
    """
    Request handler for creating a mediation request record and sending.

    The internal mediation record will be created and a request
    sent to the connection.

    Args:
        request: aiohttp request object

    """
    args = ['r_time', 'context', 'outbound_handler', 'conn_id',
            'mediator_terms', 'recipient_terms']
    (r_time, context, outbound_handler, conn_id, mediator_terms,
     recipient_terms) = itemgetter(*args)(await _prepare_handler(request))
    try:
        connection_record = await ConnRecord.retrieve_by_id(
            context, conn_id
        )
        if not connection_record.is_ready:
            raise web.HTTPBadRequest(
                reason="connection identifier must be from a valid connection.")
        await check_mediation_record(context, conn_id)
        _manager = M_Manager(context)
        record, mediation_request = await _manager.prepare_request(
            connection_id=conn_id,
            mediator_terms=mediator_terms,
            recipient_terms=recipient_terms,
        )
        result = record.serialize()
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    await outbound_handler(
        mediation_request, connection_id=conn_id
    )
    return web.json_response(result, status=201)


@docs(tags=["mediation"], summary="create and send mediation request.")
@match_info_schema(MediationIdMatchInfoSchema())
@response_schema(MediationRecordSchema(), 201)  # TODO: return mediation report,
# if possible return the response from other server.
async def mediation_record_send(request: web.BaseRequest):
    """
    Request handler for sending a mediation request record.

    Args:
        request: aiohttp request object

    """
    args = ['r_time', 'context', 'outbound_handler',
            'mediation_id', 'mediator_terms', 'recipient_terms']
    (r_time, context, outbound_handler, _id, mediator_terms,
     recipient_terms) = itemgetter(*args)(await _prepare_handler(request))
    _record = None
    try:
        _record = await MediationRecord.retrieve_by_id(
            context, _id
        )
        _message = MediationRequest(mediator_terms=_record.mediator_terms,
                                    recipient_terms=_record.recipient_terms)
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    await outbound_handler(
        _message, connection_id=_record.connection_id
    )
    return web.json_response(_record.serialize(), status=201)


@docs(tags=["mediation"], summary="create invitation"
      "from mediation record.")
@match_info_schema(MediationIdMatchInfoSchema())
@querystring_schema(CreateMediationInvitationQueryStringSchema())
@response_schema(InvitationResultSchema(), 200)
async def create_invitation(request: web.BaseRequest):
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
    multi_use = json.loads(request.query.get("multi_use", "false"))
    base_url = context.settings.get("invite_base_url")

    args = ['context', 'outbound_handler',
            'mediation_id']
    (context, outbound_handler, _id) = itemgetter(*args)(await _prepare_handler(request))
    connection_mgr = ConnectionManager(context)
    try:
        _record = await MediationRecord.retrieve_by_id(
            context, _id
        )
        (connection, invitation) = await connection_mgr.create_invitation(
            auto_accept=auto_accept,
            multi_use=multi_use,
            alias=alias,
            recipient_keys=_record.recipient_keys,
            my_endpoint=_record.endpoint,
            routing_keys=_record.routing_keys,
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


# TODO: move this logic into connections

async def mediation_did_document(
    context,
    did_info: DIDInfo,
    connection: ConnRecord = None,
    mediation_record: MediationRecord = None
) -> DIDDoc:
    """Create DID document for connection request.

    Args:

    Returns:
        The prepared `DIDDoc` instance

    """
    recip_keys = []
    route_keys = []
    did_doc = DIDDoc(did=did_info.did)
    # did_controller = did_info.did
    # did_key = did_info.verkey
    # storage: BaseStorage = await context.inject(BaseStorage)
    wallet: BaseWallet = await context.inject(BaseWallet)
    for recipient_key in mediation_record.recipient_keys:
        # get did record for verkey.
        # record = await storage.find_record(
        # ConnectionManager.RECORD_TYPE_DID_DOC,
        # {"verkey": recipient_key}
        # )
        # TODO wrap in try/except
        did_info = await wallet.get_local_did_for_verkey(recipient_key)
        recip_key = PublicKey(
            did_info.did,
            "1",  # TODO: why one?
            did_info.verkey,
            PublicKeyType.ED25519_SIG_2018,
            did_info.did,
            True,
        )
        recip_keys.append(recip_key)

    for routing_key in mediation_record.routing_keys:
        # TODO: resolve did_dock for provided verkey
        route_key = PublicKey(
            did="55GkHamhTU1ZbTbV2ab9DE",  # fake! TODO: not provided from mediator
            ident="1",  # f"routing-{connection.id}",
            value=routing_key,
            pk_type=PublicKeyType.ED25519_SIG_2018,
            controller="55GkHamhTU1ZbTbV2ab9DE",  # fake! TODO: this is never provided
            authn=False,
        )
        route_keys.append(route_key)

    endpoint_ident = "indy"
    service = Service(
        did=did_info.did,
        ident=endpoint_ident,
        typ="IndyAgent",
        recip_keys=recip_keys,
        routing_keys=route_keys,
        endpoint=mediation_record.endpoint,
    )
    did_doc.set(service)

    return did_doc


# TODO: put into constructor?
async def connection_from_invitation(
    context,
    invitation: ConnectionInvitation,
    mediation_record: MediationRecord,
    alias: str = None
) -> ConnRecord:
    """
    Create a new connection record to track a received invitation.

    Args:
        context:
        invitation: The `ConnectionInvitation` to store
        mediation_record:
        alias: optional alias to set on the record

    Returns:
        The new `ConnRecord` instance

    """
    if not invitation.did:
        if not invitation.recipient_keys:
            raise ConnectionManagerError("Invitation must contain recipient key(s)")
        if not invitation.endpoint:
            raise ConnectionManagerError("Invitation must contain an endpoint")

    # Create connection record
    connection = ConnRecord(
        invitation_key=invitation.recipient_keys and invitation.recipient_keys[0],
        their_label=invitation.label,
        their_role=ConnRecord.Role.RESPONDER.rfc160,
        state=ConnRecord.State.INVITATION.rfc160,
        accept=True,
        alias=alias,
    )

    await connection.save(
        context,
        reason="Created new connection record from invitation",
        log_params={"invitation": invitation, "their_label": invitation.label},
    )

    # Save the invitation for later processing
    await connection.attach_invitation(context, invitation)

    return connection


async def create_request(
    context,
    connection: ConnRecord,
    invitation: ConnectionInvitation,
    mediation_record: MediationRecord
) -> ConnectionRequest:
    """
    Create a new connection request for a previously-received invitation.

    Args:
        connection: The `ConnRecord` representing the invitation to accept
        invitation:
        mediation_record:
        label: My label

    Returns:
        A new `ConnectionRequest` message to send to the other agent

    """
    wallet: BaseWallet = await context.inject(BaseWallet)
    my_info = await wallet.get_local_did_for_verkey(
        mediation_record.recipient_keys[0]
    )  # TODO wrap in try/except
    connection.my_did = my_info.did
    # Create connection request message
    did_doc = await mediation_did_document(
        context, my_info, connection, mediation_record)
    label = context.settings.get("default_label")
    request = ConnectionRequest(
        label=label,
        connection=ConnectionDetail(did=my_info.did, did_doc=did_doc),
    )

    # Update connection state
    connection.request_id = request._id
    connection.state = ConnRecord.State.REQUEST.rfc160

    await connection.save(context, reason="Created connection request")

    return request


@docs(tags=["mediation"], summary="accept connection invitation with mediator.")
@match_info_schema(MediationIdMatchInfoSchema())
@querystring_schema(AcceptInvitationQueryStringSchema())
@response_schema(ConnRecordSchema(), 200)
async def mediation_accept_invitation(request: web.BaseRequest):
    """
    Request handler for accepting a new connection invitation over a mediator.

    Args:
        request: aiohttp request object

    Returns:
        The connection invitation details

    """
    context = request.app["request_context"]
    if context.settings.get("admin.no_receive_invites"):
        raise web.HTTPForbidden(
            reason="Configuration does not allow receipt of invitations"
        )
    # invitation_json = await request.json()
    # auto_accept = json.loads(request.query.get("auto_accept", "null"))
    # alias = request.query.get("alias")
    args = ['context', 'outbound_handler', 'conn_id',
            'mediation_id']
    (context, outbound_handler,
        conn_id, _id) = itemgetter(*args)(await _prepare_handler(request))
    connection_mgr = ConnectionManager(context)
    try:
        mediation_record = await MediationRecord.retrieve_by_id(context, _id)
        connection = await ConnRecord.retrieve_by_id(context, conn_id)
        connection_mgr = ConnectionManager(context)
        # my_label = request.query.get("my_label") or None
        # my_endpoint = mediation_record.endpoint or None
        storage: BaseStorage = await context.inject(BaseStorage)
        result = await storage.find_record(
            connection_mgr.RECORD_TYPE_INVITATION, {"connection_id": conn_id}
        )
        ser = json.loads(result.value)
        invitation = ConnectionInvitation.deserialize(ser)
        request = await create_request(
            context,
            connection,
            invitation,
            mediation_record
        )
        await outbound_handler(request, connection_id=connection.connection_id)
        result = connection.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (StorageError, WalletError, ConnectionManagerError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response(result, 200)


@docs(
    tags=["mediation"],
    summary="Receive invitation with a mediator."
)
@match_info_schema(MediationIdMatchInfoSchema())
@request_schema(ReceiveInvitationRequestSchema())
@response_schema(ConnRecordSchema(), 201)
async def mediation_receive_invitation(request: web.BaseRequest):
    """
    Automatically receive a new connection invitation with mediation.

    Args:
        request: aiohttp request object

    Returns:
        The connection invitation details

    """
    context = request.app["request_context"]
    if context.settings.get("admin.no_receive_invites"):
        raise web.HTTPForbidden(
            reason="Configuration does not allow receipt of invitations"
        )
    invitation_json = await request.json()
    alias = request.query.get("alias")

    args = ['outbound_handler',
            'mediation_id']
    (outbound_handler, _id) = itemgetter(*args)(await _prepare_handler(request))
    try:
        mediation_record = await MediationRecord.retrieve_by_id(
            context, _id
        )
        invitation = ConnectionInvitation.deserialize(invitation_json)
        connection = await connection_from_invitation(
            context,
            invitation,
            mediation_record,
            alias=alias,
        )
        connection_request = await create_request(
            context,
            connection,
            invitation,
            mediation_record
        )
        await outbound_handler(
            connection_request, connection_id=connection.connection_id
        )
        result = connection.serialize()

    except (ConnectionManagerError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(result, status=201)


@docs(tags=["mediation"], summary="grant received mediation")
@match_info_schema(MediationIdMatchInfoSchema())
@response_schema(MediationGrantSchema(), 201)
async def mediation_record_grant(request: web.BaseRequest):
    """
    Request handler for granting a stored mediation record.

    Args:
        request: aiohttp request object
    """
    args = ['r_time', 'context', 'outbound_handler', 'mediation_id']
    (r_time, context, outbound_handler,
     _id) = itemgetter(*args)(await _prepare_handler(request))
    # TODO: check that request origination point
    _record = None
    try:
        _record = await MediationRecord.retrieve_by_id(
            context, _id
        )
        _manager = M_Manager(context)
        _record, _message = await _manager.grant_request(
            mediation=_record
        )
        result = _record.serialize()
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    await outbound_handler(
        _message,
        connection_id=_record.connection_id
    )
    return web.json_response(result, status=201)


@docs(tags=["mediation"], summary="deny a stored mediation request")
@match_info_schema(MediationIdMatchInfoSchema())
@request_schema(AdminMediationDenySchema())
@response_schema(MediationDenySchema(), 201)
async def mediation_record_deny(request: web.BaseRequest):
    """
    Request handler for denying a stored mediation record.

    Args:
        request: aiohttp request object
    """
    args = ['r_time', 'context', 'outbound_handler',
            'mediation_id', 'mediator_terms', 'recipient_terms']
    (r_time, context, outbound_handler, _id, mediator_terms,
     recipient_terms) = itemgetter(*args)(await _prepare_handler(request))
    # TODO: check that request origination point
    _record = None
    try:
        _record = await MediationRecord.retrieve_by_id(
            context, _id
        )
        _manager = M_Manager(context)
        _record, _message = await _manager.deny_request(mediation=_record)
        result = _message.serialize()
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    await outbound_handler(
        _message, connection_id=_record.connection_id
    )
    return web.json_response(result, status=201)


# class AllKeyListRecordsPagingSchema(OpenAPISchema):
#     """Parameters and validators for keylist record list query string."""

#     #filter = fields..... TODO: add filtering to handler
#     limit= fields.Integer(
#         description="Number of keylists in a single page.",
#         required=False,
#         example="5",
#     )
#     offset= fields.Integer(
#         description="Page to receive in pagination.",
#         required=False,
#         example="5",
#     )


class KeyListRecordListSchema(OpenAPISchema):
    """Result schema for mediation list query."""

    results = fields.List(  # TODO: order matters, should match sequence?
        fields.Nested(RouteRecordSchema),
        description="List of keylist records",
    )


class KeylistUpdateSchema(OpenAPISchema):
    """Routing key schema."""

    action = fields.Str(
        description="update actions",
        required=True,
        validate=validate.OneOf(
            [
                getattr(KeylistUpdateRule, m)
                for m in vars(KeylistUpdateRule)
                if m.startswith("RULE_")
            ]
        ),
        example="'add' or 'remove'",
    )
    key = fields.Str(
        description="Key to be acted on.",
        required=True,
    )


class KeylistUpdateRequestSchema(OpenAPISchema):
    """keylist update request schema."""

    updates = fields.List(
        fields.Nested(
            KeylistUpdateSchema()
        )
    )


class MediationIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking mediation request id."""

    mediation_id = MEDIATION_ID_SCHEMA


@docs(
    tags=["keylist"],
    summary="Query keylists, returns list of all keylist records.",
)
# @querystring_schema(AllRecordsQueryStringSchema()) # TODO: add filtering
@response_schema(KeyListRecordListSchema(), 200)
async def list_all_records(request: web.BaseRequest):
    """
    Request handler for searching keylist records.

    Args:
        request: aiohttp request object

    Returns:
        keylists

    """
    context = request.app["request_context"]
    try:
        records = await RouteRecord.query(context, {})
        results = [record.serialize() for record in records]
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response(results, status=200)


@docs(
    tags=["keylist"],
    summary="send Query keylists request, returns list of all keylist records.",
)
# @querystring_schema(AllRecordsQueryStringSchema()) # TODO: add filtering
@match_info_schema(MediationIdMatchInfoSchema())
@response_schema(KeyListRecordListSchema(), 200)
async def send_keylists_request(request: web.BaseRequest):
    """
    Request handler for searching keylist records.

    Args:
        request: aiohttp request object

    Returns:
        keylists

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"],
    mediation_id = request.match_info["mediation_id"]
    # TODO: add pagination to request
    try:
        record = await MediationRecord.retrieve_by_id(
            context, mediation_id
        )
        _manager = M_Manager(context)
        request = await _manager.prepare_keylist_query()
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    conn_id = record.connection_id
    await outbound_handler(
        request, connection_id=conn_id
    )
    return web.json_response(request, status=200)


@docs(tags=["keylist"], summary="update keylist.")
@match_info_schema(MediationIdMatchInfoSchema())
@request_schema(KeylistUpdateRequestSchema())
@response_schema(KeylistUpdateResponseSchema(), 201)
async def update_keylists(request: web.BaseRequest):
    """
    Request handler for updating keylist.

    Args:
        request: aiohttp request object
    """
    context = request.app["request_context"]
    mediation_id = request.match_info["mediation_id"]
    body = await request.json()
    updates = body.get("updates")
    # TODO: move this logic into controller.
    updates = [KeylistUpdateRule(
        recipient_key=update.get("key"),
        action=update.get("action")) for update in updates]
    try:
        record = await MediationRecord.retrieve_by_id(
            context, mediation_id
        )
        if record.state != MediationRecord.STATE_GRANTED:
            raise web.HTTPBadRequest(reason=("mediation is not granted."))
        mgr = MediationManager(context)
        response = await mgr.update_keylist(
            record, updates=updates
        )
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    # TODO: return updated record with update rules
    return web.json_response(response.serialize(), status=201)


@docs(tags=["keylist"], summary="update keylist.")
@match_info_schema(MediationIdMatchInfoSchema())
# @querystring_schema(KeylistUpdateRequestSchema())
@request_schema(KeylistUpdateRequestSchema())
@response_schema(KeylistUpdateResponseSchema(), 201)
async def send_update_keylists(request: web.BaseRequest):
    """
    Request handler for updating keylist.

    Args:
        request: aiohttp request object
    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    mediation_id = request.match_info["mediation_id"]
    body = await request.json()
    updates = body.get("updates")
    # TODO: move this logic into controller.
    updates = [KeylistUpdateRule(
        recipient_key=update.get("key"),
        action=update.get("action")) for update in updates]
    try:
        record = await MediationRecord.retrieve_by_id(
            context, mediation_id
        )
        if record.state != MediationRecord.STATE_GRANTED:
            raise web.HTTPBadRequest(reason=("mediation is not granted."))
        request = KeylistUpdate(updates=updates)
        results = request.serialize()
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    await outbound_handler(
        request, connection_id=record.connection_id
    )
    return web.json_response(results, status=201)


async def register(app: web.Application):
    """Register routes.

    record represents internal origin, request extrenal origin

    """

    app.add_routes(
        [
            web.get(
                "/mediation/requests",
                mediation_records_list,
                allow_head=False
            ),  # -> fetch all mediation request records
            web.get(
                "/mediation/requests/{mediation_id}",
                mediation_record_retrieve,
                allow_head=False
            ),  # . -> fetch a single mediation request record
            web.post(
                "/mediation/requests/{conn_id}/create",
                mediation_record_create
            ),
            web.post(
                "/mediation/requests/client/{conn_id}/create-send",
                mediation_record_send_create
            ),
            web.post(
                "/mediation/requests/client/{mediation_id}/create-invitation",
                create_invitation
            ),
            web.post(
                "/mediation/requests/client/{mediation_id}/receive-invitation",
                mediation_receive_invitation
            ),
            web.post(
                "/mediation/requests/client/{mediation_id}/accept-invitation",
                mediation_accept_invitation
            ),
            web.post(
                "/mediation/requests/client/{mediation_id}/send",
                mediation_record_send
            ),  # -> send mediation request
            web.post(
                "/mediation/requests/broker/{mediation_id}/grant",
                mediation_record_grant
            ),  # -> grant
            web.post(
                "/mediation/requests/broker/{mediation_id}/deny",
                mediation_record_deny
            ),  # -> deny
            # ======
            web.get("/mediation/keylists/broker",
                    list_all_records,
                    allow_head=False),
            # web.get("/keylists/records/pagination",
            #     list_all_records_paging,
            #     allow_head=False),
            # web.get("/keylists/records/{record_id}",
            #     keylist,
            #     allow_head=False),
            # web.get("/keylists/records/{record_id}/pagination",
            #     keylist,
            #     allow_head=False),
            web.post("/mediation/keylists/broker/{mediation_id}/update",
                     update_keylists),
            web.post("/mediation/keylists/client/{mediation_id}/update",
                     send_update_keylists),
            web.post("/mediation/keylists/client/{mediation_id}",
                     send_keylists_request),
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
