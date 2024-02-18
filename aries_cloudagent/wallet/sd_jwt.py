"""Operations supporting SD-JWT creation and verification."""

import re
from typing import Any, List, Mapping, Optional, Union

from jsonpath_ng.ext import parse as jsonpath_parse
from marshmallow import fields
from sd_jwt.common import SDObj
from sd_jwt.issuer import SDJWTIssuer
from sd_jwt.verifier import SDJWTVerifier

from ..core.error import BaseError
from ..core.profile import Profile
from ..messaging.valid import StrOrDictField
from ..wallet.jwt import JWTVerifyResult, JWTVerifyResultSchema, jwt_sign, jwt_verify

CLAIMS_NEVER_SD = ["iss", "iat", "exp", "cnf"]


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
    for item in non_sd_list:
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
    sd_list = [
        claim for claim in flattened_payload if claim not in separated_non_sd_list
    ]
    return sort_sd_list(sd_list)


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
                    match.context.value.remove(match.value)
                    match.context.value.append(SDObj(match.value))
                else:
                    match.context.value[SDObj(str(match.path))] = (
                        match.context.value.pop(str(match.path))
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

    async def _verify_key_binding_jwt(
        self,
        expected_aud: Union[str, None] = None,
        expected_nonce: Union[str, None] = None,
    ):
        verified_kb_jwt = await jwt_verify(
            self.profile, self._unverified_input_key_binding_jwt
        )
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

        if verified_kb_jwt.headers["typ"] != self.KB_JWT_TYP_HEADER:
            raise ValueError("Invalid header typ")
        if verified_kb_jwt.payload["aud"] != expected_aud:
            raise ValueError("Invalid audience")
        if verified_kb_jwt.payload["nonce"] != expected_nonce:
            raise ValueError("Invalid nonce")


async def sd_jwt_verify(
    profile: Profile,
    sd_jwt_presentation: str,
    expected_aud: str = None,
    expected_nonce: str = None,
) -> SDJWTVerifyResult:
    """Verify sd-jwt using SDJWTVerifierACAPy.verify()."""
    sd_jwt_verifier = SDJWTVerifierACAPy(
        profile, sd_jwt_presentation, expected_aud, expected_nonce
    )
    return await sd_jwt_verifier.verify()
