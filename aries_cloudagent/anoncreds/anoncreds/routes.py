""" Anoncreds admin routes """
# import json

from aiohttp import web
# from aiohttp_apispec import (docs, match_info_schema, querystring_schema,
#                             request_schema, response_schema)

SPEC_URI = ""


async def register(app: web.Application):
    """Register routes."""

    app.add_routes([
        web.post("/anoncreds/schemas",  , allow_head=False),
        web.get("/anoncreds/schemas/{schema_id}", , allow_head=False),
        web.get("/anoncreds/schemas/created", ,allow_head=False),
        web.post("/anoncreds/credential-definitions", ,allow_head=False),
        web.get("/anoncreds/credential-definitions/{credential_definition_id}", ,allow_head=False),
        web.get("/anoncreds/credential-definitions/created", ,allow_head=False),
    ])


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
