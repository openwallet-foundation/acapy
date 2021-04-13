"""jsonld admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema

from marshmallow import fields

from ...admin.request_context import AdminRequestContext

from ..models.openapi import OpenAPISchema
from ...config.base import InjectionError
from ...wallet.error import WalletError
from ...resolver.did_resolver import DIDResolver
from ...resolver.base import ResolverError
from .error import MissingVerificationMethodError, BaseJSONLDMessagingError
from .credential import sign_credential, verify_credential


class SignRequestSchema(OpenAPISchema):
    """Request schema for signing a jsonld doc."""

    verkey = fields.Str(required=True, description="verkey to use for signing")
    doc = fields.Dict(
        required=True,
        description="JSON-LD Doc to sign",
        doc=fields.Dict(
            credential=fields.Dict(
                required=True,
                description="credential to sign",
            ),
            options=fields.Dict(
                description="option describing how to sign",
                required=True,
                creator=fields.Str(required=False),
                verificationMethod=fields.Str(required=False),
                proofPurpose=fields.Str(required=False),
            ),
        ),
    )


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
    body = await request.json()
    doc = body.get("doc")
    try:
        context: AdminRequestContext = request["context"]
        async with context.session() as session:
            doc_with_proof = await sign_credential(
                session, doc.get("credential"), doc.get("options"), body.get("verkey")
            )
            response["signed_doc"] = doc_with_proof
    except (BaseJSONLDMessagingError) as err:
        response["error"] = repr(err)
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="No wallet available")
    return web.json_response(response)


class VerifyRequestSchema(OpenAPISchema):
    """Request schema for signing a jsonld doc."""

    verkey = fields.Str(
        required=False, description="verkey to use for doc verification"
    )
    doc = fields.Dict(
        required=True,
        description="JSON-LD Doc to verify",
        doc=fields.Dict(
            credential=fields.Dict(
                required=True,
                description="credential to verify",
            ),
            options=fields.Dict(
                description="option describing how to verify",
                required=True,
                creator=fields.Str(required=False),
                verificationMethod=fields.Str(required=False),
                proofPurpose=fields.Str(required=False),
            ),
        ),
    )


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
        profile = context.profile
        body = await request.json()
        verkey = body.get("verkey")
        doc = body.get("doc")
        async with context.session() as session:
            if verkey is None:
                resolver = session.inject(DIDResolver)
                ver_meth_expanded = await resolver.dereference(
                    profile, doc["proof"]["verificationMethod"]
                )
                if ver_meth_expanded is None:
                    raise MissingVerificationMethodError(
                        f"Verification method "
                        f"{doc['proof']['verificationMethod']} not found."
                    )
                verkey = ver_meth_expanded.material
            valid = await verify_credential(session, doc, verkey)
        response["valid"] = valid
    except (
        BaseJSONLDMessagingError,
        ResolverError,
    ) as e:
        response["error"] = repr(e)
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
            "name": "json-ld sign/verify",
            "description": "sign and verify json-ld data.",
            "externalDocs": {"description": "Specification"},  # , "url": SPEC_URI},
        }
    )
