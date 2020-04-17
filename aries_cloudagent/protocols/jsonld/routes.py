"""jsonld admin routes."""
import datetime
import json
from pyld import jsonld

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from aries_cloudagent.wallet.base import BaseWallet

from marshmallow import fields, Schema

from ...wallet.util import (
    b58_to_bytes,
    b64_to_bytes,
    b64_to_str,
    bytes_to_b58,
    bytes_to_b64,
    set_urlsafe_b64,
    str_to_b64,
    unpad,
)


class SignRequestSchema(Schema):
    """Request schema for signing a jsonld doc."""
    verkey = fields.Str(required=True, description="verkey to use for signing")
    doc = fields.Dict(required=True, description="JSON-LD Doc to sign")

class SignResponseSchema(Schema):
    """Response schema for a signed jsonld doc."""
    signed_doc = fields.Dict(required=True)

MULTIBASE_B58_BTC = "z"
MULTICODEC_ED25519_PUB = b"\xed"

def did_key(verkey: str) -> str:
    """Qualify verkey into DID key if need be."""

    if verkey.startswith(f"did:key:{MULTIBASE_B58_BTC}"):
        return verkey

    return f"did:key:{MULTIBASE_B58_BTC}" + bytes_to_b58(
        MULTICODEC_ED25519_PUB + b58_to_bytes(verkey)
    )



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
    credential = doc['credential']
    options = doc['options']

    normalized = jsonld.normalize(
        credential, {'algorithm': 'URDNA2015', 'format': 'application/n-quads'})

    message_bin = normalized #.encode("ascii")
    jose_header = {
        "alg": "EdDSA",
        "kid": did_key(verkey),
    }
    encoded_header = str_to_b64(json.dumps(jose_header), urlsafe=True, pad=False)
    signature_bin = await wallet.sign_message((encoded_header + "." + message_bin).encode("ascii"), verkey)
    proof = {
        "type": "Ed25519Signature2018",
        "created": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verificationMethod": options["verificationMethod"],
        "proofPurpose": options["proofPurpose"],
        "jws": encoded_header + ".." + bytes_to_b64(signature_bin, urlsafe=True, pad=False)
    }
    credential['proof'] = proof

    return web.json_response({
        "signed_doc": doc,
    })


async def register(app: web.Application):
    """Register routes."""

    app.add_routes([web.post("/jsonld/sign", sign)])
