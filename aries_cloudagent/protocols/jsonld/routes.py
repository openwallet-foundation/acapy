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

from .create_verify_data import create_verify_data

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

def b64encode(str):
    return str_to_b64(str, urlsafe=True, pad=False)

def b64decode(bytes):
    return b64_to_str(bytes, urlsafe=True)

def create_jws(encoded_header, verify_data):
    return (encoded_header + "." + verify_data).encode("ascii")


async def jws_sign(verify_data, verkey, wallet):
    header = {
        "alg": "EdDSA",
        "b64": False,
        "crit": ["b64"]
    }

    encoded_header = b64encode(json.dumps(header))

    jws_to_sign = create_jws(encoded_header, verify_data)

    encoded_signature = await wallet.sign_message(jws_to_sign, verkey)

    #encoded_signature = b64encode(signature)
    return encoded_header + ".." + bytes_to_b64(encoded_signature, urlsafe=True, pad=False)


def verify_jws_header(header):
    if not( header['alg'] == "EdDSA" and
      header['b64'] == False and
      isinstance(header['crit'], list) and
      len(header['crit']) == 1 and
      header['crit'][0] == "b64"
    ) and len(header) == 3:
        raise Exception("Invalid JWS header parameters for Ed25519Signature2018.")


async def jws_verify(verify_data, signature, public_key, wallet):
    encoded_header, _,  encoded_signature = signature.partition("..")
    decoded_header = json.loads(b64decode(encoded_header))

    verify_jws_header(decoded_header)

    decoded_signature = b64decode(encoded_signature)

    jws_to_verify = create_jws(encoded_header, verify_data)

    return await wallet.verify_message(jws_to_verify, decoded_signature, public_key)


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

    body = await request.json()
    verkey = body.get("verkey")
    doc = body.get("doc")
    credential = doc['credential']
    signature_options = doc['options']

    framed, verify_data_hex_string = create_verify_data(credential, signature_options)

    jws = await jws_sign(verify_data_hex_string, verkey, wallet)

    document_with_proof = {
        **credential,
        "proof": {
            **signature_options,
            "jws": jws
        }
    }

    return web.json_response({
        "signed_doc": document_with_proof,
    })


class VerifyRequestSchema(Schema):
    """Request schema for signing a jsonld doc."""
    issuerkey = fields.Str(required=True, description="verkey to use for issuer verification")
    holderkey = fields.Str(required=True, description="verkey to use for holder verification")
    doc = fields.Dict(required=True, description="JSON-LD Doc to verify")

class VerifyResponseSchema(Schema):
    """Response schema for verification result."""
    valid = fields.Bool(required=True)


@docs(tags=["jsonld"], summary="Verify a JSON-LD structure.")
@request_schema(VerifyRequestSchema())
@response_schema(VerifyResponseSchema(), 200)
async def verify(request: web.BaseRequest):
    """
    Request handler for signing a jsonld doc.

    Args:
        request: aiohttp request object

    """
    context = request.app["request_context"]
    wallet: BaseWallet = await context.inject(BaseWallet)
    if not wallet:
        raise web.HTTPForbidden()

    body = await request.json()
    issuerkey = body.get("issuekey")
    holderkey = body.get("holderkey")
    doc = body.get("doc")

    credential = doc['credential']
    #signature_options = doc['options']

    framed, verify_data_hex_string = create_verify_data(credential, credential['proof'])

    #jws = await jws_sign(verify_data_hex_string, verkey, wallet)
    valid = await jws_verify(verify_data_hex_string, framed['proof']['jws'], holderkey, wallet)
    #document_with_proof = {
    #    **framed,
    #    "proof": {
    #        **signature_options,
    #        "jws": jws
    #    }
    #}

    #holder_valid = await wallet.verify_message(verify_data_hex_string, framed['proof']['jws'], holderkey)

    return web.json_response({
        "valid": valid,
    })



async def register(app: web.Application):
    """Register routes."""

    app.add_routes([web.post("/jsonld/sign", sign)])
    app.add_routes([web.post("/jsonld/verify", verify)])

# examples here: https://github.com/w3c-ccg/vc-examples/tree/master/docs/chapi-http-edu