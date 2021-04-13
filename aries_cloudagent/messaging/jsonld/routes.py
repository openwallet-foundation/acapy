"""jsonld admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema

from marshmallow import fields

from ...admin.request_context import AdminRequestContext

from ..models.openapi import OpenAPISchema
from ...config.base import InjectionError
from ...wallet.error import WalletError
from ...resolver.did_resolver import DIDResolver
from ...resolver.base import ResolverError, BaseError
from pydid import DIDError
from .error import DroppedAttributeError, MissingVerificationMethodError
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
        session = await context.session()
        body = await request.json()
        verkey = body.get("verkey")
        doc = body.get("doc")
        doc_with_proof = await sign_credential(
            session, doc.get("credential"), doc.get("options"), verkey
        )
        response["signed_doc"] = doc_with_proof
    except (WalletError, DroppedAttributeError, MissingVerificationMethodError) as err:
        response["error"] = str(err)
    return web.json_response(response)


class VerifyRequestSchema(OpenAPISchema):
    """Request schema for signing a jsonld doc."""

    verkey = fields.Str(required=True, description="verkey to use for doc verification")
    verification_method = fields.Str(
        required=False,
        description="DID URL to the Verification Method to use to verify doc",
    )
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
    try:
        context: AdminRequestContext = request["context"]
        profile = context.profile
        body = await request.json()
        verkey = body.get("verkey")
        ver_meth = body.get("verification_method")
        doc = body.get("doc")
        async with context.session() as session:
            if ver_meth:
                resolver = session.inject(DIDResolver)
                ver_meth_expanded = await resolver.dereference(profile, ver_meth)
                if ver_meth_expanded is None:
                    raise ResolverError(f"Verification method {ver_meth} not found.")
                verkey = ver_meth_expanded.material
            result = await verify_credential(session, doc, verkey)
    except (DIDError, ResolverError, WalletError, InjectionError) as err:
        if isinstance(err, BaseError):
            raise web.HTTPBadRequest(reason=err.roll_up) from err
        else:
            raise web.HTTPBadRequest(
                reason=f"internal raised error: '{repr(err)}'"
            ) from err
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
