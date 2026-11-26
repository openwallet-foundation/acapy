"""Operations supporting SD-JWT creation and verification."""

import re
from typing import Any, List, Mapping, Optional, Tuple, Union

from aries_askar import Key
from jsonpath_ng.ext import parse as jsonpath_parse
from jsonpath_ng.jsonpath import Index
from marshmallow import fields
from sd_jwt.common import SDObj
from sd_jwt.issuer import SDJWTIssuer
from sd_jwt.verifier import SDJWTVerifier

from ..core.error import BaseError
from ..core.profile import Profile
from ..messaging.valid import StrOrDictField
from ..wallet.jwt import (
    JWTVerifyResult,
    JWTVerifyResultSchema,
    b64_to_dict,
    jwt_sign,
    jwt_verify,
)
from .base import BaseWallet
from .error import WalletError
from .key_type import ED25519, P256, KeyType
from .util import b64_to_bytes, bytes_to_b58

CLAIMS_NEVER_SD = ["iss", "iat", "exp", "cnf"]
SD_DIGESTS_KEY = "_sd"
SD_ALG_KEY = "_sd_alg"
SD_LIST_PREFIX = "..."

# Holder key types accepted in the cnf.jwk claim of an SD-JWT
HOLDER_JWK_KEY_TYPES = {
    ("OKP", "Ed25519"): ED25519,
    ("EC", "P-256"): P256,
}


class SDJWTError(BaseError):
    """SD-JWT Error."""


class SDJWTIssuerACAPy(SDJWTIssuer):
    """SDJWTIssuer class for ACA-Py implementation."""

    def __init__(
        self,
        user_claims: dict,
        issuer_key,
        holder_key,
        profile: Profile,
        headers: dict,
        did: Optional[str] = None,
        verification_method: Optional[str] = None,
        add_decoy_claims: bool = False,
        serialization_format: str = "compact",
    ):
        """Initialize an SDJWTIssuerACAPy instance."""
        self._user_claims = user_claims
        self._issuer_key = issuer_key
        self._holder_key = holder_key

        self.profile = profile
        self.headers = headers
        self.did = did
        self.verification_method = verification_method

        self._add_decoy_claims = add_decoy_claims
        self._serialization_format = serialization_format
        self.ii_disclosures = []

    async def _create_signed_jws(self) -> str:
        self.serialized_sd_jwt = await jwt_sign(
            self.profile,
            self.headers,
            self.sd_jwt_payload,
            self.did,
            self.verification_method,
        )

    async def issue(self) -> str:
        """Issue an sd-jwt."""
        self._check_for_sd_claim(self._user_claims)
        self._assemble_sd_jwt_payload()
        await self._create_signed_jws()
        self._create_combined()
        return self.sd_jwt_issuance


def create_json_paths(it, current_path="", path_list=None) -> List:
    """Create a json path for each element of the payload."""
    if path_list is None:
        path_list = []

    if isinstance(it, dict):
        for k, v in it.items():
            if not k.startswith(tuple(CLAIMS_NEVER_SD)):
                new_key = f"{current_path}.{k}" if current_path else k
                path_list.append(new_key)

                if isinstance(v, dict):
                    create_json_paths(v, new_key, path_list)
                elif isinstance(v, list):
                    for i, e in enumerate(v):
                        if isinstance(e, (dict, list)):
                            create_json_paths(e, f"{new_key}[{i}]", path_list)
                        else:
                            path_list.append(f"{new_key}[{i}]")
    elif isinstance(it, list):
        for i, e in enumerate(it):
            if isinstance(e, (dict, list)):
                create_json_paths(e, f"{current_path}[{i}]", path_list)
            else:
                path_list.append(f"{current_path}[{i}]")

    return path_list


def sort_sd_list(sd_list) -> List:
    """Sorts sd_list.

    Ensures that selectively disclosable claims deepest
    in the structure are handled first.
    """
    nested_claim_sort = [(len(sd.split(".")), sd) for sd in sd_list]
    nested_claim_sort.sort(reverse=True)
    return [sd[1] for sd in nested_claim_sort]


