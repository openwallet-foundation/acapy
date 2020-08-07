"""Sign and verify functions for json-ld based credentials."""

import json

from ...wallet.util import (
    b58_to_bytes,
    b64_to_bytes,
    b64_to_str,
    bytes_to_b58,
    bytes_to_b64,
    str_to_b64,
)

from .create_verify_data import create_verify_data


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
    """Url Safe B64 Encode."""
    return str_to_b64(str, urlsafe=True, pad=False)


def b64decode(bytes):
    """Url Safe B64 Decode."""
    return b64_to_str(bytes, urlsafe=True)


def create_jws(encoded_header, verify_data):
    """Compose JWS."""
    return (encoded_header + ".").encode("utf-8") + verify_data


async def jws_sign(verify_data, verkey, wallet):
    """Sign JWS."""

    header = {"alg": "EdDSA", "b64": False, "crit": ["b64"]}

    encoded_header = b64encode(json.dumps(header))

    jws_to_sign = create_jws(encoded_header, verify_data)

    signature = await wallet.sign_message(jws_to_sign, verkey)

    encoded_signature = bytes_to_b64(signature, urlsafe=True, pad=False)

    return encoded_header + ".." + encoded_signature


def verify_jws_header(header):
    """Check header requirements."""

    if (
        not (
            header["alg"] == "EdDSA"
            and header["b64"] is False
            and isinstance(header["crit"], list)
            and len(header["crit"]) == 1
            and header["crit"][0] == "b64"
        )
        and len(header) == 3
    ):
        raise Exception("Invalid JWS header parameters for Ed25519Signature2018.")


async def jws_verify(verify_data, signature, public_key, wallet):
    """Detatched jws verify handling."""

    encoded_header, _, encoded_signature = signature.partition("..")
    decoded_header = json.loads(b64decode(encoded_header))

    verify_jws_header(decoded_header)

    decoded_signature = b64_to_bytes(encoded_signature, urlsafe=True)

    jws_to_verify = create_jws(encoded_header, verify_data)

    verified = await wallet.verify_message(jws_to_verify, decoded_signature, public_key)

    return verified


async def sign_credential(credential, signature_options, verkey, wallet):
    """Sign Credential."""

    framed, verify_data_hex_string = create_verify_data(credential, signature_options)
    verify_data_bytes = bytes.fromhex(verify_data_hex_string)
    jws = await jws_sign(verify_data_bytes, verkey, wallet)
    document_with_proof = {**credential, "proof": {**signature_options, "jws": jws}}
    return document_with_proof


async def verify_credential(doc, verkey, wallet):
    """Verify credential."""

    framed, verify_data_hex_string = create_verify_data(doc, doc["proof"])
    verify_data_bytes = bytes.fromhex(verify_data_hex_string)
    valid = await jws_verify(verify_data_bytes, framed["proof"]["jws"], verkey, wallet)
    return valid
