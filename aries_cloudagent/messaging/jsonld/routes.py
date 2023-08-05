"""jsonld admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from pydid.verification_method import Ed25519VerificationKey2018

from marshmallow import INCLUDE, Schema, fields

from ...admin.request_context import AdminRequestContext
from ...config.base import InjectionError
from ...resolver.base import ResolverError
from ...resolver.did_resolver import DIDResolver
from ...wallet.error import WalletError
from ..models.openapi import OpenAPISchema
from .credential import sign_credential, verify_credential
from .error import BaseJSONLDMessagingError

SUPPORTED_VERIFICATION_METHOD_TYPES = (Ed25519VerificationKey2018,)


class SignatureOptionsSchema(Schema):
    """Schema for LD signature options."""

    type = fields.Str(required=False)
    verificationMethod = fields.Str(required=True)
    proofPurpose = fields.Str(required=True)
    challenge = fields.Str(required=False)
    domain = fields.Str(required=False)


class DocSchema(OpenAPISchema):
    """Schema for LD doc to sign."""

    credential = fields.Dict(
        required=True, metadata={"description": "Credential to sign"}
    )
    options = fields.Nested(
        SignatureOptionsSchema,
        required=True,
        metadata={"description": "Signature options"},
    )


class SignRequestSchema(OpenAPISchema):
    """Request schema for signing a jsonld doc."""

    verkey = fields.Str(
        required=True, metadata={"description": "Verkey to use for signing"}
    )
    doc = fields.Nested(DocSchema, required=True)


class SignResponseSchema(OpenAPISchema):
    """Response schema for a signed jsonld doc."""

    signed_doc = fields.Dict(
        required=False, metadata={"description": "Signed document"}
    )
    error = fields.Str(required=False, metadata={"description": "Error text"})


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
    body = await request.json()
    doc = body.get("doc")
    try:
        context: AdminRequestContext = request["context"]
        async with context.session() as session:
            doc_with_proof = await sign_credential(
                session, doc.get("credential"), doc.get("options"), body.get("verkey")
            )
            response["signed_doc"] = doc_with_proof
    except BaseJSONLDMessagingError as err:
        response["error"] = str(err)
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="No wallet available")
    return web.json_response(response)


class SignedDocSchema(OpenAPISchema):
    """Verifiable doc schema."""

    class Meta:
        """Keep unknown values."""

        unknown = INCLUDE

    proof = fields.Nested(
        SignatureOptionsSchema,
        required=True,
        metadata={"unknown": INCLUDE, "description": "Linked data proof"},
    )


class VerifyRequestSchema(OpenAPISchema):
    """Request schema for signing a jsonld doc."""

    verkey = fields.Str(
        required=False, metadata={"description": "Verkey to use for doc verification"}
    )
    doc = fields.Nested(
        SignedDocSchema, required=True, metadata={"description": "Signed document"}
    )


class VerifyResponseSchema(OpenAPISchema):
    """Response schema for verification result."""

    valid = fields.Bool(required=True)
    error = fields.Str(required=False, metadata={"description": "Error text"})


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
        profile = context.profile
        body = await request.json()
        verkey = body.get("verkey")
        doc = body.get("doc")
        async with context.session() as session:
            if verkey is None:
                resolver = session.inject(DIDResolver)
                vmethod = await resolver.dereference(
                    profile,
                    doc["proof"]["verificationMethod"],
                )

                if not isinstance(vmethod, SUPPORTED_VERIFICATION_METHOD_TYPES):
                    raise web.HTTPBadRequest(
                        reason="{} is not supported".format(vmethod.type)
                    )
                verkey = vmethod.material

            valid = await verify_credential(session, doc, verkey)

        response["valid"] = valid
    except (BaseJSONLDMessagingError, ResolverError, ValueError) as error:
        response["error"] = str(error)
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="No wallet available")
    return web.json_response(response)


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
            "name": "jsonld",
            "description": "Sign and verify json-ld data",
            "externalDocs": {
                "description": "Specification",
                "url": "https://tools.ietf.org/html/rfc7515",
            },
        }
    )
