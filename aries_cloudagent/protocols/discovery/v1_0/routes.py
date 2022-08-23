"""Feature discovery admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, response_schema
from marshmallow import fields

from ....admin.request_context import AdminRequestContext
from ....messaging.models.base import BaseModelError
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import UUIDFour
from ....storage.error import StorageNotFoundError, StorageError

from .manager import V10DiscoveryMgr
from .message_types import SPEC_URI
from .models.discovery_record import (
    V10DiscoveryExchangeRecord,
    V10DiscoveryRecordSchema,
)


class V10DiscoveryExchangeListResultSchema(OpenAPISchema):
    """Result schema for Discover Features v1.0 exchange records."""

    results = fields.List(
        fields.Nested(
            V10DiscoveryRecordSchema,
            description="Discover Features v1.0 exchange record",
        )
    )


class QueryFeaturesQueryStringSchema(OpenAPISchema):
    """Query string parameters for feature query."""

    query = fields.Str(
        description="Protocol feature query", required=False, example="*"
    )
    comment = fields.Str(description="Comment", required=False, example="test")
    connection_id = fields.Str(
        description=(
            "Connection identifier, if none specified, "
            "then the query will provide features for this agent."
        ),
        example=UUIDFour.EXAMPLE,
        required=False,
    )


class QueryDiscoveryExchRecordsSchema(OpenAPISchema):
    """Query string parameter for Discover Features v1.0 exchange record."""

    connection_id = fields.Str(
        description="Connection identifier",
        example=UUIDFour.EXAMPLE,
        required=False,
    )


@docs(
    tags=["discover-features"],
    summary="Query supported features",
)
@querystring_schema(QueryFeaturesQueryStringSchema())
@response_schema(V10DiscoveryRecordSchema(), 200, description="")
async def query_features(request: web.BaseRequest):
    """
    Request handler for creating and sending feature query.

    Args:
        request: aiohttp request object

    Returns:
        V10DiscoveryExchangeRecord

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile
    mgr = V10DiscoveryMgr(profile)
    query = request.query.get("query", "*")
    comment = request.query.get("comment", "*")
    connection_id = request.query.get("connection_id")
    result = await mgr.create_and_send_query(
        connection_id=connection_id,
        query=query,
        comment=comment,
    )
    return web.json_response(result.serialize())


@docs(
    tags=["discover-features"],
    summary="Discover Features records",
)
@querystring_schema(QueryDiscoveryExchRecordsSchema())
@response_schema(V10DiscoveryExchangeListResultSchema(), 200, description="")
async def query_records(request: web.BaseRequest):
    """
    Request handler for looking up V10DiscoveryExchangeRecord.

    Args:
        request: aiohttp request object

    Returns:
        List of V10DiscoveryExchangeRecord

    """
    context: AdminRequestContext = request["context"]
    connection_id = request.query.get("connection_id")
    if not connection_id:
        try:
            async with context.profile.session() as session:
                records = await V10DiscoveryExchangeRecord.query(session=session)
            results = [record.serialize() for record in records]
        except (StorageError, BaseModelError) as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err
    else:
        try:
            async with context.profile.session() as session:
                record = await V10DiscoveryExchangeRecord.retrieve_by_connection_id(
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
            web.get("/discover-features/query", query_features, allow_head=False),
            web.get("/discover-features/records", query_records, allow_head=False),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "discover-features",
            "description": "Feature discovery",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
