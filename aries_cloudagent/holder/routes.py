"""Holder admin routes."""

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

from ..admin.request_context import AdminRequestContext
from ..indy.holder import IndyHolder, IndyHolderError
from ..ledger.base import BaseLedger
from ..ledger.error import LedgerError
from ..messaging.models.openapi import OpenAPISchema
from ..messaging.valid import (
    ENDPOINT,
    INDY_CRED_DEF_ID,
    INDY_CRED_REV_ID,
    INDY_REV_REG_ID,
    INDY_SCHEMA_ID,
    INDY_WQL,
    NUM_STR_NATURAL,
    NUM_STR_WHOLE,
    UUIDFour,
)
from ..storage.error import StorageError, StorageNotFoundError
from ..storage.vc_holder.base import VCHolder
from ..storage.vc_holder.vc_record import VCRecordSchema
from ..wallet.error import WalletNotFoundError


class HolderModuleResponseSchema(OpenAPISchema):
    """Response schema for Holder Module."""


class AttributeMimeTypesResultSchema(OpenAPISchema):
    """Result schema for credential attribute MIME type."""


class CredBriefSchema(OpenAPISchema):
    """Result schema with credential brief for credential query."""

    referent = fields.Str(description="Credential referent", example=UUIDFour.EXAMPLE)
    attrs = fields.Dict(
        keys=fields.Str(description="Attribute name"),
        values=fields.Str(description="Attribute value"),
        description="Attribute names mapped to their raw values",
    )
    schema_id = fields.Str(description="Schema identifier", **INDY_SCHEMA_ID)
    cred_def_id = fields.Str(
        description="Credential definition identifier", **INDY_CRED_DEF_ID
    )
    rev_reg_id = fields.Str(
        description="Revocation registry identifier", **INDY_REV_REG_ID
    )
    cred_rev_id = fields.Str(
        description="Credential revocation identifier", **INDY_CRED_REV_ID
    )


class CredBriefListSchema(OpenAPISchema):
    """Result schema for credential query."""

    results = fields.List(fields.Nested(CredBriefSchema()))


class CredentialsListQueryStringSchema(OpenAPISchema):
    """Parameters and validators for query string in credentials list query."""

    start = fields.Str(
        description="Start index",
        required=False,
        **NUM_STR_WHOLE,
    )
    count = fields.Str(
        description="Maximum number to retrieve",
        required=False,
        **NUM_STR_NATURAL,
    )
    wql = fields.Str(
        description="(JSON) WQL query",
        required=False,
        **INDY_WQL,
    )


class DIFCredentialsListRequestSchema(OpenAPISchema):
    """Parameters and validators for DIF credentials request."""

    contexts = fields.List(
        fields.Str(
            description="Credential context to match",
            **ENDPOINT,
        ),
        required=False,
    )
    types = fields.List(
        fields.Str(
            description="Credential type to match",
            **ENDPOINT,
        ),
        required=False,
    )
    schema_ids = fields.List(
        fields.Str(
            description="Credential schema identifier to match",
            **ENDPOINT,
        ),
        required=False,
    )
    issuer_id = fields.Str(
        required=False,
        description="Credential issuer identifier to match",
    )
    subject_id = fields.Str(
        required=False,
        description="Subject identifier to match",
    )
    tag_query = fields.Dict(
        keys=fields.Str(description="Tag name"),
        values=fields.Str(description="Tag value"),
        required=False,
        description="Tag filter",
    )
    max_results = fields.Int(
        strict=True, description="Maximum number of results to return", required=False
    )


class VCRecordListSchema(OpenAPISchema):
    """Result schema for DIF credential query."""

    results = fields.List(fields.Nested(VCRecordSchema()))


class CredIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking credential id."""

    credential_id = fields.Str(
        description="Credential identifier", required=True, example=UUIDFour.EXAMPLE
    )


class CredRevokedQueryStringSchema(OpenAPISchema):
    """Path parameters and validators for request seeking cred revocation status."""

    fro = fields.Str(
        data_key="from",
        description="Earliest epoch of revocation status interval of interest",
        required=False,
        **NUM_STR_WHOLE,
    )
    to = fields.Str(
        description="Latest epoch of revocation status interval of interest",
        required=False,
        **NUM_STR_WHOLE,
    )


class CredRevokedResultSchema(OpenAPISchema):
    """Result schema for credential revoked request."""

    revoked = fields.Bool(description="Whether credential is revoked on the ledger")


@docs(tags=["credentials"], summary="Fetch credential from wallet by id")
@match_info_schema(CredIdMatchInfoSchema())
@response_schema(CredBriefSchema(), 200, description="")
async def credentials_get(request: web.BaseRequest):
    """
    Request handler for retrieving credential.

    Args:
        request: aiohttp request object

    Returns:
        The credential brief

    """
    context: AdminRequestContext = request["context"]
    credential_id = request.match_info["credential_id"]
    session = await context.session()

    holder = session.inject(IndyHolder)
    try:
        credential = await holder.get_credential(credential_id)
    except WalletNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    credential_json = json.loads(credential)
    return web.json_response(credential_json)


@docs(tags=["credentials"], summary="Query credential revocation status by id")
@match_info_schema(CredIdMatchInfoSchema())
@querystring_schema(CredRevokedQueryStringSchema())
@response_schema(CredRevokedResultSchema(), 200, description="")
async def credentials_revoked(request: web.BaseRequest):
    """
    Request handler for querying revocation status of credential.

    Args:
        request: aiohttp request object

    Returns:
        Empty production

    """
    context: AdminRequestContext = request["context"]
    session = await context.session()
    credential_id = request.match_info["credential_id"]
    fro = request.query.get("from")
    to = request.query.get("to")

    ledger = session.inject(BaseLedger, required=False)
    if not ledger:
        reason = "No ledger available"
        if not context.settings.get_value("wallet.type"):
            reason += ": missing wallet-type?"
        raise web.HTTPForbidden(reason=reason)

    async with ledger:
        try:
            holder = session.inject(IndyHolder)
            revoked = await holder.credential_revoked(
                ledger,
                credential_id,
                int(fro) if fro else None,
                int(to) if to else None,
            )
        except WalletNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err
        except LedgerError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"revoked": revoked})


@docs(tags=["credentials"], summary="Get attribute MIME types from wallet")
@match_info_schema(CredIdMatchInfoSchema())
@response_schema(AttributeMimeTypesResultSchema(), 200, description="")
async def credentials_attr_mime_types_get(request: web.BaseRequest):
    """
    Request handler for getting credential attribute MIME types.

    Args:
        request: aiohttp request object

    Returns:
        The MIME types response

    """
    context: AdminRequestContext = request["context"]
    session = await context.session()
    credential_id = request.match_info["credential_id"]

    holder = session.inject(IndyHolder)
    return web.json_response(await holder.get_mime_type(credential_id))


@docs(tags=["credentials"], summary="Remove credential from wallet by id")
@match_info_schema(CredIdMatchInfoSchema())
@response_schema(HolderModuleResponseSchema(), description="")
async def credentials_remove(request: web.BaseRequest):
    """
    Request handler for searching connection records.

    Args:
        request: aiohttp request object

    Returns:
        Empty production

    """
    context: AdminRequestContext = request["context"]
    credential_id = request.match_info["credential_id"]

    session = await context.session()
    holder = session.inject(IndyHolder)
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
@response_schema(CredBriefListSchema(), 200, description="")
async def credentials_list(request: web.BaseRequest):
    """
    Request handler for searching credential records.

    Args:
        request: aiohttp request object

    Returns:
        The credential list response

    """
    context: AdminRequestContext = request["context"]
    session = await context.session()
    start = request.query.get("start")
    count = request.query.get("count")

    # url encoded json wql
    encoded_wql = request.query.get("wql") or "{}"
    wql = json.loads(encoded_wql)

    # defaults
    start = int(start) if isinstance(start, str) else 0
    count = int(count) if isinstance(count, str) else 10

    holder = session.inject(IndyHolder)
    try:
        credentials = await holder.get_credentials(start, count, wql)
    except IndyHolderError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"results": credentials})


@docs(
    tags=["credentials"],
    summary="Fetch DIF credential from wallet by id",
)
@match_info_schema(CredIdMatchInfoSchema())
@response_schema(VCRecordSchema(), 200, description="")
async def dif_cred_get(request: web.BaseRequest):
    """
    Request handler for retrieving DIF credential.

    Args:
        request: aiohttp request object

    Returns:
        Verifiable credential record

    """
    context: AdminRequestContext = request["context"]
    credential_id = request.match_info["credential_id"]

    session = await context.session()
    holder = session.inject(VCHolder)
    try:
        vc_record = await holder.retrieve_credential_by_given_id(credential_id)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except StorageError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(vc_record)


@docs(
    tags=["credentials"],
    summary="Remove DIF credential from wallet by id",
)
@match_info_schema(CredIdMatchInfoSchema())
@response_schema(HolderModuleResponseSchema(), 200, description="")
async def dif_cred_remove(request: web.BaseRequest):
    """
    Request handler for deleting DIF credential.

    Args:
        request: aiohttp request object

    Returns:
        Empty production

    """
    context: AdminRequestContext = request["context"]
    credential_id = request.match_info["credential_id"]

    session = await context.session()
    holder = session.inject(VCHolder)
    try:
        vc_record = await holder.retrieve_credential_by_given_id(credential_id)
        await holder.delete_credential(vc_record)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except StorageError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})


@docs(
    tags=["credentials"],
    summary="Fetch DIF credentials from wallet",
)
@request_schema(DIFCredentialsListRequestSchema())
@querystring_schema(CredentialsListQueryStringSchema())
@response_schema(VCRecordListSchema(), 200, description="")
async def dif_creds_list(request: web.BaseRequest):
    """
    Request handler for searching DIF credential records.

    Args:
        request: aiohttp request object

    Returns:
        The credential record list response

    """
    context: AdminRequestContext = request["context"]
    session = await context.session()
    body = await request.json()
    contexts = body.get("contexts")
    types = body.get("types")
    schema_ids = body.get("schema_ids")
    issuer_id = body.get("issuer_id")
    subject_id = body.get("subject_id")
    tag_query = body.get("tag_query")
    max_results = body.get("max_results")

    holder = session.inject(VCHolder)
    try:
        search = holder.search_credentials(
            contexts, types, schema_ids, issuer_id, subject_id, tag_query
        )
        records = await search.fetch(max_results)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except StorageError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"results": records})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/credential/{credential_id}", credentials_get, allow_head=False),
            web.get(
                "/credential/revoked/{credential_id}",
                credentials_revoked,
                allow_head=False,
            ),
            web.get(
                "/credential/mime-types/{credential_id}",
                credentials_attr_mime_types_get,
                allow_head=False,
            ),
            web.delete("/credential/{credential_id}", credentials_remove),
            web.get("/credentials", credentials_list, allow_head=False),
            web.get(
                "/credential/dif/{credential_id}",
                dif_cred_get,
                allow_head=False,
            ),
            web.delete("/credential/dif/{credential_id}", dif_cred_remove),
            web.get("/credentials/dif", dif_creds_list, allow_head=False),
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
