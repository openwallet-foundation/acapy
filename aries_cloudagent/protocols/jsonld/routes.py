"""jsonld admin routes."""
import json
from pyld import jsonld

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from aries_cloudagent.wallet.base import BaseWallet

from marshmallow import fields, Schema

from aries_cloudagent.wallet.util import bytes_to_b64
from ...connections.models.connection_record import ConnectionRecord
from ...storage.error import StorageNotFoundError


class SignRequestSchema(Schema):
    """Request schema for signing a jsonld doc."""
    verkey = fields.Str(required=True, description="verkey to use for signing")
    doc = fields.Dict(required=True, description="JSON-LD Doc to sign")

class SignResponseSchema(Schema):
    """Response schema for a signed jsonld doc."""
    signed_doc = fields.Dict(required=True)

@docs(tags=["jsonld"], summary="Sign a JSON-LD structure and return it")
@request_schema(SignRequestSchema())
@response_schema(SignResponseSchema(), 200)
async def sign(request: web.BaseRequest):
    """
    Request handler for signing a jsonld doc.

    Args:
        request: aiohttp request object

    """
    context = request.app["request_context"]
    wallet: BaseWallet = await context.inject(BaseWallet)
    if not wallet:
        raise web.HTTPForbidden()
    #connection_id = request.match_info["id"] #comes from URL

    body = await request.json()
    verkey = body.get("verkey")
    doc = body.get("doc")
    #comment = body.get("comment")
    normalized = jsonld.normalize(
        doc['credential'], {'algorithm': 'URDNA2015', 'format': 'application/n-quads'})
    #message_bin = json.dumps(doc).encode("ascii")
    message_bin = normalized.encode("ascii")
    signature_bin = await wallet.sign_message(message_bin, verkey)


    return web.json_response({
        "signed_doc": {
            'signature': bytes_to_b64(signature_bin, urlsafe=True),
        }
    })


async def register(app: web.Application):
    """Register routes."""

    app.add_routes([web.post("/jsonld/sign", sign)])
