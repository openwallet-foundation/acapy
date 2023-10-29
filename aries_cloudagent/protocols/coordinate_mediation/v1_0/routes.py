"""coordinate mediation admin routes."""

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)

from marshmallow import fields, validate

from ....admin.request_context import AdminRequestContext
from ....connections.models.conn_record import ConnRecord
from ....messaging.models.base import BaseModelError
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import UUID4_EXAMPLE
from ....storage.error import StorageError, StorageNotFoundError
from ...connections.v1_0.routes import ConnectionsConnIdMatchInfoSchema
from ...routing.v1_0.models.route_record import RouteRecord, RouteRecordSchema
from .manager import MediationManager, MediationManagerError
from .message_types import SPEC_URI
from .messages.inner.keylist_update_rule import (
    KeylistUpdateRule,
    KeylistUpdateRuleSchema,
)
from .messages.keylist_query import KeylistQuerySchema
from .messages.keylist_update import KeylistUpdateSchema
from .messages.mediate_deny import MediationDenySchema
from .messages.mediate_grant import MediationGrantSchema
from .models.mediation_record import MediationRecord, MediationRecordSchema
from .route_manager import RouteManager

CONNECTION_ID_SCHEMA = fields.UUID(
    required=False,
    metadata={
        "description": "Connection identifier (optional)",
        "example": UUID4_EXAMPLE,
    },
)


MEDIATION_ID_SCHEMA = fields.UUID(
    metadata={"description": "Mediation record identifier", "example": UUID4_EXAMPLE},
)


MEDIATION_STATE_SCHEMA = fields.Str(
    required=False,
    validate=validate.OneOf(
        [
            getattr(MediationRecord, m)
            for m in vars(MediationRecord)
            if m.startswith("STATE_")
        ]
    ),
    metadata={
        "description": "Mediation state (optional)",
        "example": MediationRecord.STATE_GRANTED,
    },
)


MEDIATOR_TERMS_SCHEMA = fields.List(
    fields.Str(
        metadata={
            "description": (
                "Indicate terms to which the mediator requires the recipient to agree"
            )
        }
    ),
    required=False,
    metadata={"description": "List of mediator rules for recipient"},
)


RECIPIENT_TERMS_SCHEMA = fields.List(
    fields.Str(
        metadata={
            "description": (
                "Indicate terms to which the recipient requires the mediator to agree"
            )
        }
    ),
    required=False,
    metadata={"description": "List of recipient rules for mediation"},
)


class MediationListSchema(OpenAPISchema):
    """Result schema for mediation list query."""

    results = fields.List(
        fields.Nested(MediationRecordSchema),
        metadata={"description": "List of mediation records"},
    )


class MediationListQueryStringSchema(OpenAPISchema):
    """Parameters and validators for mediation record list request query string."""

    conn_id = CONNECTION_ID_SCHEMA
    mediator_terms = MEDIATOR_TERMS_SCHEMA
    recipient_terms = RECIPIENT_TERMS_SCHEMA
    state = MEDIATION_STATE_SCHEMA


class MediationCreateRequestSchema(OpenAPISchema):
    """Parameters and validators for create Mediation request query string."""

    mediator_terms = MEDIATOR_TERMS_SCHEMA
    recipient_terms = RECIPIENT_TERMS_SCHEMA


class AdminMediationDenySchema(OpenAPISchema):
    """Parameters and validators for Mediation deny admin request query string."""

    mediator_terms = MEDIATOR_TERMS_SCHEMA
    recipient_terms = RECIPIENT_TERMS_SCHEMA


class MediationIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking mediation request id."""

    mediation_id = MEDIATION_ID_SCHEMA


class GetKeylistQuerySchema(OpenAPISchema):
    """Get keylist query string paramaters."""

    conn_id = CONNECTION_ID_SCHEMA
    role = fields.Str(
        validate=validate.OneOf(
            [MediationRecord.ROLE_CLIENT, MediationRecord.ROLE_SERVER]
        ),
        load_default=MediationRecord.ROLE_SERVER,
        required=False,
        metadata={
            "description": (
                f"Filer on role, '{MediationRecord.ROLE_CLIENT}' for keys     mediated"
                f" by other agents, '{MediationRecord.ROLE_SERVER}' for keys    "
                " mediated by this agent"
            )
        },
    )


class KeylistSchema(OpenAPISchema):
    """Result schema for mediation list query."""

    results = fields.List(
        fields.Nested(RouteRecordSchema),
        metadata={"description": "List of keylist records"},
    )


class KeylistQueryFilterRequestSchema(OpenAPISchema):
    """Request schema for keylist query filtering."""

    filter = fields.Dict(
        required=False, metadata={"description": "Filter for keylist query"}
    )


class KeylistQueryPaginateQuerySchema(OpenAPISchema):
    """Query string schema for keylist query pagination."""

    paginate_limit = fields.Int(
        required=False,
        load_default=-1,
        metadata={"description": "limit number of results"},
    )
    paginate_offset = fields.Int(
        required=False,
        load_default=0,
        metadata={"description": "offset to use in pagination"},
    )


class KeylistUpdateRequestSchema(OpenAPISchema):
    """keylist update request schema."""

    updates = fields.List(fields.Nested(KeylistUpdateRuleSchema()))


def mediation_sort_key(mediation: dict):
    """Get the sorting key for a particular serialized mediation record."""
    if mediation["state"] == MediationRecord.STATE_DENIED:
        pfx = "2"
    elif mediation["state"] == MediationRecord.STATE_REQUEST:
        pfx = "1"
    else:  # GRANTED
        pfx = "0"
    return pfx + mediation["created_at"]


@docs(
    tags=["mediation"],
    summary="Query mediation requests, returns list of all mediation records",
)
@querystring_schema(MediationListQueryStringSchema())
@response_schema(MediationListSchema(), 200)
async def list_mediation_requests(request: web.BaseRequest):
    """List mediation requests for either client or server role."""
    context: AdminRequestContext = request["context"]
    conn_id = request.query.get("conn_id")
    state = request.query.get("state")

    tag_filter = {}
    if conn_id:
        tag_filter["connection_id"] = conn_id
    if state:
        tag_filter["state"] = state

    try:
        async with context.profile.session() as session:
            records = await MediationRecord.query(session, tag_filter)
        results = [record.serialize() for record in records]
        results.sort(key=mediation_sort_key)
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response({"results": results})


@docs(tags=["mediation"], summary="Retrieve mediation request record")
@match_info_schema(MediationIdMatchInfoSchema())
@response_schema(MediationRecordSchema(), 200)
async def retrieve_mediation_request(request: web.BaseRequest):
    """Retrieve a single mediation request."""
    context: AdminRequestContext = request["context"]

    mediation_id = request.match_info["mediation_id"]
    try:
        async with context.profile.session() as session:
            mediation_record = await MediationRecord.retrieve_by_id(
                session, mediation_id
            )
        result = mediation_record.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (BaseModelError, StorageError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(result)


@docs(tags=["mediation"], summary="Delete mediation request by ID")
@match_info_schema(MediationIdMatchInfoSchema())
@response_schema(MediationRecordSchema, 200)
async def delete_mediation_request(request: web.BaseRequest):
    """Delete a mediation request by ID."""
    context: AdminRequestContext = request["context"]

    mediation_id = request.match_info["mediation_id"]
    try:
        async with context.profile.session() as session:
            mediation_record = await MediationRecord.retrieve_by_id(
                session, mediation_id
            )
        result = mediation_record.serialize()
        async with context.profile.session() as session:
            await mediation_record.delete_record(session)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (BaseModelError, StorageError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(result)


@docs(tags=["mediation"], summary="Request mediation from connection")
@match_info_schema(ConnectionsConnIdMatchInfoSchema())
@request_schema(MediationCreateRequestSchema())
@response_schema(MediationRecordSchema(), 201)
async def request_mediation(request: web.BaseRequest):
    """Request mediation from connection."""
    context: AdminRequestContext = request["context"]
    profile = context.profile
    outbound_message_router = request["outbound_message_router"]

    conn_id = request.match_info["conn_id"]

    body = await request.json()
    mediator_terms = body.get("mediator_terms")
    recipient_terms = body.get("recipient_terms")

    try:
        async with profile.session() as session:
            connection_record = await ConnRecord.retrieve_by_id(session, conn_id)

        if not connection_record.is_ready:
            raise web.HTTPBadRequest(reason="requested connection is not ready")

        async with profile.session() as session:
            if await MediationRecord.exists_for_connection_id(session, conn_id):
                raise web.HTTPBadRequest(
                    reason=f"MediationRecord already exists for connection {conn_id}"
                )

        mediation_record, mediation_request = await MediationManager(
            profile
        ).prepare_request(
            connection_id=conn_id,
            mediator_terms=mediator_terms,
            recipient_terms=recipient_terms,
        )

        result = mediation_record.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_message_router(mediation_request, connection_id=conn_id)

    return web.json_response(result, status=201)


@docs(tags=["mediation"], summary="Grant received mediation")
@match_info_schema(MediationIdMatchInfoSchema())
@response_schema(MediationGrantSchema(), 201)
async def mediation_request_grant(request: web.BaseRequest):
    """Grant a stored mediation request."""
    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]
    mediation_id = request.match_info.get("mediation_id")
    try:
        mediation_mgr = MediationManager(context.profile)
        record, grant_request = await mediation_mgr.grant_request(
            mediation_id=mediation_id
        )
        result = record.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (MediationManagerError, StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    await outbound_handler(grant_request, connection_id=record.connection_id)
    return web.json_response(result, status=201)


@docs(tags=["mediation"], summary="Deny a stored mediation request")
@match_info_schema(MediationIdMatchInfoSchema())
@request_schema(AdminMediationDenySchema())
@response_schema(MediationDenySchema(), 201)
async def mediation_request_deny(request: web.BaseRequest):
    """Deny a stored mediation request."""
    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]
    mediation_id = request.match_info.get("mediation_id")
    body = await request.json()
    mediator_terms = body.get("mediator_terms")
    recipient_terms = body.get("recipient_terms")
    try:
        mediation_manager = MediationManager(context.profile)
        record, deny_request = await mediation_manager.deny_request(
            mediation_id=mediation_id,
            mediator_terms=mediator_terms,
            recipient_terms=recipient_terms,
        )
        result = record.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (MediationManagerError, StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(deny_request, connection_id=record.connection_id)
    return web.json_response(result, status=201)


@docs(
    tags=["mediation"],
    summary="Retrieve keylists by connection or role",
)
@querystring_schema(GetKeylistQuerySchema())
@response_schema(KeylistSchema(), 200)
async def get_keylist(request: web.BaseRequest):
    """Retrieve keylists by connection or role."""
    context: AdminRequestContext = request["context"]
    connection_id = request.query.get("conn_id")
    role = request.query.get("role")

    tag_filter = {}
    if connection_id:
        tag_filter["connection_id"] = connection_id
    if role:
        tag_filter["role"] = role

    try:
        async with context.profile.session() as session:
            keylists = await RouteRecord.query(session, tag_filter)
        results = [record.serialize() for record in keylists]
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response({"results": results}, status=200)


@docs(
    tags=["mediation"],
    summary="Send keylist query to mediator",
)
@match_info_schema(MediationIdMatchInfoSchema())
@querystring_schema(KeylistQueryPaginateQuerySchema())
@request_schema(KeylistQueryFilterRequestSchema())
@response_schema(KeylistQuerySchema(), 201)
async def send_keylist_query(request: web.BaseRequest):
    """Send keylist query to mediator."""
    context: AdminRequestContext = request["context"]
    profile = context.profile
    outbound_handler = request["outbound_message_router"]

    mediation_id = request.match_info["mediation_id"]

    body = await request.json()
    filter_ = body.get("filter")

    paginate_limit = request.query.get("paginate_limit")
    paginate_offset = request.query.get("paginate_offset")

    try:
        async with profile.session() as session:
            record = await MediationRecord.retrieve_by_id(session, mediation_id)
        mediation_manager = MediationManager(profile)
        keylist_query_request = await mediation_manager.prepare_keylist_query(
            filter_=filter_,
            paginate_limit=paginate_limit,
            paginate_offset=paginate_offset,
        )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(keylist_query_request, connection_id=record.connection_id)
    return web.json_response(keylist_query_request.serialize(), status=201)


@docs(tags=["mediation"], summary="Send keylist update to mediator")
@match_info_schema(MediationIdMatchInfoSchema())
@request_schema(KeylistUpdateRequestSchema())
@response_schema(KeylistUpdateSchema(), 201)
async def send_keylist_update(request: web.BaseRequest):
    """Send keylist update to mediator."""
    context: AdminRequestContext = request["context"]
    profile = context.profile

    outbound_handler = request["outbound_message_router"]

    mediation_id = request.match_info["mediation_id"]

    body = await request.json()
    updates = body.get("updates")

    if not updates:
        raise web.HTTPBadRequest(reason="Updates cannot be empty.")

    mediation_mgr = MediationManager(profile)
    keylist_updates = None
    for update in updates:
        if update.get("action") == KeylistUpdateRule.RULE_ADD:
            keylist_updates = await mediation_mgr.add_key(
                update.get("recipient_key"), keylist_updates
            )
        elif update.get("action") == KeylistUpdateRule.RULE_REMOVE:
            keylist_updates = await mediation_mgr.remove_key(
                update.get("recipient_key"), keylist_updates
            )
        else:
            raise web.HTTPBadRequest(reason="Invalid action for keylist update.")

    try:
        async with profile.session() as session:
            record = await MediationRecord.retrieve_by_id(session, mediation_id)
        if record.state != MediationRecord.STATE_GRANTED:
            raise web.HTTPBadRequest(reason="mediation is not granted.")
        results = keylist_updates.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    await outbound_handler(keylist_updates, connection_id=record.connection_id)
    return web.json_response(results, status=201)


@docs(tags=["mediation"], summary="Get default mediator")
@response_schema(MediationRecordSchema(), 200)
async def get_default_mediator(request: web.BaseRequest):
    """Get default mediator."""
    context: AdminRequestContext = request["context"]
    try:
        default_mediator = await MediationManager(
            context.profile
        ).get_default_mediator()
        results = default_mediator.serialize() if default_mediator else {}
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response(results, status=200)


@docs(tags=["mediation"], summary="Set default mediator")
@match_info_schema(MediationIdMatchInfoSchema())
@response_schema(MediationRecordSchema(), 201)
async def set_default_mediator(request: web.BaseRequest):
    """Set default mediator."""
    context: AdminRequestContext = request["context"]
    mediation_id = request.match_info.get("mediation_id")
    try:
        mediator_mgr = MediationManager(context.profile)
        await mediator_mgr.set_default_mediator_by_id(mediation_id=mediation_id)
        default_mediator = await mediator_mgr.get_default_mediator()
        results = default_mediator.serialize() if default_mediator else {}
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response(results, status=201)


@docs(tags=["mediation"], summary="Clear default mediator")
@response_schema(MediationRecordSchema(), 201)
async def clear_default_mediator(request: web.BaseRequest):
    """Clear set default mediator."""
    context: AdminRequestContext = request["context"]
    try:
        mediator_mgr = MediationManager(context.profile)
        default_mediator = await mediator_mgr.get_default_mediator()
        await mediator_mgr.clear_default_mediator()
        results = default_mediator.serialize() if default_mediator else {}
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response(results, status=201)


@docs(tags=["mediation"], summary="Update keylist for a connection")
@match_info_schema(ConnectionsConnIdMatchInfoSchema())
@request_schema(MediationIdMatchInfoSchema())
# TODO Fix this response so that it adequately represents Optionals
@response_schema(KeylistUpdateSchema(), 200)
async def update_keylist_for_connection(request: web.BaseRequest):
    """Update keylist for a connection."""
    context: AdminRequestContext = request["context"]
    body = await request.json()
    mediation_id = body.get("mediation_id")
    connection_id = request.match_info["conn_id"]
    try:
        route_manager = context.inject(RouteManager)

        async with context.session() as session:
            connection_record = await ConnRecord.retrieve_by_id(session, connection_id)
            mediation_record = await route_manager.mediation_record_for_connection(
                context.profile, connection_record, mediation_id, or_default=True
            )

        # MediationRecord is permitted to be None; route manager will
        # ensure the correct mediator is notified.
        keylist_update = await route_manager.route_connection(
            context.profile, connection_record, mediation_record
        )

        results = keylist_update.serialize() if keylist_update else {}
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(results, status=200)


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/mediation/requests", list_mediation_requests, allow_head=False),
            web.get(
                "/mediation/requests/{mediation_id}",
                retrieve_mediation_request,
                allow_head=False,
            ),
            web.delete("/mediation/requests/{mediation_id}", delete_mediation_request),
            web.post(
                "/mediation/requests/{mediation_id}/grant",
                mediation_request_grant,
            ),
            web.post("/mediation/requests/{mediation_id}/deny", mediation_request_deny),
            web.post("/mediation/request/{conn_id}", request_mediation),
            web.get("/mediation/keylists", get_keylist, allow_head=False),
            web.post(
                "/mediation/keylists/{mediation_id}/send-keylist-update",
                send_keylist_update,
            ),
            web.post(
                "/mediation/keylists/{mediation_id}/send-keylist-query",
                send_keylist_query,
            ),
            web.get(
                "/mediation/default-mediator", get_default_mediator, allow_head=False
            ),
            web.put("/mediation/{mediation_id}/default-mediator", set_default_mediator),
            web.delete("/mediation/default-mediator", clear_default_mediator),
            web.post(
                "/mediation/update-keylist/{conn_id}", update_keylist_for_connection
            ),
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
            "description": "Mediation management",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
