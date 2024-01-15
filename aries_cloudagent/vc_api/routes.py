"""VC-API Routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema

from ..admin.request_context import AdminRequestContext
from ..config.base import InjectionError
from ..resolver.base import ResolverError
from ..wallet.error import WalletError

from ..vc.vc_ld.manager import VcLdpManager, VcLdpManagerError
from ..vc.vc_ld.models.credential import VerifiableCredential
from ..vc.vc_ld.models.presentation import VerifiablePresentation
from ..vc.vc_ld.models.options import LDProofVCOptions
from .examples import (
    IssueCredentialRequest,
    IssueCredentialResponse,
    VerifyCredentialRequest,
    VerifyCredentialResponse,
    ProvePresentationRequest,
    ProvePresentationResponse,
    VerifyPresentationRequest,
    VerifyPresentationResponse,
)

"""CREDENTIALS"""


@docs(tags=["vc-api"], summary="Issue a credential")
@request_schema(IssueCredentialRequest)
@response_schema(IssueCredentialResponse, 201)
async def issue_credential(request: web.BaseRequest):
    """Request handler for signing a jsonld doc.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    credential = VerifiableCredential.deserialize(body["credential"])

    options = {} if "options" not in body else body["options"]
    # Default to Ed25519Signature2018 if no proof type was provided
    options["proofType"] = (
        "Ed25519Signature2018" if "proofType" not in options else options["proofType"]
    )
    options = LDProofVCOptions.deserialize(options)
    try:
        manager = context.inject(VcLdpManager)
        vc = await manager.issue(credential, options)
    except VcLdpManagerError as err:
        return web.json_response({"message": str(err)}, status=400)
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="No wallet available")
    return web.json_response({"verifiableCredential": vc.serialize()}, status=201)


@docs(tags=["vc-api"], summary="Verify a credential")
@request_schema(VerifyCredentialRequest)
@response_schema(VerifyCredentialResponse, 200)
async def verify_credential(request: web.BaseRequest):
    """Request handler for verifying a jsonld doc.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    vc = VerifiableCredential.deserialize(body.get("verifiableCredential"))
    try:
        manager = context.inject(VcLdpManager)
        result = await manager.verify_credential(vc)
        return web.json_response(result.serialize())
    except (VcLdpManagerError, ResolverError, ValueError) as error:
        raise web.HTTPBadRequest(reason=str(error))
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="No wallet available")


"""PRESENTATIONS"""


@docs(tags=["vc-api"], summary="Prove a presentation")
@request_schema(ProvePresentationRequest)
@response_schema(ProvePresentationResponse, 201)
async def prove_presentation(request: web.BaseRequest):
    """Request handler for signing a jsonld doc.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    presentation = VerifiablePresentation.deserialize(body["presentation"])

    options = {} if "options" not in body else body["options"]
    # Default to Ed25519Signature2018 if no proof type was provided
    options["proofType"] = (
        "Ed25519Signature2018" if "proofType" not in options else options["proofType"]
    )
    options = LDProofVCOptions.deserialize(options)

    try:
        manager = context.inject(VcLdpManager)
        vp = await manager.prove(presentation, options)
    except VcLdpManagerError as err:
        return web.json_response({"error": str(err)}, status=400)
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="No wallet available")
    return web.json_response({"verifiablePresentation": vp.serialize()}, status=201)


@docs(tags=["vc-api"], summary="Verify a presentation")
@request_schema(VerifyPresentationRequest)
@response_schema(VerifyPresentationResponse, 201)
async def verify_presentation(request: web.BaseRequest):
    """Request handler for verifying a jsonld doc.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    vp = VerifiablePresentation.deserialize(body.get("verifiablePresentation"))

    options = {} if "options" not in body else body["options"]
    options = LDProofVCOptions.deserialize(options)
    try:
        manager = context.inject(VcLdpManager)

        result = await manager.verify_presentation(vp, options)
        return web.json_response(result.serialize())
    except (VcLdpManagerError, ResolverError, ValueError) as error:
        raise web.HTTPBadRequest(reason=str(error))
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="No wallet available")


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.post("/credentials/issue", issue_credential),
            web.post("/credentials/verify", verify_credential),
            web.post("/presentations/prove", prove_presentation),
            web.post("/presentations/verify", verify_presentation),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""
    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "vc-api",
            "description": "Manage W3C credentials and presentations",
            "externalDocs": {
                "description": "Specification",
                "url": "https://w3c-ccg.github.io/vc-api",
            },
        }
    )
