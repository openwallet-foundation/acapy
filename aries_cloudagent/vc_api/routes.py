"""VC-API Routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema

from ..admin.request_context import AdminRequestContext
from ..config.base import InjectionError
from ..resolver.base import ResolverError
from ..wallet.error import WalletError

from ..vc.ld_proofs.document_loader import DocumentLoader
from ..vc.ld_proofs.purposes.assertion_proof_purpose import AssertionProofPurpose

from ..vc.vc_ld.verify import verify_credential, verify_presentation
from ..vc.vc_ld.issue import issue as issue_credential
from ..vc.vc_ld.prove import sign_presentation
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
async def issue_credential_route(request: web.BaseRequest):
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
        vc = await issue_credential(
            credential=credential.serialize(),
            suite=await manager._get_suite_for_credential(credential, options),
            document_loader=manager.profile.inject(DocumentLoader),
            purpose=AssertionProofPurpose(),
        )
    except VcLdpManagerError as err:
        return web.json_response({"message": str(err)}, status=400)
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="No wallet available")
    return web.json_response({"verifiableCredential": vc}, status=201)


@docs(tags=["vc-api"], summary="Verify a credential")
@request_schema(VerifyCredentialRequest)
@response_schema(VerifyCredentialResponse, 200)
async def verify_credential_route(request: web.BaseRequest):
    """Request handler for verifying a jsonld doc.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    vc = VerifiableCredential.deserialize(body.get("verifiableCredential"))
    try:
        manager = context.inject(VcLdpManager)
        result = await verify_credential(
            credential=vc.serialize(),
            suites=await manager._get_all_suites(),
            document_loader=manager.profile.inject(DocumentLoader),
        )
        return web.json_response(result.serialize())
    except (VcLdpManagerError, ResolverError, ValueError) as error:
        raise web.HTTPBadRequest(reason=str(error))
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="No wallet available")


"""PRESENTATIONS"""


@docs(tags=["vc-api"], summary="Prove a presentation")
@request_schema(ProvePresentationRequest)
@response_schema(ProvePresentationResponse, 201)
async def prove_presentation_route(request: web.BaseRequest):
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
        vp = await sign_presentation(
            presentation=presentation.serialize(),
            suite=await manager._get_suite_for_credential(presentation, options),
            document_loader=manager.profile.inject(DocumentLoader),
            purpose=AssertionProofPurpose(),
        )
    except VcLdpManagerError as err:
        return web.json_response({"error": str(err)}, status=400)
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="No wallet available")
    return web.json_response({"verifiablePresentation": vp}, status=201)


@docs(tags=["vc-api"], summary="Verify a presentation")
@request_schema(VerifyPresentationRequest)
@response_schema(VerifyPresentationResponse, 201)
async def verify_presentation_route(request: web.BaseRequest):
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
        result = await verify_presentation(
            presentation=vp.serialize(),
            suites=await manager._get_all_suites(),
            document_loader=manager.profile.inject(DocumentLoader),
            purpose=AssertionProofPurpose(),
        )
        return web.json_response(result.serialize())
    except (VcLdpManagerError, ResolverError, ValueError) as error:
        raise web.HTTPBadRequest(reason=str(error))
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="No wallet available")


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.post("/credentials/issue", issue_credential_route),
            web.post("/credentials/verify", verify_credential_route),
            web.post("/presentations/prove", prove_presentation_route),
            web.post("/presentations/verify", verify_presentation_route),
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
