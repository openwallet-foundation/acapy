"""Feature discovery v2 admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, response_schema

from marshmallow import fields

from ....admin.request_context import AdminRequestContext
from ....messaging.models.base import BaseModelError
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import UUID4_EXAMPLE
from ....storage.error import StorageError, StorageNotFoundError
from .manager import V20DiscoveryMgr
from .message_types import SPEC_URI
from .models.discovery_record import (
    V20DiscoveryExchangeRecord,
    V20DiscoveryRecordSchema,
)


class V20DiscoveryExchangeResultSchema(OpenAPISchema):
    """Result schema for Discover Features v2.0 exchange record."""

    results = fields.Nested(
        V20DiscoveryRecordSchema,
        metadata={"description": "Discover Features v2.0 exchange record"},
    )


class V20DiscoveryExchangeListResultSchema(OpenAPISchema):
    """Result schema for Discover Features v2.0 exchange records."""

    results = fields.List(
        fields.Nested(
            V20DiscoveryRecordSchema,
            metadata={"description": "Discover Features v2.0 exchange record"},
        )
    )


class QueryFeaturesQueryStringSchema(OpenAPISchema):
    """Query string parameters for feature query."""

    query_protocol = fields.Str(
        required=False,
        metadata={"description": "Protocol feature-type query", "example": "*"},
    )
    query_goal_code = fields.Str(
        required=False,
        metadata={"description": "Goal-code feature-type query", "example": "*"},
    )
    connection_id = fields.Str(
        required=False,
        metadata={
            "description": (
                "Connection identifier, if none specified, then the query will provide"
                " features for this agent."
            ),
            "example": UUID4_EXAMPLE,
        },
    )


class QueryDiscoveryExchRecordsSchema(OpenAPISchema):
    """Query string parameter for Discover Features v2.0 exchange record."""

    connection_id = fields.Str(
        required=False,
        metadata={"description": "Connection identifier", "example": UUID4_EXAMPLE},
    )


@docs(
    tags=["discover-features v2.0"],
    summary="Query supported features",
)
@querystring_schema(QueryFeaturesQueryStringSchema())
@response_schema(V20DiscoveryExchangeResultSchema(), 200, description="")
async def query_features(request: web.BaseRequest):
    """
    Request handler for creating and sending feature queries.

    Args:
        request: aiohttp request object

    Returns:
        V20DiscoveryExchangeRecord

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile
    mgr = V20DiscoveryMgr(profile)
    query_protocol = request.query.get("query_protocol", "*")
    query_goal_code = request.query.get("query_goal_code", "*")
    connection_id = request.query.get("connection_id")
    result = await mgr.create_and_send_query(
        connection_id=connection_id,
        query_protocol=query_protocol,
        query_goal_code=query_goal_code,
    )
    return web.json_response(result.serialize())


@docs(
    tags=["discover-features v2.0"],
    summary="Discover Features v2.0 records",
)
@querystring_schema(QueryDiscoveryExchRecordsSchema())
@response_schema(V20DiscoveryExchangeListResultSchema(), 200, description="")
async def query_records(request: web.BaseRequest):
    """
    Request handler for looking up V20DiscoveryExchangeRecord.

    Args:
        request: aiohttp request object

    Returns:
        List of V20DiscoveryExchangeRecord

    """
    context: AdminRequestContext = request["context"]
    connection_id = request.query.get("connection_id")
    if not connection_id:
        try:
            async with context.profile.session() as session:
                records = await V20DiscoveryExchangeRecord.query(session=session)
            results = [record.serialize() for record in records]
        except (StorageError, BaseModelError) as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err
    else:
        try:
            async with context.profile.session() as session:
                record = await V20DiscoveryExchangeRecord.retrieve_by_connection_id(
                    session=session, connection_id=connection_id
                )
            # There should only be one record for a connection
            results = [record.serialize()]
        except (StorageError, BaseModelError, StorageNotFoundError) as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response({"results": results})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/discover-features-2.0/queries", query_features, allow_head=False),
            web.get("/discover-features-2.0/records", query_records, allow_head=False),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "discover-features v2.0",
            "description": "Feature discovery v2",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
