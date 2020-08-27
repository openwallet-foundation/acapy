"""Holder admin routes."""

import json

from aiohttp import web
from aiohttp_apispec import docs, match_info_schema, querystring_schema, response_schema
from marshmallow import fields

from .base import BaseHolder, HolderError
from ..messaging.models.openapi import OpenAPISchema
from ..messaging.valid import (
    INDY_CRED_DEF_ID,
    INDY_REV_REG_ID,
    INDY_SCHEMA_ID,
    INDY_WQL,
    NATURAL_NUM,
    WHOLE_NUM,
    UUIDFour,
)
from ..wallet.error import WalletNotFoundError


class AttributeMimeTypesResultSchema(OpenAPISchema):
    """Result schema for credential attribute MIME type."""


class RawEncCredAttrSchema(OpenAPISchema):
    """Credential attribute schema."""

    raw = fields.Str(description="Raw value", example="Alex")
    encoded = fields.Str(
        description="(Numeric string) encoded value",
        example="412821674062189604125602903860586582569826459817431467861859655321",
    )


class RevRegSchema(OpenAPISchema):
    """Revocation registry schema."""

    accum = fields.Str(
        description="Revocation registry accumulator state",
        example="21 136D54EA439FC26F03DB4b812 21 123DE9F624B86823A00D ...",
    )


class WitnessSchema(OpenAPISchema):
    """Witness schema."""

    omega = fields.Str(
        description="Revocation registry witness omega state",
        example="21 129EA8716C921058BB91826FD 21 8F19B91313862FE916C0 ...",
    )


class CredentialSchema(OpenAPISchema):
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


class CredentialsListSchema(OpenAPISchema):
    """Result schema for a credential query."""

    results = fields.List(fields.Nested(CredentialSchema()))


class CredentialsListQueryStringSchema(OpenAPISchema):
    """Parameters and validators for query string in credentials list query."""

    start = fields.Int(
        description="Start index",
        required=False,
        **WHOLE_NUM,
    )
    count = fields.Int(
        description="Maximum number to retrieve",
        required=False,
        **NATURAL_NUM,
    )
    wql = fields.Str(
        description="(JSON) WQL query",
        required=False,
        **INDY_WQL,
    )


class CredIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking credential id."""

    credential_id = fields.Str(
        description="Credential identifier", required=True, example=UUIDFour.EXAMPLE
    )


@docs(tags=["credentials"], summary="Fetch a credential from wallet by id")
@match_info_schema(CredIdMatchInfoSchema())
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

    credential_id = request.match_info["credential_id"]

    holder: BaseHolder = await context.inject(BaseHolder)
    try:
        credential = await holder.get_credential(credential_id)
    except WalletNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    credential_json = json.loads(credential)
    return web.json_response(credential_json)


@docs(tags=["credentials"], summary="Get attribute MIME types from wallet")
@match_info_schema(CredIdMatchInfoSchema())
@response_schema(AttributeMimeTypesResultSchema(), 200)
async def credentials_attr_mime_types_get(request: web.BaseRequest):
    """
    Request handler for getting credential attribute MIME types.

    Args:
        request: aiohttp request object

    Returns:
        The MIME types response

    """
    context = request.app["request_context"]
    credential_id = request.match_info["credential_id"]
    holder: BaseHolder = await context.inject(BaseHolder)

    return web.json_response(await holder.get_mime_type(credential_id))


@docs(tags=["credentials"], summary="Remove a credential from the wallet by id")
@match_info_schema(CredIdMatchInfoSchema())
async def credentials_remove(request: web.BaseRequest):
    """
    Request handler for searching connection records.

    Args:
        request: aiohttp request object

    Returns:
        The connection list response

    """
    context = request.app["request_context"]

    credential_id = request.match_info["credential_id"]

    holder: BaseHolder = await context.inject(BaseHolder)
    try:
        await holder.delete_credential(credential_id)
    except WalletNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    return web.json_response({})


@docs(
    tags=["credentials"],
    summary="Fetch credentials from wallet",
)
@querystring_schema(CredentialsListQueryStringSchema())
@response_schema(CredentialsListSchema(), 200)
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
    try:
        credentials = await holder.get_credentials(start, count, wql)
    except HolderError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"results": credentials})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/credential/{credential_id}", credentials_get, allow_head=False),
            web.get(
                "/credential/mime-types/{credential_id}",
                credentials_attr_mime_types_get,
                allow_head=False,
            ),
            web.post("/credential/{credential_id}/remove", credentials_remove),
            web.get("/credentials", credentials_list, allow_head=False),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "credentials",
            "description": "Holder credential management",
            "externalDocs": {
                "description": "Overview",
                "url": ("https://w3c.github.io/vc-data-model/#credentials"),
            },
        }
    )
