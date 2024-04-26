"""Operations supporting JWT creation and verification."""

import json
import logging
from typing import Any, Mapping, Optional

from marshmallow import fields
from pydid import DIDUrl, Resource, VerificationMethod

from ..core.profile import Profile
from ..messaging.jsonld.error import BadJWSHeaderError, InvalidVerificationMethod
from ..messaging.jsonld.routes import SUPPORTED_VERIFICATION_METHOD_TYPES
from ..messaging.models.base import BaseModel, BaseModelSchema
from ..resolver.did_resolver import DIDResolver
from .default_verification_key_strategy import BaseVerificationKeyStrategy
from .base import BaseWallet
from .key_type import ED25519
from .util import b64_to_bytes, bytes_to_b64

LOGGER = logging.getLogger(__name__)


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
        if not verification_method:
            raise ValueError("Could not determine verification method from DID")
    else:
        # We look up keys by did for now
        did = DIDUrl.parse(verification_method).did
        if not did:
            raise ValueError("DID URL must be absolute")

    if not headers.get("typ", None):
        headers["typ"] = "JWT"
    headers = {
        **headers,
        "alg": "EdDSA",
        "kid": verification_method,
    }
    encoded_headers = dict_to_b64(headers)
    encoded_payload = dict_to_b64(payload)

    async with profile.session() as session:
        wallet = session.inject(BaseWallet)
        LOGGER.info(f"jwt sign: {did}")
        did_info = await wallet.get_local_did(did_lookup_name(did))
        sig_bytes = await wallet.sign_message(
            f"{encoded_headers}.{encoded_payload}".encode(), did_info.verkey
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


async def resolve_public_key_by_kid_for_verify(profile: Profile, kid: str) -> str:
    """Resolve public key material from a kid."""
    resolver = profile.inject(DIDResolver)
    vmethod: Resource = await resolver.dereference(
        profile,
        kid,
    )

    if not isinstance(vmethod, VerificationMethod):
        raise InvalidVerificationMethod(
            "Dereferenced resource is not a verification method"
        )

    if not isinstance(vmethod, SUPPORTED_VERIFICATION_METHOD_TYPES):
        raise InvalidVerificationMethod(
            f"Dereferenced method {type(vmethod).__name__} is not supported"
        )

    return vmethod.material


async def jwt_verify(profile: Profile, jwt: str) -> JWTVerifyResult:
    """Verify a JWT and return the headers and payload."""
    encoded_headers, encoded_payload, encoded_signature = jwt.split(".", 3)
    headers = b64_to_dict(encoded_headers)
    if "alg" not in headers or headers["alg"] != "EdDSA" or "kid" not in headers:
        raise BadJWSHeaderError(
            "Invalid JWS header parameters for Ed25519Signature2018."
        )

    payload = b64_to_dict(encoded_payload)
    verification_method = headers["kid"]
    decoded_signature = b64_to_bytes(encoded_signature, urlsafe=True)

    async with profile.session() as session:
        verkey = await resolve_public_key_by_kid_for_verify(
            profile, verification_method
        )
        wallet = session.inject(BaseWallet)
        valid = await wallet.verify_message(
            f"{encoded_headers}.{encoded_payload}".encode(),
            decoded_signature,
            verkey,
            ED25519,
        )

    return JWTVerifyResult(headers, payload, valid, verification_method)