def separate_list_splices(non_sd_list) -> List:
    """Separate list splices in the non_sd_list into individual indices.

    This is necessary in order to properly construct the inverse of
    the claims which should not be selectively disclosable in the case
    of list splices.
    """
    for item in list(non_sd_list):
        if ":" in item:
            split = re.split(r"\[|\]|:", item)
            for i in range(int(split[1]), int(split[2])):
                non_sd_list.append(f"{split[0]}[{i}]")
            non_sd_list.remove(item)

    return non_sd_list


def create_sd_list(payload, non_sd_list) -> List:
    """Create a list of claims which will be selectively disclosable."""
    flattened_payload = create_json_paths(payload)
    separated_non_sd_list = separate_list_splices(non_sd_list)
    sd_list = [claim for claim in flattened_payload if claim not in separated_non_sd_list]
    return sort_sd_list(sd_list)



def wrap_list_item_as_sd(match) -> None:
    """Wrap a list element match as SDObj without changing sibling order.

    create_sd_list sorts index paths descending, so remove()+append() used to
    reverse array order (issue #3965). Prefer the jsonpath Index when present.
    """
    if isinstance(match.path, Index) and len(match.path.indices) == 1:
        match.context.value[match.path.indices[0]] = SDObj(match.value)
    else:
        idx = match.context.value.index(match.value)
        match.context.value[idx] = SDObj(match.value)


async def sd_jwt_sign(
    profile: Profile,
    headers: Mapping[str, Any],
    payload: Mapping[str, Any],
    non_sd_list: Optional[List] = None,
    did: Optional[str] = None,
    verification_method: Optional[str] = None,
) -> str:
    """Sign sd-jwt.

    Use non_sd_list and json paths for payload elements to create a list of
    claims that can be selectively disclosable. Use this list to wrap
    selectively disclosable claims with SDObj within payload,
    create SDJWTIssuerACAPy object, and call SDJWTIssuerACAPy.issue().
    """
    non_sd_list = non_sd_list or []
    sd_list = create_sd_list(payload, non_sd_list)
    for sd in sd_list:
        jsonpath_expression = jsonpath_parse(f"$.{sd}")
        matches = jsonpath_expression.find(payload)
        if len(matches) < 1:
            raise SDJWTError(f"Claim for {sd} not found in payload.")
        else:
            for match in matches:
                if isinstance(match.context.value, list):
                    wrap_list_item_as_sd(match)
                else:
                    match.context.value[SDObj(str(match.path))] = match.context.value.pop(
                        str(match.path)
                    )

    return await SDJWTIssuerACAPy(
        user_claims=payload,
        issuer_key=None,
        holder_key=None,
        profile=profile,
        headers=headers,
        did=did,
        verification_method=verification_method,
    ).issue()


class SDJWTVerifyResult(JWTVerifyResult):
    """Result from verifying SD-JWT."""

    class Meta:
        """SDJWTVerifyResult metadata."""

        schema_class = "SDJWTVerifyResultSchema"

    def __init__(
        self,
        headers,
        payload,
        valid,
        kid,
        disclosures,
    ):
        """Initialize an SDJWTVerifyResult instance."""
        super().__init__(
            headers,
            payload,
            valid,
            kid,
        )
        self.disclosures = disclosures


class SDJWTVerifyResultSchema(JWTVerifyResultSchema):
    """SDJWTVerifyResult schema."""

    class Meta:
        """SDJWTVerifyResultSchema metadata."""

        model_class = SDJWTVerifyResult

    disclosures = fields.List(
        fields.List(StrOrDictField()),
        metadata={
            "description": "Disclosure arrays associated with the SD-JWT",
            "example": [
                ["fx1iT_mETjGiC-JzRARnVg", "name", "Alice"],
                [
                    "n4-t3mlh8jSS6yMIT7QHnA",
                    "street_address",
                    {"_sd": ["kLZrLK7enwfqeOzJ9-Ss88YS3mhjOAEk9lr_ix2Heng"]},
                ],
            ],
        },
    )


