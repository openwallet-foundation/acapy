import json
from base64 import urlsafe_b64decode
from hashlib import sha256
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase

from aries_askar import Key, KeyAlg
from sd_jwt.common import SDObj

from ...resolver.did_resolver import DIDResolver
from ...resolver.tests.test_did_resolver import MockResolver
from ...utils.testing import create_test_profile
from ...wallet.did_method import KEY, DIDMethods
from ...wallet.key_type import ED25519, P256, KeyTypes
from ..base import BaseWallet
from ..default_verification_key_strategy import (
    BaseVerificationKeyStrategy,
    DefaultVerificationKeyStrategy,
)
from ..jwt import dict_to_b64, jwt_sign
from ..sd_jwt import (
    SDJWTVerifyResult,
    create_sd_list,
    sd_jwt_sign,
    sd_jwt_verify,
    wrap_list_item_as_sd,
)
from ..util import b58_to_bytes, b64_to_bytes, bytes_to_b64

KB_AUD = "https://example.com/verifier"
KB_NONCE = "1234567890"


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

    async def test_array_element_order_preserved(self):
        # Issue #3965: wrapping list items used remove()+append(), which reversed
        # array order when index paths were processed descending.
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            did_info = await wallet.create_local_did(KEY, ED25519, self.seed)
        original = ["1", "2", "3"]
        payload = {
            "example": list(original),
            "iss": "https://example.com/issuer",
            "iat": 1683000000,
            "exp": 1883000000,
        }
        signed = await sd_jwt_sign(
            self.profile,
            self.headers,
            payload,
            [],
            did_info.did,
            None,
        )
        assert signed
        # Whole claim is wrapped as SDObj key; elements stay SDObj values in order
        wrapped = payload[SDObj("example")]
        assert [item.value for item in wrapped] == original
        assert all(isinstance(item, SDObj) for item in wrapped)

        verified = await sd_jwt_verify(self.profile, signed)
        assert verified.valid
        # Array-element disclosures are [salt, value]; order must match input
        disclosed_values = [d[1] for d in verified.disclosures if len(d) == 2]
        assert disclosed_values == original
        # Outer claim disclosure carries the array of digest placeholders in order
        example_disclosure = next(d for d in verified.disclosures if len(d) == 3)
        assert example_disclosure[1] == "example"
        assert len(example_disclosure[2]) == 3

    def test_wrap_list_item_as_sd_uses_index_path(self):
        from jsonpath_ng.jsonpath import Index

        items = ["a", "b", "c"]
        match = SimpleNamespace(
            path=Index(1),
            value="b",
            context=SimpleNamespace(value=items),
        )
        wrap_list_item_as_sd(match)
        assert items[0] == "a"
        assert isinstance(items[1], SDObj) and items[1].value == "b"
        assert items[2] == "c"

    def test_wrap_list_item_as_sd_falls_back_without_index(self):
        items = ["x", "y", "z"]
        match = SimpleNamespace(
            path="not-an-index",
            value="y",
            context=SimpleNamespace(value=items),
        )
        wrap_list_item_as_sd(match)
        assert items[0] == "x"
        assert isinstance(items[1], SDObj) and items[1].value == "y"
        assert items[2] == "z"

    def test_wrap_list_item_as_sd_descending_indices_keep_order(self):
        # Mirrors create_sd_list descending walk that previously reversed arrays.
        from jsonpath_ng.jsonpath import Index

        items = ["1", "2", "3"]
        for i in (2, 1, 0):
            wrap_list_item_as_sd(
                SimpleNamespace(
                    path=Index(i),
                    value=items[i],
                    context=SimpleNamespace(value=items),
                )
            )
        assert [item.value for item in items] == ["1", "2", "3"]
        assert all(isinstance(item, SDObj) for item in items)

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

    def test_adjacent_list_splices(self):
        payload = {"a": ["x", "y"], "b": ["x", "y"]}
        assert sorted(create_sd_list(payload, ["a[0:2]", "b[0:2]"])) == ["a", "b"]

    async def _holder(self, key_type=ED25519):
        """Create a holder key and return its verkey, key type and public JWK."""
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            key_info = await wallet.create_key(key_type)
        jwk = json.loads(
            Key.from_public_bytes(
                KeyAlg.ED25519 if key_type == ED25519 else KeyAlg.P256,
                b58_to_bytes(key_info.verkey),
            ).get_jwk_public()
        )
        return key_info.verkey, key_type, jwk

    async def _sign_kb(self, verkey, key_type, headers=None, payload=None):
        """Sign a key binding JWT directly with a wallet key."""
        headers = {"alg": key_type.jws_algorithm, "typ": "kb+jwt", **(headers or {})}
        payload = payload or {"nonce": KB_NONCE, "aud": KB_AUD, "iat": 1688160483}
        encoded = f"{dict_to_b64(headers)}.{dict_to_b64(payload)}"
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            sig = await wallet.sign_message(encoded.encode(), verkey)
        return f"{encoded}.{bytes_to_b64(sig, urlsafe=True, pad=False)}"

    async def _issue_bound(self, holder_jwk, cnf=None):
        """Issue an SD-JWT bound to the given holder JWK."""
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            did_info = await wallet.create_local_did(KEY, ED25519, self.seed)
        payload = {
            "given_name": "John",
            "family_name": "Doe",
            "iss": "https://example.com/issuer",
            "iat": 1683000000,
            "exp": 1883000000,
            "cnf": cnf if cnf is not None else {"jwk": holder_jwk},
        }
        return await sd_jwt_sign(self.profile, self.headers, payload, did=did_info.did)

    async def test_sd_jwt_key_binding(self):
        verkey, key_type, jwk = await self._holder()
        signed = await self._issue_bound(jwk)
        kb = await self._sign_kb(verkey, key_type)

        assert await sd_jwt_verify(
            self.profile, f"{signed}{kb}", expected_aud=KB_AUD, expected_nonce=KB_NONCE
        )

    async def test_sd_jwt_key_binding_with_kid(self):
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            did_info = await wallet.create_local_did(KEY, ED25519, self.seed)
        jwk = json.loads(
            Key.from_public_bytes(
                KeyAlg.ED25519, b58_to_bytes(did_info.verkey)
            ).get_jwk_public()
        )
        signed = await self._issue_bound(jwk)
        kb = await jwt_sign(
            self.profile,
            {"alg": "EdDSA", "typ": "kb+jwt"},
            {"nonce": KB_NONCE, "aud": KB_AUD, "iat": 1688160483},
            did_info.did,
        )

        assert await sd_jwt_verify(
            self.profile, f"{signed}{kb}", expected_aud=KB_AUD, expected_nonce=KB_NONCE
        )

    async def test_sd_jwt_key_binding_p256(self):
        verkey, key_type, jwk = await self._holder(P256)
        signed = await self._issue_bound(jwk)
        kb = await self._sign_kb(verkey, key_type)

        assert await sd_jwt_verify(
            self.profile, f"{signed}{kb}", expected_aud=KB_AUD, expected_nonce=KB_NONCE
        )

    async def test_sd_jwt_key_binding_x_other_key(self):
        _, _, holder_jwk = await self._holder()
        other_verkey, other_type, _ = await self._holder()
        signed = await self._issue_bound(holder_jwk)
        kb = await self._sign_kb(other_verkey, other_type)

        with self.assertRaisesRegex(ValueError, "not signed by the holder key"):
            await sd_jwt_verify(
                self.profile,
                f"{signed}{kb}",
                expected_aud=KB_AUD,
                expected_nonce=KB_NONCE,
            )

    async def test_sd_jwt_key_binding_x_other_key_with_kid(self):
        _, _, holder_jwk = await self._holder()
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            other = await wallet.create_local_did(KEY, ED25519, self.seed)
        signed = await self._issue_bound(holder_jwk)
        kb = await jwt_sign(
            self.profile,
            {"alg": "EdDSA", "typ": "kb+jwt"},
            {"nonce": KB_NONCE, "aud": KB_AUD, "iat": 1688160483},
            other.did,
        )

        with self.assertRaisesRegex(ValueError, "not signed by the holder key"):
            await sd_jwt_verify(
                self.profile,
                f"{signed}{kb}",
                expected_aud=KB_AUD,
                expected_nonce=KB_NONCE,
            )

    async def test_sd_jwt_key_binding_x_bad_signature(self):
        verkey, key_type, jwk = await self._holder()
        signed = await self._issue_bound(jwk)
        kb = await self._sign_kb(verkey, key_type)
        header, payload, sig = kb.split(".")
        raw = bytearray(b64_to_bytes(sig, urlsafe=True))
        raw[0] ^= 0x01
        kb = f"{header}.{payload}.{bytes_to_b64(bytes(raw), urlsafe=True, pad=False)}"

        with self.assertRaisesRegex(ValueError, "not signed by the holder key"):
            await sd_jwt_verify(
                self.profile,
                f"{signed}{kb}",
                expected_aud=KB_AUD,
                expected_nonce=KB_NONCE,
            )

    async def test_sd_jwt_key_binding_x_alg_mismatch(self):
        verkey, key_type, jwk = await self._holder()
        signed = await self._issue_bound(jwk)
        kb = await self._sign_kb(verkey, key_type, headers={"alg": "ES256"})

        with self.assertRaisesRegex(ValueError, "alg does not match"):
            await sd_jwt_verify(
                self.profile,
                f"{signed}{kb}",
                expected_aud=KB_AUD,
                expected_nonce=KB_NONCE,
            )

    async def test_sd_jwt_key_binding_x_unsupported_holder_key(self):
        verkey, key_type, jwk = await self._holder()
        signed = await self._issue_bound(jwk, cnf={"jwk": {**jwk, "crv": "X25519"}})
        kb = await self._sign_kb(verkey, key_type)

        with self.assertRaisesRegex(ValueError, "Unsupported holder key"):
            await sd_jwt_verify(
                self.profile,
                f"{signed}{kb}",
                expected_aud=KB_AUD,
                expected_nonce=KB_NONCE,
            )

    async def test_sd_jwt_key_binding_x_missing_kb_jwt(self):
        _, _, jwk = await self._holder()
        signed = await self._issue_bound(jwk)

        with self.assertRaisesRegex(ValueError, "Malformed key binding JWT"):
            await sd_jwt_verify(
                self.profile, signed, expected_aud=KB_AUD, expected_nonce=KB_NONCE
            )

    async def test_sd_jwt_key_binding_errors(self):
        verkey, key_type, jwk = await self._holder()
        cases = [
            (
                "Either both expected_aud and expected_nonce",
                {"jwk": jwk},
                {},
                KB_AUD,
                None,
            ),
            ("No holder public key in SD-JWT", {}, {}, KB_AUD, KB_NONCE),
            (
                "doesn't contain the claim jwk",
                {"y": jwk["x"]},
                {},
                KB_AUD,
                KB_NONCE,
            ),
            ("Invalid header typ", {"jwk": jwk}, {"typ": "JWT"}, KB_AUD, KB_NONCE),
            ("Invalid audience", {"jwk": jwk}, {}, "invalid_aud", KB_NONCE),
            ("Invalid nonce", {"jwk": jwk}, {}, KB_AUD, "invalid_nonce"),
        ]
        for error, cnf, headers_kb, expected_aud, expected_nonce in cases:
            with self.subTest(error=error):
                signed = await self._issue_bound(jwk, cnf=cnf or None)
                if not cnf:
                    # Issue without any cnf claim
                    async with self.profile.session() as session:
                        wallet = session.inject(BaseWallet)
                        did_info = await wallet.create_local_did(KEY, ED25519, self.seed)
                    signed = await sd_jwt_sign(
                        self.profile,
                        self.headers,
                        {"given_name": "John", "iss": "https://example.com/issuer"},
                        did=did_info.did,
                    )
                kb = await self._sign_kb(verkey, key_type, headers=headers_kb)

                with self.assertRaisesRegex(ValueError, error):
                    await sd_jwt_verify(
                        self.profile,
                        f"{signed}{kb}",
                        expected_aud=expected_aud,
                        expected_nonce=expected_nonce,
                    )

    @staticmethod
    def _disclosure(*values):
        """Encode a disclosure and return it with its digest."""
        encoded = bytes_to_b64(json.dumps(list(values)).encode(), urlsafe=True, pad=False)
        digest = bytes_to_b64(
            sha256(encoded.encode("ascii")).digest(), urlsafe=True, pad=False
        )
        return encoded, digest

    @staticmethod
    def _decoded(disclosure):
        return json.loads(b64_to_bytes(disclosure, urlsafe=True))

    async def _sign_nested(self):
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            did_info = await wallet.create_local_did(KEY, ED25519, self.seed)
        payload = {
            "given_name": "John",
            "address": {"street_address": "123 Main St", "country": "US"},
            "nationalities": ["US", "CA"],
            "iss": "https://example.com/issuer",
            "iat": 1683000000,
            "exp": 1883000000,
        }
        signed = await sd_jwt_sign(
            self.profile, self.headers, payload, ["given_name"], did=did_info.did
        )
        jwt_part, *disclosures, _ = signed.split("~")
        return did_info, jwt_part, disclosures

    async def test_verify_nested_disclosures(self):
        _, jwt_part, disclosures = await self._sign_nested()

        verified = await sd_jwt_verify(
            self.profile, "~".join([jwt_part, *disclosures, ""])
        )
        assert verified.valid
        assert len(verified.disclosures) == len(disclosures)

    async def test_verify_x_injected_disclosure(self):
        _, jwt_part, disclosures = await self._sign_nested()
        injected, _ = self._disclosure("c2FsdA", "role", "admin")

        with self.assertRaisesRegex(ValueError, "not referenced"):
            await sd_jwt_verify(
                self.profile, "~".join([jwt_part, *disclosures, injected, ""])
            )

    async def test_verify_x_injected_array_disclosure(self):
        _, jwt_part, disclosures = await self._sign_nested()
        injected, _ = self._disclosure("c2FsdA", "FR")

        with self.assertRaisesRegex(ValueError, "not referenced"):
            await sd_jwt_verify(
                self.profile, "~".join([jwt_part, *disclosures, injected, ""])
            )

    async def test_verify_x_nested_disclosure_without_parent(self):
        _, jwt_part, disclosures = await self._sign_nested()
        presented = [d for d in disclosures if self._decoded(d)[1:2] != ["address"]]
        assert len(presented) == len(disclosures) - 1

        with self.assertRaisesRegex(ValueError, "not referenced"):
            await sd_jwt_verify(self.profile, "~".join([jwt_part, *presented, ""]))

    async def test_verify_x_repeated_disclosure(self):
        _, jwt_part, disclosures = await self._sign_nested()

        with self.assertRaisesRegex(ValueError, "Duplicate disclosure"):
            await sd_jwt_verify(
                self.profile,
                "~".join([jwt_part, *disclosures, disclosures[0], ""]),
            )

    async def test_verify_x_disclosure_digests(self):
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            did_info = await wallet.create_local_did(KEY, ED25519, self.seed)
        claim, claim_digest = self._disclosure("c2FsdA", "role", "user")
        element, element_digest = self._disclosure("c2FsdA", "US")
        base = {"iss": "https://example.com/issuer", "_sd_alg": "sha-256"}
        cases = [
            (
                "Duplicate digest",
                {**base, "_sd": [claim_digest], "a": {"_sd": [claim_digest]}},
                [claim],
            ),
            ("Unsupported _sd_alg", {**base, "_sd_alg": "sha-512"}, []),
            ("Invalid _sd", {**base, "_sd": claim_digest}, [claim]),
            ("Malformed disclosure", {**base, "_sd": [element_digest]}, [element]),
            ("Malformed disclosure", {**base, "a": [{"...": claim_digest}]}, [claim]),
        ]
        for error, payload, presented in cases:
            with self.subTest(error=error):
                jwt_part = await jwt_sign(
                    self.profile, {"typ": "JWT"}, payload, did_info.did
                )
                with self.assertRaisesRegex(ValueError, error):
                    await sd_jwt_verify(
                        self.profile, "~".join([jwt_part, *presented, ""])
                    )
