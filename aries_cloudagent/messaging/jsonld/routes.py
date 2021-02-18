"""jsonld admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema

from marshmallow import fields

from ...admin.request_context import AdminRequestContext
from ...wallet.base import BaseWallet

from ..models.openapi import OpenAPISchema

from .credential import sign_credential, verify_credential


class SignRequestSchema(OpenAPISchema):
    """Request schema for signing a jsonld doc."""

    verkey = fields.Str(required=True, description="verkey to use for signing")
    doc = fields.Dict(required=True, description="JSON-LD Doc to sign")


class SignResponseSchema(OpenAPISchema):
    """Response schema for a signed jsonld doc."""

    signed_doc = fields.Dict(required=True)


@docs(tags=["jsonld"], summary="Sign a JSON-LD structure and return it")
@request_schema(SignRequestSchema())
@response_schema(SignResponseSchema(), 200, description="")
async def sign(request: web.BaseRequest):
    """
    Request handler for signing a jsonld doc.

    Args:
        request: aiohttp request object

    """
    response = {}
    try:
        context: AdminRequestContext = request["context"]
        body = await request.json()
        verkey = body.get("verkey")
        doc = body.get("doc")
        credential = doc["credential"]
        signature_options = doc["options"]

        async with context.session() as session:
            wallet = session.inject(BaseWallet, required=False)
            if not wallet:
                raise web.HTTPForbidden()
            document_with_proof = await sign_credential(
                credential, signature_options, verkey, wallet
            )

        response["signed_doc"] = document_with_proof
    except Exception as e:
        response["error"] = str(e)

    return web.json_response(response)


class VerifyRequestSchema(OpenAPISchema):
    """Request schema for signing a jsonld doc."""

    verkey = fields.Str(required=True, description="verkey to use for doc verification")
    doc = fields.Dict(required=True, description="JSON-LD Doc to verify")


class VerifyResponseSchema(OpenAPISchema):
    """Response schema for verification result."""

    valid = fields.Bool(required=True)


@docs(tags=["jsonld"], summary="Verify a JSON-LD structure.")
@request_schema(VerifyRequestSchema())
@response_schema(VerifyResponseSchema(), 200, description="")
async def verify(request: web.BaseRequest):
    """
    Request handler for signing a jsonld doc.

    Args:
        request: aiohttp request object

    """
    response = {"valid": False}
    try:
        context: AdminRequestContext = request["context"]
        body = await request.json()
        verkey = body.get("verkey")
        doc = body.get("doc")

        async with context.session() as session:
            wallet = session.inject(BaseWallet, required=False)
            if not wallet:
                raise web.HTTPForbidden()
            valid = await verify_credential(doc, verkey, wallet)

        response["valid"] = valid
    except Exception as e:
        response["error"] = str(e)

    return web.json_response(response)


async def register(app: web.Application):
    """Register routes."""

    app.add_routes([web.post("/jsonld/sign", sign)])
    app.add_routes([web.post("/jsonld/verify", verify)])
