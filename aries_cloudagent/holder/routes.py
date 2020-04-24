"""Holder admin routes."""

import json

from aiohttp import web
from aiohttp_apispec import docs, response_schema
from marshmallow import fields, Schema

from .base import BaseHolder
from ..messaging.valid import INDY_CRED_DEF_ID, INDY_REV_REG_ID, INDY_SCHEMA_ID
from ..wallet.error import WalletNotFoundError


class RawEncCredAttrSchema(Schema):
    """Credential attribute schema."""

    raw = fields.Str(description="Raw value", example="Alex")
    encoded = fields.Str(
        description="(Numeric string) encoded value",
        example="412821674062189604125602903860586582569826459817431467861859655321",
    )


class RevRegSchema(Schema):
    """Revocation registry schema."""

    accum = fields.Str(
        description="Revocation registry accumulator state",
        example="21 136D54EA439FC26F03DB4b812 21 123DE9F624B86823A00D ...",
    )


class WitnessSchema(Schema):
    """Witness schema."""

    omega = fields.Str(
        description="Revocation registry witness omega state",
        example="21 129EA8716C921058BB91826FD 21 8F19B91313862FE916C0 ...",
    )


class CredentialSchema(Schema):
    """Result schema for a credential query."""

    schema_id = fields.Str(description="Schema identifier", **INDY_SCHEMA_ID)
    cred_def_id = fields.Str(
        description="Credential definition identifier", **INDY_CRED_DEF_ID
    )
    rev_reg_id = fields.Str(
        description="Revocation registry identifier", **INDY_REV_REG_ID
    )
    values = fields.Dict(
        keys=fields.Str(description="Attribute name"),
        values=fields.Nested(RawEncCredAttrSchema),
        description="Attribute names mapped to their raw and encoded values",
    )
    signature = fields.Dict(description="Digital signature")
    signature_correctness_proof = fields.Dict(description="Signature correctness proof")
    rev_reg = fields.Nested(RevRegSchema)
    witness = fields.Nested(WitnessSchema)


class CredentialListSchema(Schema):
    """Result schema for a credential query."""

    results = fields.List(fields.Nested(CredentialSchema()))


@docs(tags=["credentials"], summary="Fetch a credential from wallet by id")
@response_schema(CredentialSchema(), 200)
async def credentials_get(request: web.BaseRequest):
    """
    Request handler for retrieving a credential.

    Args:
        request: aiohttp request object

    Returns:
        The credential response

    """
    context = request.app["request_context"]

    credential_id = request.match_info["id"]

    holder: BaseHolder = await context.inject(BaseHolder)
    try:
        credential = await holder.get_credential(credential_id)
    except WalletNotFoundError:
        raise web.HTTPNotFound()

    credential_json = json.loads(credential)
    return web.json_response(credential_json)


@docs(tags=["credentials"], summary="Remove a credential from the wallet by id")
async def credentials_remove(request: web.BaseRequest):
    """
    Request handler for searching connection records.

    Args:
        request: aiohttp request object

    Returns:
        The connection list response

    """
    context = request.app["request_context"]

    credential_id = request.match_info["id"]

    holder: BaseHolder = await context.inject(BaseHolder)
    try:
        await holder.delete_credential(credential_id)
    except WalletNotFoundError:
        raise web.HTTPNotFound()

    return web.json_response({})


@docs(
    tags=["credentials"],
    parameters=[
        {
            "name": "start",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
        {
            "name": "count",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
        {"name": "wql", "in": "query", "schema": {"type": "string"}, "required": False},
    ],
    summary="Fetch credentials from wallet",
)
@response_schema(CredentialListSchema(), 200)
async def credentials_list(request: web.BaseRequest):
    """
    Request handler for searching credential records.

    Args:
        request: aiohttp request object

    Returns:
        The credential list response

    """
    context = request.app["request_context"]

    start = request.query.get("start")
    count = request.query.get("count")

    # url encoded json wql
    encoded_wql = request.query.get("wql") or "{}"
    wql = json.loads(encoded_wql)

    # defaults
    start = int(start) if isinstance(start, str) else 0
    count = int(count) if isinstance(count, str) else 10

    holder: BaseHolder = await context.inject(BaseHolder)
    credentials = await holder.get_credentials(start, count, wql)

    return web.json_response({"results": credentials})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/credential/{id}", credentials_get),
            web.post("/credential/{id}/remove", credentials_remove),
            web.get("/credentials", credentials_list),
        ]
    )
