"""jsonld admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema

from ...admin.request_context import AdminRequestContext
from ...messaging.models.openapi import OpenAPISchema
from marshmallow import fields

from ...config.base import InjectionError
from ...wallet.error import WalletError
from ...resolver.did_resolver import DIDResolver
from ...resolver.base import ResolverError
from ...resolver.did import DIDError
from .credential import sign_credential, verify_credential


class JsonLDRequestSchema(OpenAPISchema):
    """Request schema for signing a jsonld doc."""

    verification_method = fields.Str(
        required=True, data_key="verificationMethod", description="key"
    )
    document = fields.Dict(required=True, description="JSON-LD Doc to sign")


class SignResponseSchema(OpenAPISchema):
    """Response schema for a signed jsonld doc."""

    signed_doc = fields.Dict(required=True)


class VerifyResponseSchema(OpenAPISchema):
    """Response schema for verification result."""

    valid = fields.Bool(required=True)


@docs(tags=["jsonld"], summary="Sign a JSON-LD structure and return it")
@request_schema(JsonLDRequestSchema())
@response_schema(SignResponseSchema(), 200, description="")
async def sign(request: web.BaseRequest):
    """
    Request handler for signing a jsonld doc.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    session = await context.session()
    body = await request.json()
    ver_meth = body.get("verificationMethod")
    doc = body.get("document")
    try:
        resolver = session.inject(DIDResolver)
        # TODO: make this work in the wild.
        ver_meth_expanded = await resolver.dereference(session, ver_meth)
        if ver_meth_expanded is None:
            raise ResolverError(f"Verification method {ver_meth} not found.")
        verkey = ver_meth_expanded.value
        doc_with_proof = await sign_credential(
            session, doc, {"verificationMethod": ver_meth}, verkey
        )
    except (DIDError, ResolverError, WalletError, InjectionError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response({"signed_doc": doc_with_proof})


@docs(tags=["jsonld"], summary="Verify a JSON-LD structure.")
@request_schema(JsonLDRequestSchema())
@response_schema(VerifyResponseSchema(), 200, description="")
async def verify(request: web.BaseRequest):
    """
    Request handler for signing a jsonld doc.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    session = await context.session()
    body = await request.json()
    ver_meth = body.get("verificationMethod")
    doc = body.get("document")
    try:
        resolver = session.inject(DIDResolver)
        # TODO: make this work in the wild.
        ver_meth_expanded = await resolver.dereference(session, ver_meth)
        if ver_meth_expanded is None:
            raise ResolverError(f"Verification method {ver_meth} not found.")
        verkey = ver_meth_expanded.value
        result = await verify_credential(session, doc, verkey)
    except (DIDError, ResolverError, WalletError, InjectionError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response({"valid": result})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes([web.post("/jsonld/sign", sign), web.post("/jsonld/verify", verify)])


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "json-ld sign/verify",
            "description": "sign and verify json-ld data.",
            "externalDocs": {"description": "Specification"},  # , "url": SPEC_URI},
        }
    )
