from base64 import urlsafe_b64decode
import json
import pytest

from ...wallet.did_method import KEY
from ...wallet.key_type import ED25519
from ...wallet.jwt import jwt_sign
from ..sd_jwt import SDJWTVerifyResult, sd_jwt_sign, sd_jwt_verify


@pytest.fixture
def create_address_payload():
    return {
        "address": {
            "street_address": "123 Main St",
            "locality": "Anytown",
            "region": "Anystate",
            "country": "US",
        },
        "iss": "https://example.com/issuer",
        "iat": 1683000000,
        "exp": 1883000000,
    }


class TestSDJWT:
    """Tests for JWT sign and verify using dids."""

    seed = "testseed000000000000000000000001"
    headers = {}

    @pytest.mark.asyncio
    async def test_sign_with_did_key_and_verify(self, profile, in_memory_wallet):
        did_info = await in_memory_wallet.create_local_did(KEY, ED25519, self.seed)
        verification_method = None
        payload = {
            "sub": "user_42",
            "given_name": "John",
            "family_name": "Doe",
            "email": "johndoe@example.com",
            "phone_number": "+1-202-555-0101",
            "phone_number_verified": True,
            "address": {
                "street_address": "123 Main St",
                "locality": "Anytown",
                "region": "Anystate",
                "country": "US",
            },
            "birthdate": "1940-01-01",
            "updated_at": 1570000000,
            "nationalities": ["US", "DE", "SA"],
            "iss": "https://example.com/issuer",
            "iat": 1683000000,
            "exp": 1883000000,
        }
        non_sd_list = [
            "given_name",
            "family_name",
            "birthdate",
        ]
        signed = await sd_jwt_sign(
            profile,
            self.headers,
            payload,
            non_sd_list,
            did_info.did,
            verification_method,
        )
        assert signed

        # Separate the jwt from the disclosures
        signed_sd_jwt = signed.split("~")[0]

        # Determine which selectively disclosable attributes to reveal
        revealed = ["sub", "phone_number", "phone_number_verified"]

        for disclosure in signed.split("~")[1:-1]:
            # Decode the disclosures
            padded = f"{disclosure}{'=' * divmod(len(disclosure),4)[1]}"
            decoded = json.loads(urlsafe_b64decode(padded).decode("utf-8"))
            # Add the disclosures associated with the claims to be revealed
            if decoded[1] in revealed:
                signed_sd_jwt = signed_sd_jwt + "~" + disclosure

        verified = await sd_jwt_verify(profile, f"{signed_sd_jwt}~")
        assert verified.valid
        # Validate that the non-selectively disclosable claims are visible in the payload
        assert verified.payload["given_name"] == payload["given_name"]
        assert verified.payload["family_name"] == payload["family_name"]
        assert verified.payload["birthdate"] == payload["birthdate"]
        # Validate that the revealed claims are in the disclosures
        assert sorted(revealed) == sorted(
            [disclosure[1] for disclosure in verified.disclosures]
        )
        assert verified.payload["iss"] == payload["iss"]
        assert verified.payload["iat"] == payload["iat"]
        assert verified.payload["exp"] == payload["exp"]

    @pytest.mark.asyncio
    async def test_flat_structure(
        self, profile, in_memory_wallet, create_address_payload
    ):
        did_info = await in_memory_wallet.create_local_did(KEY, ED25519, self.seed)
        verification_method = None
        non_sd_list = [
            "address.street_address",
            "address.locality",
            "address.region",
            "address.country",
        ]
        signed = await sd_jwt_sign(
            profile,
            self.headers,
            create_address_payload,
            non_sd_list,
            did_info.did,
            verification_method,
        )
        assert signed

        verified = await sd_jwt_verify(profile, signed)
        assert isinstance(verified, SDJWTVerifyResult)
        assert verified.valid
        assert verified.payload["_sd"]
        assert verified.payload["_sd_alg"]
        assert verified.disclosures[0][1] == "address"
        assert verified.disclosures[0][2] == {
            "street_address": "123 Main St",
            "locality": "Anytown",
            "region": "Anystate",
            "country": "US",
        }

    @pytest.mark.asyncio
    async def test_nested_structure(
        self, profile, in_memory_wallet, create_address_payload
    ):
        did_info = await in_memory_wallet.create_local_did(KEY, ED25519, self.seed)
        verification_method = None
        non_sd_list = ["address"]

        signed = await sd_jwt_sign(
            profile,
            self.headers,
            create_address_payload,
            non_sd_list,
            did_info.did,
            verification_method,
        )
        assert signed

        verified = await sd_jwt_verify(profile, signed)
        assert isinstance(verified, SDJWTVerifyResult)
        assert verified.valid
        assert len(verified.payload["address"]["_sd"]) >= 4
        assert verified.payload["_sd_alg"]
        sd_claims = ["street_address", "region", "locality", "country"]
        assert sorted(sd_claims) == sorted([claim[1] for claim in verified.disclosures])

    @pytest.mark.asyncio
    async def test_recursive_nested_structure(
        self, profile, in_memory_wallet, create_address_payload
    ):
        did_info = await in_memory_wallet.create_local_did(KEY, ED25519, self.seed)
        verification_method = None
        non_sd_list = []

        signed = await sd_jwt_sign(
            profile,
            self.headers,
            create_address_payload,
            non_sd_list,
            did_info.did,
            verification_method,
        )
        assert signed

        verified = await sd_jwt_verify(profile, signed)
        assert isinstance(verified, SDJWTVerifyResult)
        assert verified.valid
        assert "address" not in verified.payload
        assert verified.payload["_sd"]
        assert verified.payload["_sd_alg"]
        sd_claims = ["street_address", "region", "locality", "country"]
        for disclosure in verified.disclosures:
            if disclosure[1] == "address":
                assert isinstance(disclosure[2], dict)
                assert len(disclosure[2]["_sd"]) >= 4
            else:
                assert disclosure[1] in sd_claims

    @pytest.mark.asyncio
    async def test_list_splice(self, profile, in_memory_wallet):
        did_info = await in_memory_wallet.create_local_did(KEY, ED25519, self.seed)
        payload = {"nationalities": ["US", "DE", "SA"]}
        verification_method = None
        non_sd_list = ["nationalities", "nationalities[1:3]"]

        signed = await sd_jwt_sign(
            profile,
            self.headers,
            payload,
            non_sd_list,
            did_info.did,
            verification_method,
        )
        assert signed

        verified = await sd_jwt_verify(profile, signed)
        assert isinstance(verified, SDJWTVerifyResult)
        assert verified.valid
        for nationality in verified.payload["nationalities"]:
            if isinstance(nationality, dict):
                assert nationality["..."]
                assert len(nationality) == 1
            else:
                assert nationality in payload["nationalities"]
        assert verified.payload["_sd_alg"]
        assert verified.disclosures[0][1] == "US"

    @pytest.mark.asyncio
    async def test_sd_jwt_key_binding(self, profile, in_memory_wallet):
        did_info = await in_memory_wallet.create_local_did(KEY, ED25519, self.seed)
        verification_method = None

        payload = {
            "given_name": "John",
            "family_name": "Doe",
            "iss": "https://example.com/issuer",
            "iat": 1683000000,
            "exp": 1883000000,
            "cnf": {
                "jwk": {
                    "kty": "EC",
                    "crv": "P-256",
                    "x": "TCAER19Zvu3OHF4j4W4vfSVoHIP1ILilDls7vCeGemc",
                    "y": "ZxjiWWbZMQGHVWKVQ4hbSIirsVfuecCE6t4jT9F2HZQ",
                }
            },
        }
        signed = await sd_jwt_sign(
            profile,
            self.headers,
            payload,
            did=did_info.did,
            verification_method=verification_method,
        )
        assert signed

        # Key binding
        headers_kb = {"alg": "ES256", "typ": "kb+jwt"}
        payload_kb = {
            "nonce": "1234567890",
            "aud": "https://example.com/verifier",
            "iat": 1688160483,
        }
        signed_kb = await jwt_sign(
            profile,
            headers_kb,
            payload_kb,
            did_info.did,
            verification_method,
        )
        assert signed_kb

        assert await sd_jwt_verify(
            profile,
            f"{signed}{signed_kb}",
            expected_aud=payload_kb["aud"],
            expected_nonce=payload_kb["nonce"],
        )

    test_input = [
        (
            "Either both expected_aud and expected_nonce must be provided or both must be None",
            {
                "given_name": "John",
                "family_name": "Doe",
                "iss": "https://example.com/issuer",
                "iat": 1683000000,
                "exp": 1883000000,
                "cnf": {
                    "jwk": {
                        "kty": "EC",
                        "crv": "P-256",
                        "x": "TCAER19Zvu3OHF4j4W4vfSVoHIP1ILilDls7vCeGemc",
                        "y": "ZxjiWWbZMQGHVWKVQ4hbSIirsVfuecCE6t4jT9F2HZQ",
                    }
                },
            },
            {"alg": "ES256", "typ": "kb+jwt"},
            "https://example.com/verifier",
            None,
        ),
        (
            "No holder public key in SD-JWT",
            {
                "given_name": "John",
                "family_name": "Doe",
                "iss": "https://example.com/issuer",
                "iat": 1683000000,
                "exp": 1883000000,
            },
            {"alg": "ES256", "typ": "kb+jwt"},
            "https://example.com/verifier",
            "1234567890",
        ),
        (
            "The holder_public_key_payload is malformed. It doesn't contain the claim jwk: ",
            {
                "given_name": "John",
                "family_name": "Doe",
                "iss": "https://example.com/issuer",
                "iat": 1683000000,
                "exp": 1883000000,
                "cnf": {"y": "ZxjiWWbZMQGHVWKVQ4hbSIirsVfuecCE6t4jT9F2HZQ"},
            },
            {"alg": "ES256", "typ": "kb+jwt"},
            "https://example.com/verifier",
            "1234567890",
        ),
        (
            "Invalid header typ",
            {
                "given_name": "John",
                "family_name": "Doe",
                "iss": "https://example.com/issuer",
                "iat": 1683000000,
                "exp": 1883000000,
                "cnf": {
                    "jwk": {
                        "kty": "EC",
                        "crv": "P-256",
                        "x": "TCAER19Zvu3OHF4j4W4vfSVoHIP1ILilDls7vCeGemc",
                        "y": "ZxjiWWbZMQGHVWKVQ4hbSIirsVfuecCE6t4jT9F2HZQ",
                    }
                },
            },
            {"alg": "ES256", "typ": "JWT"},
            "https://example.com/verifier",
            "1234567890",
        ),
        (
            "Invalid audience",
            {
                "given_name": "John",
                "family_name": "Doe",
                "iss": "https://example.com/issuer",
                "iat": 1683000000,
                "exp": 1883000000,
                "cnf": {
                    "jwk": {
                        "kty": "EC",
                        "crv": "P-256",
                        "x": "TCAER19Zvu3OHF4j4W4vfSVoHIP1ILilDls7vCeGemc",
                        "y": "ZxjiWWbZMQGHVWKVQ4hbSIirsVfuecCE6t4jT9F2HZQ",
                    }
                },
            },
            {"alg": "ES256", "typ": "kb+jwt"},
            "invalid_aud",
            "1234567890",
        ),
        (
            "Invalid nonce",
            {
                "given_name": "John",
                "family_name": "Doe",
                "iss": "https://example.com/issuer",
                "iat": 1683000000,
                "exp": 1883000000,
                "cnf": {
                    "jwk": {
                        "kty": "EC",
                        "crv": "P-256",
                        "x": "TCAER19Zvu3OHF4j4W4vfSVoHIP1ILilDls7vCeGemc",
                        "y": "ZxjiWWbZMQGHVWKVQ4hbSIirsVfuecCE6t4jT9F2HZQ",
                    }
                },
            },
            {"alg": "ES256", "typ": "kb+jwt"},
            "https://example.com/verifier",
            "invalid_nonce",
        ),
    ]

    @pytest.mark.parametrize(
        "error, payload, headers_kb, expected_aud, expected_nonce", test_input
    )
    @pytest.mark.asyncio
    async def test_sd_jwt_key_binding_errors(
        self,
        payload,
        error,
        expected_nonce,
        headers_kb,
        expected_aud,
        profile,
        in_memory_wallet,
    ):
        did_info = await in_memory_wallet.create_local_did(KEY, ED25519, self.seed)
        verification_method = None

        signed = await sd_jwt_sign(
            profile,
            self.headers,
            payload,
            did=did_info.did,
            verification_method=verification_method,
        )
        assert signed

        # Key binding
        payload_kb = {
            "nonce": "1234567890",
            "aud": "https://example.com/verifier",
            "iat": 1688160483,
        }
        signed_kb = await jwt_sign(
            profile,
            headers_kb,
            payload_kb,
            did_info.did,
            verification_method,
        )
        assert signed_kb

        with pytest.raises(
            ValueError,
            match=error,
        ):
            await sd_jwt_verify(
                profile,
                f"{signed}{signed_kb}",
                expected_aud=expected_aud,
                expected_nonce=expected_nonce,
            )
