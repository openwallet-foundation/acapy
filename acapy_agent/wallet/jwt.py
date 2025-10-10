"""Operations supporting JWT creation and verification."""

import json
import logging
from typing import Any, Mapping, Optional

from marshmallow import fields

from acapy_agent.wallet.keys.manager import (
    MultikeyManager,
    key_type_from_multikey,
    multikey_to_verkey,
)

from ..core.profile import Profile
from ..messaging.jsonld.error import BadJWSHeaderError
from ..messaging.models.base import BaseModel, BaseModelSchema
from .base import BaseWallet
from .default_verification_key_strategy import BaseVerificationKeyStrategy
from .util import b64_to_bytes, bytes_to_b64

LOGGER = logging.getLogger(__name__)
SUPPORTED_JWT_ALGS = ("EdDSA", "ES256")


def dict_to_b64(value: Mapping[str, Any]) -> str:
    """Encode a dictionary as a b64 string."""
    return bytes_to_b64(json.dumps(value).encode(), urlsafe=True, pad=False)


def b64_to_dict(value: str) -> Mapping[str, Any]:
    """Decode a dictionary from a b64 encoded value."""
    return json.loads(b64_to_bytes(value, urlsafe=True))


def nym_to_did(value: str) -> str:
    """Return a did from nym if passed value is nym, else return value."""
    return value if value.startswith("did:") else f"did:sov:{value}"


def did_lookup_name(value: str) -> str:
    """Return the value used to lookup a DID in the wallet.

    If value is did:sov, return the unqualified value. Else, return value.
    """
    return value.split(":", 3)[2] if value.startswith("did:sov:") else value


async def jwt_sign(
    profile: Profile,
    headers: Mapping[str, Any],
    payload: Mapping[str, Any],
    did: Optional[str] = None,
    verification_method: Optional[str] = None,
) -> str:
    """Create a signed JWT given headers, payload, and signing DID or DID URL."""
    if verification_method is None:
        if did is None:
            raise ValueError("did or verificationMethod required.")

        did = nym_to_did(did)

        verkey_strat = profile.inject(BaseVerificationKeyStrategy)
        verification_method = await verkey_strat.get_verification_method_id_for_did(
            did, profile
        )

    async with profile.session() as session:
        wallet = session.inject(BaseWallet)
        key_manager = MultikeyManager(session)
        key_info = await key_manager.resolve_and_bind_kid(verification_method)
        multikey = key_info["multikey"]
        key_type = key_type_from_multikey(multikey)
        public_key_base58 = multikey_to_verkey(multikey)

        header_alg = key_type.jws_algorithm
        if not header_alg:
            raise ValueError(f"DID key type '{key_type}' cannot be used for JWS")

        if not headers.get("typ", None):
            headers["typ"] = "JWT"
        headers = {
            **headers,
            "alg": header_alg,
            "kid": verification_method,
        }
        encoded_headers = dict_to_b64(headers)
        encoded_payload = dict_to_b64(payload)

        LOGGER.info(f"jwt sign: {verification_method}")
        sig_bytes = await wallet.sign_message(
            f"{encoded_headers}.{encoded_payload}".encode(), public_key_base58
        )

    sig = bytes_to_b64(sig_bytes, urlsafe=True, pad=False)
    return f"{encoded_headers}.{encoded_payload}.{sig}"


class JWTVerifyResult(BaseModel):
    """Result from verify."""

    class Meta:
        """JWTVerifyResult metadata."""

        schema_class = "JWTVerifyResultSchema"

    def __init__(
        self,
        headers: Mapping[str, Any],
        payload: Mapping[str, Any],
        valid: bool,
        kid: str,
    ):
        """Initialize a JWTVerifyResult instance."""
        self.headers = headers
        self.payload = payload
        self.valid = valid
        self.kid = kid


class JWTVerifyResultSchema(BaseModelSchema):
    """JWTVerifyResult schema."""

    class Meta:
        """JWTVerifyResultSchema metadata."""

        model_class = JWTVerifyResult

    headers = fields.Dict(
        required=True, metadata={"description": "Headers from verified JWT."}
    )
    payload = fields.Dict(
        required=True, metadata={"description": "Payload from verified JWT"}
    )
    valid = fields.Bool(required=True)
    kid = fields.Str(required=True, metadata={"description": "kid of signer"})
    error = fields.Str(required=False, metadata={"description": "Error text"})


async def jwt_verify(profile: Profile, jwt: str) -> JWTVerifyResult:
    """Verify a JWT and return the headers and payload."""
    encoded_headers, encoded_payload, encoded_signature = jwt.split(".", 3)
    headers = b64_to_dict(encoded_headers)
    if "alg" not in headers:
        raise BadJWSHeaderError("Missing 'alg' parameter in JWS header")
    if "kid" not in headers:
        raise BadJWSHeaderError("Missing 'kid' parameter in JWS header")
    if headers["alg"] not in SUPPORTED_JWT_ALGS:
        raise BadJWSHeaderError(
            f"Unsupported 'alg' value in JWS header: '{headers['alg']}'. "
            f"Supported algorithms: {', '.join(SUPPORTED_JWT_ALGS)}"
        )

    payload = b64_to_dict(encoded_payload)
    verification_method = headers["kid"]
    decoded_signature = b64_to_bytes(encoded_signature, urlsafe=True)

    async with profile.session() as session:
        key_manager = MultikeyManager(session)
        multikey = await key_manager.resolve_multikey_from_verification_method_id(
            verification_method
        )
        key_type = key_type_from_multikey(multikey)
        public_key_base58 = multikey_to_verkey(multikey)

        wallet = session.inject(BaseWallet)
        valid = await wallet.verify_message(
            f"{encoded_headers}.{encoded_payload}".encode(),
            decoded_signature,
            from_verkey=public_key_base58,
            key_type=key_type,
        )

    return JWTVerifyResult(headers, payload, valid, verification_method)