class SDJWTVerifierACAPy(SDJWTVerifier):
    """SDJWTVerifier class for ACA-Py implementation."""

    def __init__(
        self,
        profile: Profile,
        sd_jwt_presentation: str,
        expected_aud: Union[str, None] = None,
        expected_nonce: Union[str, None] = None,
        serialization_format: str = "compact",
    ):
        """Initialize an SDJWTVerifierACAPy instance."""
        self.profile = profile
        self.sd_jwt_presentation = sd_jwt_presentation
        self._serialization_format = serialization_format
        self.expected_aud = expected_aud
        self.expected_nonce = expected_nonce

    async def _verify_sd_jwt(self) -> SDJWTVerifyResult:
        verified = await jwt_verify(
            self.profile,
            self._unverified_input_sd_jwt,
        )
        return SDJWTVerifyResult(
            headers=verified.headers,
            payload=verified.payload,
            valid=verified.valid,
            kid=verified.kid,
            disclosures=self._disclosures_list,
        )

    async def verify(self) -> SDJWTVerifyResult:
        """Verify an sd-jwt."""
        self._parse_sd_jwt(self.sd_jwt_presentation)
        self._create_hash_mappings(self._input_disclosures)
        self._disclosures_list = list(self._hash_to_decoded_disclosure.values())

        self.verified_sd_jwt = await self._verify_sd_jwt()
        self._check_disclosures_referenced(self.verified_sd_jwt.payload)

        if self.expected_aud or self.expected_nonce:
            if not (self.expected_aud and self.expected_nonce):
                raise ValueError(
                    "Either both expected_aud and expected_nonce must be provided "
                    "or both must be None"
                )
            await self._verify_key_binding_jwt(
                self.expected_aud,
                self.expected_nonce,
            )
        return self.verified_sd_jwt

    def _check_disclosures_referenced(self, payload: Mapping[str, Any]):
        """Check that every disclosure is referenced by a digest in the SD-JWT.

        Digests are collected from ``_sd`` arrays and ``{"...": digest}`` array
        elements in the issuer-signed payload, and from the values of disclosures
        that are themselves referenced. Any disclosure left unreferenced, or any
        digest that appears more than once, causes the SD-JWT to be rejected.
        """
        sd_alg = payload.get(SD_ALG_KEY, self.HASH_ALG["name"])
        if sd_alg != self.HASH_ALG["name"]:
            raise ValueError(f"Unsupported {SD_ALG_KEY}: {sd_alg}")

        referenced = set()
        pending = [payload]

        def _reference(digest, from_array: bool):
            if not isinstance(digest, str):
                raise ValueError("Invalid digest in SD-JWT")
            if digest in referenced:
                raise ValueError(f"Duplicate digest in SD-JWT: {digest}")
            referenced.add(digest)
            disclosure = self._hash_to_decoded_disclosure.get(digest)
            if disclosure is None:
                return
            expected_len = 2 if from_array else 3
            if not isinstance(disclosure, list) or len(disclosure) != expected_len:
                raise ValueError(f"Malformed disclosure for digest {digest}")
            pending.append(disclosure[-1])

        while pending:
            node = pending.pop()
            if isinstance(node, dict):
                digests = node.get(SD_DIGESTS_KEY, [])
                if not isinstance(digests, list):
                    raise ValueError(f"Invalid {SD_DIGESTS_KEY} in SD-JWT")
                for digest in digests:
                    _reference(digest, from_array=False)
                pending.extend(
                    value
                    for key, value in node.items()
                    if key not in (SD_DIGESTS_KEY, SD_ALG_KEY)
                )
            elif isinstance(node, list):
                for element in node:
                    if (
                        isinstance(element, dict)
                        and len(element) == 1
                        and SD_LIST_PREFIX in element
                    ):
                        _reference(element[SD_LIST_PREFIX], from_array=True)
                    else:
                        pending.append(element)

        if set(self._hash_to_decoded_disclosure) - referenced:
            raise ValueError("Disclosure not referenced by the SD-JWT")

    async def _verify_key_binding_jwt(
        self,
        expected_aud: Union[str, None] = None,
        expected_nonce: Union[str, None] = None,
    ):
        """Verify the key binding JWT against the holder key in the SD-JWT.

        The key binding JWT must be signed by the key in the ``cnf.jwk`` claim of
        the issuer-signed SD-JWT, and must carry the expected audience and nonce.
        """
        self._holder_public_key_payload = self.verified_sd_jwt.payload.get("cnf", None)

        if not self._holder_public_key_payload:
            raise ValueError("No holder public key in SD-JWT")

        holder_public_key_payload_jwk = self._holder_public_key_payload.get("jwk", None)
        if not holder_public_key_payload_jwk:
            raise ValueError(
                "The holder_public_key_payload is malformed. "
                "It doesn't contain the claim jwk: "
                f"{self._holder_public_key_payload}"
            )

        holder_verkey, holder_key_type = _holder_key_from_jwk(
            holder_public_key_payload_jwk
        )

        try:
            encoded_headers, encoded_payload, encoded_signature = (
                self._unverified_input_key_binding_jwt.split(".")
            )
            kb_jwt_headers = b64_to_dict(encoded_headers)
            kb_jwt_payload = b64_to_dict(encoded_payload)
            signature = b64_to_bytes(encoded_signature, urlsafe=True)
        except Exception as err:
            raise ValueError("Malformed key binding JWT") from err

        if kb_jwt_headers.get("alg") != holder_key_type.jws_algorithm:
            raise ValueError("Key binding JWT alg does not match the holder key")

        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            try:
                valid = await wallet.verify_message(
                    f"{encoded_headers}.{encoded_payload}".encode(),
                    signature,
                    from_verkey=holder_verkey,
                    key_type=holder_key_type,
                )
            except WalletError:
                valid = False
        if not valid:
            raise ValueError("Key binding JWT is not signed by the holder key")

        if kb_jwt_headers.get("typ") != self.KB_JWT_TYP_HEADER:
            raise ValueError("Invalid header typ")
        if kb_jwt_payload.get("aud") != expected_aud:
            raise ValueError("Invalid audience")
        if kb_jwt_payload.get("nonce") != expected_nonce:
            raise ValueError("Invalid nonce")


