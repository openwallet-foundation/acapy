""" Anoncreds admin routes """
# import json

from aiohttp import web
from aiohttp_apispec import (docs,  # request_schema, response_schema
                             match_info_schema, querystring_schema)
from marshmallow import fields
from ...messaging.valid import ( UUIDFour
)
from ...messaging.models.openapi import OpenAPISchema

SPEC_URI = ""

class SchemaIdMatchInfoSchema(OpenAPISchema):
    """"""
    schema_id = fields.Str(
        description="Schema identifier", required=True, example=UUIDFour.EXAMPLE
    )
    

@docs(tags=["anoncreds"], summary="")
async def schemas_post(request: web.BaseRequest):
    raise NotImplementedError()


@docs(tags=["anoncreds"], summary="")
@match_info_schema(HolderCredIdMatchInfoSchema())
async def schema_get(request: web.BaseRequest):
    raise NotImplementedError()


@docs(tags=["anoncreds"], summary="")
async def schemas_get(request: web.BaseRequest):
    raise NotImplementedError()


@docs(tags=["anoncreds"], summary="")
async def schemas_get_created(request: web.BaseRequest):
    raise NotImplementedError()


@docs(tags=["anoncreds"], summary="")
async def cred_def_post(request: web.BaseRequest):
    raise NotImplementedError()


@docs(tags=["anoncreds"], summary="")
async def cred_def_get(request: web.BaseRequest):
    raise NotImplementedError()


@docs(tags=["anoncreds"], summary="")
async def cred_defs_get(request: web.BaseRequest):
    raise NotImplementedError()


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.post("/anoncreds/schema", schemas_post, allow_head=False),
            web.get("/anoncreds/schema/{schema_id}", schema_get, allow_head=False),
            web.get(
                "/anoncreds/schemas/issuer/{issuer_id}", schemas_get, allow_head=False
            ),
            web.get(
                "/anoncreds/schemas/did-method/{did_method}",
                schemas_get,
                allow_head=False,
            ),
            web.post(
                "/anoncreds/credential-definition", cred_def_post, allow_head=False
            ),
            web.get(
                "/anoncreds/credential-definition/{credential_definition_id}",
                cred_def_get,
                allow_head=False,
            ),
            web.get(
                "/anoncreds/credential-definitions/issuer/{did_method}",
                cred_defs_get,
                allow_head=False,
            ),
            web.get(
                "/anoncreds/credential-definitions/did-method/{did_method}",
                cred_defs_get,
                allow_head=False,
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
            "name": "anoncreds",
            "description": "Anoncreds management",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
