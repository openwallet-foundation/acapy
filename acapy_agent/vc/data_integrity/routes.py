"""Data Integrity admin routes."""

import logging

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow import fields

from ...admin.decorators.auth import tenant_authentication
from ...admin.request_context import AdminRequestContext
from ...messaging.models.openapi import OpenAPISchema
from ...wallet.error import WalletError
from .manager import DataIntegrityManager, DataIntegrityManagerError
from .models import DataIntegrityProofOptions, DataIntegrityProofOptionsSchema

LOGGER = logging.getLogger(__name__)


class AddProofSchema(OpenAPISchema):
    """Request schema to add a DI proof to a document."""

    document = fields.Dict(required=True, metadata={"example": {"hello": "world"}})
    options = fields.Nested(
        DataIntegrityProofOptionsSchema,
        metadata={
            "example": {
                "type": "DataIntegrityProof",
                "cryptosuite": "eddsa-jcs-2022",
                "proofPurpose": "assertionMethod",
                "verificationMethod": "did:web:example.com#key-01",
            }
        },
    )


class AddProofResponseSchema(OpenAPISchema):
    """Response schema to adding a DI proof to a document."""

    secured_document = fields.Dict(
        required=True, metadata={"example": {"hello": "world"}}
    )


class VerifyDiRequestSchema(OpenAPISchema):
    """Request schema to verify a document secured with a data integrity proof."""

    secured_document = fields.Dict(
        data_key="securedDocument",
        required=True,
        metadata={
            "example": {
                "hello": "world",
                "proof": [
                    {
                        "cryptosuite": "eddsa-jcs-2022",
                        "proofPurpose": "assertionMethod",
                        "type": "DataIntegrityProof",
                        "verificationMethod": "did:key:\
                            z6MksxraKwH8GR7NKeQ4HVZAeRKvD76kfd6G7jm8MscbDmy8#\
                                z6MksxraKwH8GR7NKeQ4HVZAeRKvD76kfd6G7jm8MscbDmy8",
                        "proofValue": "zHtda8vV7kJQUPfSKiTGSQDhZfhkgtpnVziT7cdEzhu\
                            fjPjbeRmysHvizMJEox1eHR7xUGzNUj1V4yaKiLw7UA6E",
                    }
                ],
            }
        },
    )


class VerifyDiResponseSchema(OpenAPISchema):
    """Request schema to verifying a document secured with a data integrity proof."""

    verified = fields.Bool(metadata={"description": "Verified", "example": True})


@docs(tags=["vc"], summary="Add a DataIntegrityProof to a document.")
@request_schema(AddProofSchema())
@response_schema(AddProofResponseSchema(), description="")
@tenant_authentication
async def add_di_proof(request: web.BaseRequest):
    """Request handler for creating di proofs.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()

    document = body.get("document")
    options = body.get("options")

    try:
        options = DataIntegrityProofOptions.deserialize(options)
        async with context.session() as session:
            secured_document = await DataIntegrityManager(session).add_proof(
                document, options
            )

        return web.json_response({"securedDocument": secured_document}, status=201)

    except (WalletError, DataIntegrityManagerError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err


@docs(tags=["vc"], summary="Verify a document secured with a data integrity proof.")
@request_schema(VerifyDiRequestSchema())
@response_schema(VerifyDiResponseSchema(), description="")
@tenant_authentication
async def verify_di_secured_document(request: web.BaseRequest):
    """Request handler for verifying di proofs.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()

    secured_document = body.get("securedDocument")

    try:
        async with context.session() as session:
            verification_response = await DataIntegrityManager(session).verify_proof(
                secured_document
            )
        # response = {
        #     "verified": verification_response.verified,
        #     "verifiedDocument": verification_response.verified_document,
        #     "results": [result.serialize() for result in verification_response.results],
        # }
        if verification_response.verified:
            return web.json_response(
                {"verificationResults": verification_response.serialize()}, status=200
            )
        return web.json_response(
            {"verificationResults": verification_response.serialize()}, status=400
        )

    except (WalletError, DataIntegrityManagerError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.post("/vc/di/add-proof", add_di_proof),
            web.post("/vc/di/verify", verify_di_secured_document),
        ]
    )
