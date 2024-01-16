"""VC Routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema

from marshmallow import ValidationError, fields, validates_schema

from aries_cloudagent.vc.vc_ld.validation_result import (
    PresentationVerificationResultSchema,
)

from .vc_ld.models.credential import (
    CredentialSchema,
    VerifiableCredential,
    VerifiableCredentialSchema,
)
from .vc_ld.models.options import LDProofVCOptions, LDProofVCOptionsSchema
from .vc_ld.manager import VcLdpManager, VcLdpManagerError
from ..admin.request_context import AdminRequestContext
from ..config.base import InjectionError
from ..resolver.base import ResolverError
from ..wallet.error import WalletError
from ..messaging.models.openapi import OpenAPISchema


class LdpIssueRequestSchema(OpenAPISchema):
    """Request schema for signing an ldb_vc."""

    credential = fields.Nested(CredentialSchema)
    options = fields.Nested(LDProofVCOptionsSchema)


class LdpIssueResponseSchema(OpenAPISchema):
    """Request schema for signing an ldb_vc."""

    vc = fields.Nested(VerifiableCredentialSchema)


@docs(tags=["ldp_vc"], summary="Sign an LDP VC.")
@request_schema(LdpIssueRequestSchema())
@response_schema(LdpIssueResponseSchema(), 200, description="")
async def ldp_issue(request: web.BaseRequest):
    """Request handler for signing a jsonld doc.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    credential = VerifiableCredential.deserialize(body["credential"])
    options = LDProofVCOptions.deserialize(body["options"])

    try:
        manager = context.inject(VcLdpManager)
        vc = await manager.issue(credential, options)
    except VcLdpManagerError as err:
        return web.json_response({"error": str(err)}, status=400)
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="No wallet available")
    return web.json_response({"vc": vc.serialize()})


class LdpVerifyRequestSchema(OpenAPISchema):
    """Request schema for verifying an LDP VP."""

    vp = fields.Nested(VerifiableCredentialSchema, required=False)
    vc = fields.Nested(VerifiableCredentialSchema, required=False)
    options = fields.Nested(LDProofVCOptionsSchema)

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Validate schema fields.

        Args:
            data: The data to validate

        Raises:
            ValidationError: if data has neither indy nor ld_proof

        """
        if not data.get("vp") and not data.get("vc"):
            raise ValidationError("Field vp or vc must be present")
        if data.get("vp") and data.get("vc"):
            raise ValidationError("Field vp or vc must be present, not both")


class LdpVerifyResponseSchema(PresentationVerificationResultSchema):
    """Request schema for verifying an LDP VP."""


@docs(tags=["ldp_vc"], summary="Verify an LDP VC or VP.")
@request_schema(LdpVerifyRequestSchema())
@response_schema(LdpVerifyResponseSchema(), 200, description="")
async def ldp_verify(request: web.BaseRequest):
    """Request handler for signing a jsonld doc.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    vp = body.get("vp")
    vc = body.get("vc")
    try:
        manager = context.inject(VcLdpManager)
        if vp:
            vp = VerifiableCredential.deserialize(vp)
            options = LDProofVCOptions.deserialize(body["options"])
            result = await manager.verify_presentation(vp, options)
        elif vc:
            vc = VerifiableCredential.deserialize(vc)
            result = await manager.verify_credential(vc)
        else:
            raise web.HTTPBadRequest(reason="vp or vc must be present")
        return web.json_response(result.serialize())
    except (VcLdpManagerError, ResolverError, ValueError) as error:
        raise web.HTTPBadRequest(reason=str(error))
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="No wallet available")


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.post("/vc/ldp/issue", ldp_issue),
            web.post("/vc/ldp/verify", ldp_verify),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""
    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "ldp-vc",
            "description": "Issue and verify LDP VCs and VPs",
            "externalDocs": {
                "description": "Specification",
                "url": "https://www.w3.org/TR/vc-data-model/",
            },
        }
    )
