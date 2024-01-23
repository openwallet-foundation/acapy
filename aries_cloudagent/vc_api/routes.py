"""VC-API Routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema

from .service import (
    list_stored_credentials,
    fetch_stored_credential,
    issue_credential,
    store_issued_credential,
    verify_credential,
    prove_presentation,
    verify_presentation,
)
from .models.request_schemas import (
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


@docs(tags=["vc-api"], summary="List credentials")
@response_schema(ListCredentialResponseSchema(), 200, description="")
async def list_credentials_route(request: web.BaseRequest):
    """Request handler for issuing a credential.

    Args:
        request: aiohttp request object

    """
    records = list_stored_credentials(request)
    response = [record.serialize()["cred_value"] for record in records]
    return web.json_response(response)


@docs(tags=["vc-api"], summary="Fetch credential by ID")
# @response_schema(ListCredentialResponseSchema(), 200, description="")
async def fetch_credential_route(request: web.BaseRequest):
    """Request handler for issuing a credential.

    Args:
        request: aiohttp request object

    """
    credential = await fetch_stored_credential(request)
    return web.json_response(credential)


@docs(tags=["vc-api"], summary="Issue a credential")
@request_schema(IssueCredentialRequestSchema())
@response_schema(IssueCredentialResponseSchema(), 200, description="")
async def issue_credential_route(request: web.BaseRequest):
    """Request handler for issuing a credential.

    Args:
        request: aiohttp request object

    """
    vc = await issue_credential(request)
    response = {"verifiableCredential": vc.serialize()}
    return web.json_response(response, status=201)


@docs(tags=["vc-api"], summary="Verify a credential")
@request_schema(VerifyCredentialRequestSchema())
@response_schema(VerifyCredentialResponseSchema(), 200, description="")
async def verify_credential_route(request: web.BaseRequest):
    """Request handler for verifying a credential.

    Args:
        request: aiohttp request object

    """
    verified = await verify_credential(request)
    response = verified.serialize()
    return web.json_response(response)


@docs(tags=["vc-api"], summary="Store a credential")
@request_schema(VerifyCredentialRequestSchema)
@response_schema(VerifyCredentialResponseSchema, 200)
async def store_credential_route(request: web.BaseRequest):
    """Request handler for storing a credential.

    Args:
        request: aiohttp request object

    """
    credential_stored = await store_issued_credential(request)
    if not credential_stored:
        response = {"message": "Credential not stored"}
        return web.json_response(response, status=400)

    response = {"message": "Credential stored"}
    return web.json_response(response, status=200)


@docs(tags=["vc-api"], summary="Prove a presentation")
@request_schema(ProvePresentationRequestSchema())
@response_schema(ProvePresentationResponseSchema(), 200, description="")
async def prove_presentation_route(request: web.BaseRequest):
    """Request handler for proving a presentation.

    Args:
        request: aiohttp request object

    """
    vp = await prove_presentation(request)
    response = {"verifiablePresentation": vp.serialize()}
    return web.json_response(response)


@docs(tags=["vc-api"], summary="Verify a Presentation")
@request_schema(VerifyPresentationRequestSchema())
@response_schema(VerifyPresentationResponseSchema(), 200, description="")
async def verify_presentation_route(request: web.BaseRequest):
    """Request handler for verifying a presentation.

    Args:
        request: aiohttp request object

    """
    verified = await verify_presentation(request)
    response = verified.serialize()
    return web.json_response(response)


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
