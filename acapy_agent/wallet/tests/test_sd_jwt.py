import json
from base64 import urlsafe_b64decode
from unittest import IsolatedAsyncioTestCase

from ...resolver.did_resolver import DIDResolver
from ...resolver.tests.test_did_resolver import MockResolver
from ...utils.testing import create_test_profile
from ...wallet.did_method import KEY, DIDMethods
from ...wallet.key_type import ED25519, KeyTypes
from ..base import BaseWallet
from ..default_verification_key_strategy import (
    BaseVerificationKeyStrategy,
    DefaultVerificationKeyStrategy,
)
from ..jwt import jwt_sign
from ..sd_jwt import SDJWTVerifyResult, sd_jwt_sign, sd_jwt_verify


class TestSDJWT(IsolatedAsyncioTestCase):
    """Tests for JWT sign and verify using dids."""

    async def asyncSetUp(self):
        self.profile = await create_test_profile()
        self.resolver = DIDResolver()
        self.resolver.register_resolver(
            MockResolver(
                ["key"],
                resolved={
                    "@context": "https://www.w3.org/ns/did/v1",
                    "id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                    "verificationMethod": [
                        {
                            "id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                            "type": "Ed25519VerificationKey2018",
                            "controller": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                            "publicKeyBase58": "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
                        }
                    ],
                    "authentication": [
                        "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
                    ],
                    "assertionMethod": [
                        "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
                    ],
                    "capabilityDelegation": [
                        "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
                    ],
                    "capabilityInvocation": [
                        "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
                    ],
                    "keyAgreement": [
                        {
                            "id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6LSbkodSr6SU2trs8VUgnrnWtSm7BAPG245ggrBmSrxbv1R",
                            "type": "X25519KeyAgreementKey2019",
                            "controller": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                            "publicKeyBase58": "5dTvYHaNaB7mk7iA9LqCJEHG2dGZQsvoi8WGzDRtYEf",
                        }
                    ],
                },
                native=True,
            )
        )
        self.profile.context.injector.bind_instance(DIDMethods, DIDMethods())
        self.profile.context.injector.bind_instance(
            BaseVerificationKeyStrategy, DefaultVerificationKeyStrategy()
        )
        self.profile.context.injector.bind_instance(DIDResolver, self.resolver)
        self.profile.context.injector.bind_instance(KeyTypes, KeyTypes())

    seed = "testseed000000000000000000000001"
    headers = {}

    async def test_sign_with_did_key_and_verify(self):
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            did_info = await wallet.create_local_did(KEY, ED25519, self.seed)

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
            self.profile,
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
            padded = f"{disclosure}{'=' * divmod(len(disclosure), 4)[1]}"
            decoded = json.loads(urlsafe_b64decode(padded).decode("utf-8"))
            # Add the disclosures associated with the claims to be revealed
            if decoded[1] in revealed:
                signed_sd_jwt = signed_sd_jwt + "~" + disclosure

        verified = await sd_jwt_verify(self.profile, f"{signed_sd_jwt}~")
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

    async def test_flat_structure(self):
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            did_info = await wallet.create_local_did(KEY, ED25519, self.seed)

        verification_method = None
        non_sd_list = [
            "address.street_address",
            "address.locality",
            "address.region",
            "address.country",
        ]
        signed = await sd_jwt_sign(
            self.profile,
            self.headers,
            {
                "address": {
                    "street_address": "123 Main St",
                    "locality": "Anytown",
                    "region": "Anystate",
                    "country": "US",
                },
                "iss": "https://example.com/issuer",
                "iat": 1683000000,
                "exp": 1883000000,
            },
            non_sd_list,
            did_info.did,
            verification_method,
        )
        assert signed

        verified = await sd_jwt_verify(self.profile, signed)
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

    async def test_nested_structure(self):
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            did_info = await wallet.create_local_did(KEY, ED25519, self.seed)
        verification_method = None
        non_sd_list = ["address"]

        signed = await sd_jwt_sign(
            self.profile,
            self.headers,
            {
                "address": {
                    "street_address": "123 Main St",
                    "locality": "Anytown",
                    "region": "Anystate",
                    "country": "US",
                },
                "iss": "https://example.com/issuer",
                "iat": 1683000000,
                "exp": 1883000000,
            },
            non_sd_list,
            did_info.did,
            verification_method,
        )
        assert signed

        verified = await sd_jwt_verify(self.profile, signed)
        assert isinstance(verified, SDJWTVerifyResult)
        assert verified.valid
        assert len(verified.payload["address"]["_sd"]) >= 4
        assert verified.payload["_sd_alg"]
        sd_claims = ["street_address", "region", "locality", "country"]
        assert sorted(sd_claims) == sorted([claim[1] for claim in verified.disclosures])

    async def test_recursive_nested_structure(self):
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            did_info = await wallet.create_local_did(KEY, ED25519, self.seed)
        verification_method = None
        non_sd_list = []

        signed = await sd_jwt_sign(
            self.profile,
            self.headers,
            {
                "address": {
                    "street_address": "123 Main St",
                    "locality": "Anytown",
                    "region": "Anystate",
                    "country": "US",
                },
                "iss": "https://example.com/issuer",
                "iat": 1683000000,
                "exp": 1883000000,
            },
            non_sd_list,
            did_info.did,
            verification_method,
        )
        assert signed

        verified = await sd_jwt_verify(self.profile, signed)
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

    async def test_list_splice(self):
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            did_info = await wallet.create_local_did(KEY, ED25519, self.seed)
        payload = {"nationalities": ["US", "DE", "SA"]}
        verification_method = None
        non_sd_list = ["nationalities", "nationalities[1:3]"]

        signed = await sd_jwt_sign(
            self.profile,
            self.headers,
            payload,
            non_sd_list,
            did_info.did,
            verification_method,
        )
        assert signed

        verified = await sd_jwt_verify(self.profile, signed)
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

    async def test_sd_jwt_key_binding(self):
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            did_info = await wallet.create_local_did(KEY, ED25519, self.seed)
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
            self.profile,
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
            self.profile,
            headers_kb,
            payload_kb,
            did_info.did,
            verification_method,
        )
        assert signed_kb

        assert await sd_jwt_verify(
            self.profile,
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

    async def test_sd_jwt_key_binding_errors(self):
        for error, payload, headers_kb, expected_aud, expected_nonce in self.test_input:
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                did_info = await wallet.create_local_did(KEY, ED25519, self.seed)
            verification_method = None

            signed = await sd_jwt_sign(
                self.profile,
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
                self.profile,
                headers_kb,
                payload_kb,
                did_info.did,
                verification_method,
            )
            assert signed_kb

        with self.assertRaises(
            ValueError,
        ):
            await sd_jwt_verify(
                self.profile,
                f"{signed}{signed_kb}",
                expected_aud=expected_aud,
                expected_nonce=expected_nonce,
            )