def _holder_key_from_jwk(jwk: Mapping) -> Tuple[str, KeyType]:
    """Return the base58 public key and key type for a holder JWK."""
    if not isinstance(jwk, Mapping):
        raise ValueError("The holder key in cnf.jwk must be a JSON object")
    key_type = HOLDER_JWK_KEY_TYPES.get((jwk.get("kty"), jwk.get("crv")))
    if not key_type:
        raise ValueError(
            "Unsupported holder key in cnf.jwk: "
            f"kty={jwk.get('kty')}, crv={jwk.get('crv')}"
        )
    public_jwk = {key: value for key, value in jwk.items() if key != "d"}
    try:
        public_bytes = Key.from_jwk(public_jwk).get_public_bytes()
    except Exception as err:
        raise ValueError("Unable to parse the holder key in cnf.jwk") from err
    return bytes_to_b58(public_bytes), key_type


async def sd_jwt_verify(
    profile: Profile,
    sd_jwt_presentation: str,
    expected_aud: Optional[str] = None,
    expected_nonce: Optional[str] = None,
) -> SDJWTVerifyResult:
    """Verify sd-jwt using SDJWTVerifierACAPy.verify()."""
    sd_jwt_verifier = SDJWTVerifierACAPy(
        profile, sd_jwt_presentation, expected_aud, expected_nonce
    )
    return await sd_jwt_verifier.verify()
