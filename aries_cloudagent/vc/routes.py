"""VC-API Routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema

from .vc_ld.models.credential import (
    VerifiableCredential,
)

from .vc_ld.models.presentation import (
    VerifiablePresentation,
)

from .vc_ld.models.request_schemas import (
    ListCredentialResponseSchema,
    IssueCredentialRequestSchema,
    IssueCredentialResponseSchema,
    VerifyCredentialRequestSchema,
    VerifyCredentialResponseSchema,
    ProvePresentationRequestSchema,
    ProvePresentationResponseSchema,
    VerifyPresentationRequestSchema,
    VerifyPresentationResponseSchema,
)
from .vc_ld.models.options import LDProofVCOptions
from .vc_ld.manager import VcLdpManager, VcLdpManagerError
from ..admin.request_context import AdminRequestContext
from ..config.base import InjectionError
from ..resolver.base import ResolverError
from ..wallet.error import WalletError
from ..storage.error import StorageError, StorageNotFoundError
from ..storage.vc_holder.base import VCHolder


@docs(tags=["vc-api"], summary="List credentials")
@response_schema(ListCredentialResponseSchema(), 200, description="")
async def list_credentials_route(request: web.BaseRequest):
    """Request handler for issuing a credential.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    async with context.profile.session() as session:
        holder = session.inject(VCHolder)
    try:
        search = holder.search_credentials()
        records = await search.fetch()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except StorageError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response([record.serialize()["cred_value"] for record in records])


@docs(tags=["vc-api"], summary="Fetch credential by ID")
@response_schema(ListCredentialResponseSchema(), 200, description="")
async def fetch_credential_route(request: web.BaseRequest):
    """Request handler for issuing a credential.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    credential_id = request.match_info["credential_id"]
    async with context.profile.session() as session:
        holder = session.inject(VCHolder)
    try:
        search = holder.search_credentials(given_id=credential_id.strip('"'))
        records = await search.fetch()
        record = [record.serialize() for record in records]
        credential = record[0]["cred_value"] if len(record) == 1 else None
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except StorageError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response(credential)


@docs(tags=["vc-api"], summary="Issue a credential")
@request_schema(IssueCredentialRequestSchema())
@response_schema(IssueCredentialResponseSchema(), 200, description="")
async def issue_credential_route(request: web.BaseRequest):
    """Request handler for issuing a credential.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    credential = VerifiableCredential.deserialize(body["credential"])
    options = {} if "options" not in body else body["options"]
    # Default to Ed25519Signature2018 if no proof type was provided
    if "type" in options:
        options["proofType"] = options.pop("type")
    else:
        options["proofType"] = (
            "Ed25519Signature2018"
            if "proofType" not in options
            else options["proofType"]
        )
    options = LDProofVCOptions.deserialize(body["options"])

    try:
        manager = context.inject(VcLdpManager)
        vc = await manager.issue(credential, options)
    except VcLdpManagerError as err:
        return web.json_response({"error": str(err)}, status=400)
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="No wallet available")
    return web.json_response({"verifiableCredential": vc.serialize()})


@docs(tags=["vc-api"], summary="Verify a credential")
@request_schema(VerifyCredentialRequestSchema())
@response_schema(VerifyCredentialResponseSchema(), 200, description="")
async def verify_credential_route(request: web.BaseRequest):
    """Request handler for verifying a credential.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    vc = body.get("verifiableCredential")
    try:
        manager = context.inject(VcLdpManager)
        vc = VerifiableCredential.deserialize(vc)
        result = await manager.verify_credential(vc)
    except (VcLdpManagerError, ResolverError, ValueError) as error:
        raise web.HTTPBadRequest(reason=str(error))
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="No wallet available")
    return web.json_response(result.serialize())


@docs(tags=["vc-api"], summary="Store a credential")
@request_schema(VerifyCredentialRequestSchema)
@response_schema(VerifyCredentialResponseSchema, 200)
async def store_credential_route(request: web.BaseRequest):
    """Request handler for storing a credential.

    Args:
        request: aiohttp request object

    """
    body = await request.json()
    vc = VerifiableCredential.deserialize(body["verifiableCredential"])
    options = {} if "options" not in body else body["options"]
    options = LDProofVCOptions.deserialize(body["options"])

    try:
        context: AdminRequestContext = request["context"]
        manager = context.inject(VcLdpManager)
        await manager.verify_credential(vc)
        await manager.store_credential(vc, options)
    except VcLdpManagerError as err:
        return web.json_response({"error": str(err)}, status=400)
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="Bad credential")
    return web.json_response({"message": "Credential stored"}, status=200)


@docs(tags=["vc-api"], summary="Prove a presentation")
@request_schema(ProvePresentationRequestSchema())
@response_schema(ProvePresentationResponseSchema(), 200, description="")
async def prove_presentation_route(request: web.BaseRequest):
    """Request handler for proving a presentation.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    presentation = VerifiablePresentation.deserialize(body["presentation"])
    options = {} if "options" not in body else body["options"]
    # Default to Ed25519Signature2018 if no proof type was provided
    if "type" in options:
        options["proofType"] = options.pop("type")
    else:
        options["proofType"] = (
            "Ed25519Signature2018"
            if "proofType" not in options
            else options["proofType"]
        )
    options = LDProofVCOptions.deserialize(body["options"])

    try:
        manager = context.inject(VcLdpManager)
        vp = await manager.prove(presentation, options)
    except VcLdpManagerError as err:
        return web.json_response({"error": str(err)}, status=400)
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="No wallet available")
    return web.json_response({"verifiablePresentation": vp.serialize()})


@docs(tags=["vc-api"], summary="Verify a Presentation")
@request_schema(VerifyPresentationRequestSchema())
@response_schema(VerifyPresentationResponseSchema(), 200, description="")
async def verify_presentation_route(request: web.BaseRequest):
    """Request handler for verifying a presentation.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    vp = body.get("verifiablePresentation")
    try:
        manager = context.inject(VcLdpManager)
        vp = VerifiablePresentation.deserialize(vp)
        options = LDProofVCOptions.deserialize(body["options"])
        result = await manager.verify_presentation(vp, options)
    except (VcLdpManagerError, ResolverError, ValueError) as error:
        raise web.HTTPBadRequest(reason=str(error))
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="No wallet available")
    return web.json_response(result.serialize())


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
