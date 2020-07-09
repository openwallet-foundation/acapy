"""Credential schema admin routes."""

from asyncio import shield

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
    form_schema,
)

from marshmallow import fields, Schema
from marshmallow.validate import Regexp

from ...issuer.base import BaseIssuer, IssuerError
from ...ledger.base import BaseLedger
from ...ledger.error import LedgerError
from ...storage.base import BaseStorage
from ..valid import B58, NATURAL_NUM, INDY_SCHEMA_ID, INDY_VERSION
from .util import SchemaQueryStringSchema, SCHEMA_SENT_RECORD_TYPE, SCHEMA_TAGS


class UploadTailsFileRequestSchema(Schema):
    """Request schema for schema send request."""

    schema_name = fields.File
    schema_version = fields.Str(
        required=True, description="Schema version", **INDY_VERSION
    )
    attributes = fields.List(
        fields.Str(description="attribute name", example="score",),
        required=True,
        description="List of schema attributes",
    )


@docs(tags=["tails"], summary="Uploads a tails file to configured tails server")
@form_schema(UploadTailsFileRequestSchema())
# @response_schema(SchemaSendResultsSchema(), 200)
async def tails_file_upload(request: web.BaseRequest):
    """
    Request handler for sending a credential offer.

    Args:
        request: aiohttp request object

    Returns:
        The schema id sent

    """
    context = request.app["request_context"]

    body = await request.json()

    schema_name = body.get("schema_name")
    schema_version = body.get("schema_version")
    attributes = body.get("attributes")

    ledger: BaseLedger = await context.inject(BaseLedger, required=False)
    if not ledger:
        reason = "No ledger available"
        if not context.settings.get_value("wallet.type"):
            reason += ": missing wallet-type?"
        raise web.HTTPForbidden(reason=reason)

    issuer: BaseIssuer = await context.inject(BaseIssuer)
    async with ledger:
        try:
            schema_id, schema_def = await shield(
                ledger.create_and_send_schema(
                    issuer, schema_name, schema_version, attributes
                )
            )
        except (IssuerError, LedgerError) as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"schema_id": schema_id, "schema": schema_def})


async def register(app: web.Application):
    """Register routes."""
    app.add_routes([web.post("/tails-files/{id}", tails_file_upload)])
