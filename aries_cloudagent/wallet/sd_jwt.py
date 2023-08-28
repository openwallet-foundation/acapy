"""Operations supporting SD-JWT creation and verification."""

import re
from typing import Any, List, Mapping, Optional
from marshmallow import fields
from jsonpath_ng.ext import parse
from sd_jwt.common import SDObj
from sd_jwt.issuer import SDJWTIssuer
from sd_jwt.verifier import SDJWTVerifier

from ..core.profile import Profile
from ..wallet.jwt import JWTVerifyResult, JWTVerifyResultSchema, jwt_sign, jwt_verify
from ..core.error import BaseError
from ..messaging.valid import StrOrDictField


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
    """
    Sorts sd_list.

    Ensures that selectively disclosable claims deepest
    in the structure are handled first.
    """
    nested_claim_sort = [(len(sd.split(".")), sd) for sd in sd_list]
    nested_claim_sort.sort(reverse=True)
    return [sd[1] for sd in nested_claim_sort]


def separate_list_splices(non_sd_list) -> List:
    """
    Separate list splices in the non_sd_list into individual indices.

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
    non_sd_list: List = [],
    did: Optional[str] = None,
    verification_method: Optional[str] = None,
) -> str:
    """
    Sign sd-jwt.

    Use non_sd_list and json paths for payload elements to create a list of
    claims that can be selectively disclosable. Use this list to wrap
    selectively disclosable claims with SDObj within payload,
    create SDJWTIssuerACAPy object, and call SDJWTIssuerACAPy.issue().
    """
    sd_list = create_sd_list(payload, non_sd_list)
    for sd in sd_list:
        jsonpath_expression = parse(f"$.{sd}")
        matches = jsonpath_expression.find(payload)
        if len(matches) < 1:
            raise SDJWTError(f"Claim for {sd} not found in payload.")
        else:
            for match in matches:
                if str(match.path) not in CLAIMS_NEVER_SD:
                    if isinstance(match.context.value, list):
                        match.context.value.remove(match.value)
                        match.context.value.append(SDObj(match.value))
                    else:
                        match.context.value[
                            SDObj(str(match.path))
                        ] = match.context.value.pop(str(match.path))

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
        serialization_format: str = "compact",
    ):
        """Initialize an SDJWTVerifierACAPy instance."""
        self.profile = profile
        self.sd_jwt_presentation = sd_jwt_presentation
        self._serialization_format = serialization_format

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
        return await self._verify_sd_jwt()


async def sd_jwt_verify(
    profile: Profile, sd_jwt_presentation: str
) -> SDJWTVerifyResult:
    """Verify sd-jwt using SDJWTVerifierACAPy.verify()."""
    sd_jwt_verifier = SDJWTVerifierACAPy(profile, sd_jwt_presentation)
    verified = await sd_jwt_verifier.verify()
    return verified
