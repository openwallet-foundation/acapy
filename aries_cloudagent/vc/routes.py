"""VC-API Routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow.exceptions import ValidationError
from ..admin.request_context import AdminRequestContext
from ..storage.error import StorageError, StorageNotFoundError
from ..wallet.error import WalletError
from ..config.base import InjectionError
from ..resolver.base import ResolverError
from ..storage.vc_holder.base import VCHolder
from .vc_ld.models import web_schemas
from .vc_ld.manager import VcLdpManager
from .vc_ld.manager import VcLdpManagerError
from .vc_ld.models.credential import (
    VerifiableCredential,
)

from .vc_ld.models.presentation import (
    VerifiablePresentation,
)

from .vc_ld.models.options import LDProofVCOptions


@docs(tags=["vc-api"], summary="List credentials")
@response_schema(web_schemas.ListCredentialsResponse(), 200, description="")
async def list_credentials_route(request: web.BaseRequest):
    """Request handler for issuing a credential.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    holder = context.inject(VCHolder)
    try:
        search = holder.search_credentials()
        records = [record.serialize()["cred_value"] for record in await search.fetch()]
        return web.json_response(records, status=200)
    except (StorageError, StorageNotFoundError) as err:
        return web.json_response({"message": err.roll_up}, status=400)


@docs(tags=["vc-api"], summary="Fetch credential by ID")
@response_schema(web_schemas.FetchCredentialResponse(), 200, description="")
async def fetch_credential_route(request: web.BaseRequest):
    """Request handler for issuing a credential.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    holder = context.inject(VCHolder)
    try:
        credential_id = request.match_info["credential_id"].strip('"')
        search = holder.search_credentials(given_id=credential_id)
        record = [record.serialize()["cred_value"] for record in await search.fetch()]
        if len(record) < 1:
            return web.json_response({"message": "No credential found"}, status=404)
        if len(record) > 1:
            return web.json_response(record, status=200)
        return web.json_response(record[0], status=200)
    except (StorageError, StorageNotFoundError) as err:
        return web.json_response({"message": err.roll_up}, status=400)


@docs(tags=["vc-api"], summary="Issue a credential")
@request_schema(web_schemas.IssueCredentialRequest())
@response_schema(web_schemas.IssueCredentialResponse(), 200, description="")
async def issue_credential_route(request: web.BaseRequest):
    """Request handler for issuing a credential.

    Args:
        request: aiohttp request object

    """
    body = await request.json()
    context: AdminRequestContext = request["context"]
    manager = context.inject(VcLdpManager)
    try:
        credential = VerifiableCredential.deserialize(body["credential"])
        options = {} if "options" not in body else body["options"]
        # Our request uses the "type" key to represent the proof type (suite) to use
        # We must pass this value as "proofType" to the LDProofVCOptions instance
        # Default to Ed25519Signature2020 if no proof type is provided
        options["proofType"] = (
            options.pop("type") if "type" in options else "Ed25519Signature2020"
        )
        options = LDProofVCOptions.deserialize(options)
        vc = await manager.issue(credential, options)
        response = {"verifiableCredential": vc.serialize()}
        return web.json_response(response, status=201)
    except (ValidationError, VcLdpManagerError, WalletError, InjectionError) as err:
        return web.json_response({"message": str(err)}, status=400)


@docs(tags=["vc-api"], summary="Verify a credential")
@request_schema(web_schemas.VerifyCredentialRequest())
@response_schema(web_schemas.VerifyCredentialResponse(), 200, description="")
async def verify_credential_route(request: web.BaseRequest):
    """Request handler for verifying a credential.

    Args:
        request: aiohttp request object

    """
    body = await request.json()
    context: AdminRequestContext = request["context"]
    manager = context.inject(VcLdpManager)
    try:
        vc = VerifiableCredential.deserialize(body["verifiableCredential"])
        result = await manager.verify_credential(vc)
        result = result.serialize()
        return web.json_response(result)
    except (
        ValidationError,
        VcLdpManagerError,
        ResolverError,
        ValueError,
        WalletError,
        InjectionError,
    ) as err:
        return web.json_response({"message": str(err)}, status=400)


@docs(tags=["vc-api"], summary="Store a credential")
async def store_credential_route(request: web.BaseRequest):
    """Request handler for storing a credential.

    Args:
        request: aiohttp request object

    """
    body = await request.json()
    context: AdminRequestContext = request["context"]
    manager = context.inject(VcLdpManager)

    try:
        vc = VerifiableCredential.deserialize(body["verifiableCredential"])
        options = {} if "options" not in body else body["options"]
        options = LDProofVCOptions.deserialize(options)
        await manager.verify_credential(vc)
        await manager.store_credential(vc, options)
        return web.json_response({"message": "Credential stored"}, status=200)
    except (ValidationError, VcLdpManagerError, WalletError, InjectionError) as err:
        return web.json_response({"message": str(err)}, status=400)


@docs(tags=["vc-api"], summary="Prove a presentation")
@request_schema(web_schemas.ProvePresentationRequest())
@response_schema(web_schemas.ProvePresentationResponse(), 200, description="")
async def prove_presentation_route(request: web.BaseRequest):
    """Request handler for proving a presentation.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    manager = context.inject(VcLdpManager)
    body = await request.json()
    try:
        presentation = VerifiablePresentation.deserialize(body["presentation"])
        options = {} if "options" not in body else body["options"]
        # Our request uses the "type" key to represent the proof type (suite) to use
        # We must pass this value as "proofType" to the LDProofVCOptions instance
        # Default to Ed25519Signature2020 if no proof type is provided
        options["proofType"] = (
            options.pop("type") if "type" in options else "Ed25519Signature2020"
        )
        options = LDProofVCOptions.deserialize(options)
        vp = await manager.prove(presentation, options)
        return web.json_response({"verifiablePresentation": vp.serialize()}, status=201)
    except (ValidationError, VcLdpManagerError, WalletError, InjectionError) as err:
        return web.json_response({"message": str(err)}, status=400)


@docs(tags=["vc-api"], summary="Verify a Presentation")
@request_schema(web_schemas.VerifyPresentationRequest())
@response_schema(web_schemas.VerifyPresentationResponse(), 200, description="")
async def verify_presentation_route(request: web.BaseRequest):
    """Request handler for verifying a presentation.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    manager = context.inject(VcLdpManager)
    body = await request.json()
    try:
        vp = VerifiablePresentation.deserialize(body["verifiablePresentation"])
        options = {} if "options" not in body else body["options"]
        options = LDProofVCOptions.deserialize(options)
        verified = await manager.verify_presentation(vp, options)
        return web.json_response(verified.serialize(), status=200)
    except (
        ValidationError,
        WalletError,
        InjectionError,
        VcLdpManagerError,
        ResolverError,
        ValueError,
    ) as err:
        return web.json_response({"message": str(err)}, status=400)


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/vc/credentials", list_credentials_route, allow_head=False),
            web.get(
                "/vc/credentials/{credential_id}",
                fetch_credential_route,
                allow_head=False,
            ),
            web.post("/vc/credentials/issue", issue_credential_route),
            web.post("/vc/credentials/store", store_credential_route),
            web.post("/vc/credentials/verify", verify_credential_route),
            web.post("/vc/presentations/prove", prove_presentation_route),
            web.post("/vc/presentations/verify", verify_presentation_route),
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
            "description": "Endpoints for managing w3c credentials and presentations",
            "externalDocs": {
                "description": "Specification",
                "url": "https://w3c-ccg.github.io/vc-api/",
            },
        }
    )
