"""Test MultikeypManager."""

import json
from unittest import IsolatedAsyncioTestCase, mock

import base58
from aries_askar import Key, KeyAlg
from pydid.verification_method import JsonWebKey2020, VerificationMethod

from acapy_agent.utils.testing import create_test_profile
from acapy_agent.wallet.key_type import KeyTypes
from acapy_agent.wallet.keys.manager import (
    MultikeyManager,
    MultikeyManagerError,
    jwk_to_multikey,
    multikey_from_verification_method,
    multikey_to_verkey,
    verkey_to_multikey,
)


class TestKeyOperations(IsolatedAsyncioTestCase):
    seed = "00000000000000000000000000000000"

    ed25519_multikey = "z6MkgKA7yrw5kYSiDuQFcye4bMaJpcfHFry3Bx45pdWh3s8i"
    ed25519_verkey = "2ru5PcgeQzxF7QZYwQgDkG2K13PRqyigVw99zMYg8eML"
    ed25519_alg = "ed25519"

    p256_multikey = "zDnaeSd75MAwSRmem34MfZEzSMjQNcpWLmzkbF8Su49AuA9U2"
    p256_verkey = "demmi97mhJ7JQu31git4hQz8a1PD1dETJH9TVKaynNQv"
    p256_alg = "p256"

    bls12381g2_multikey = "zUC71fcKNvfU5d4NT3vurh8wdBqD2VSaVz7RdHmsfFBiYqfLDFkJTVK3m3hLb7yYDZq1C95HyssoX5BCr4ZatwP7jEh3UnwW7AMnx5fxdrhNkGVknbVY5QmjJ6S2CmtztCCffFL"
    bls12381g2_verkey = "mq4SKF1Ej1CA37G4gkSjKtUHnD8NU1ZVkuC4BPiuoxJXoenfkputxbjfS8dHhGHN3vfQwU1z9BdEuBqTjg3PuHAKgT3Q9XEJgRyZje4WGKMtRh9vzUbd8J23jbA7Je3oAe2"
    bls12381g2_alg = "bls12381g2"

    async def asyncSetUp(self) -> None:
        self.profile = await create_test_profile()
        self.profile.context.injector.bind_instance(KeyTypes, KeyTypes())

    async def test_key_creation(self):
        async with self.profile.session() as session:
            for i, (alg, expected_multikey) in enumerate(
                [
                    (self.ed25519_alg, self.ed25519_multikey),
                    (self.p256_alg, self.p256_multikey),
                    (self.bls12381g2_alg, self.bls12381g2_multikey),
                ]
            ):
                manager = MultikeyManager(session=session)
                kid = f"did:web:example.com#key-0{i}"

                key_info = await manager.create(seed=self.seed, alg=alg)
                assert key_info["multikey"] == expected_multikey
                assert key_info["kid"] is None

                key_info = await manager.from_multikey(multikey=expected_multikey)
                assert key_info["multikey"] == expected_multikey
                assert key_info["kid"] == []

                key_info = await manager.update(multikey=expected_multikey, kid=kid)
                assert key_info["multikey"] == expected_multikey
                assert key_info["kid"] == kid

                key_info = await manager.from_kid(kid=kid)
                assert key_info["multikey"] == expected_multikey
                assert key_info["kid"] == kid

    async def test_key_id_binding(self):
        async with self.profile.session() as session:
            test_multikey = self.ed25519_multikey
            key_id_01 = "did:web:example.com#key-01"
            key_id_02 = "did:web:example.com#key-02"
            key_id_03 = "did:web:example.com#key-03"

            manager = MultikeyManager(session=session)

            await manager.create(self.seed, key_id_01, self.ed25519_alg)
            await manager.bind_key_id(test_multikey, key_id_02)
            await manager.bind_key_id(test_multikey, key_id_03)

            assert (await manager.from_kid(key_id_01))["multikey"] == test_multikey
            assert (await manager.from_kid(key_id_02))["multikey"] == test_multikey
            assert (await manager.from_kid(key_id_03))["multikey"] == test_multikey

            await manager.unbind_key_id(test_multikey, key_id_01)

            assert (await manager.from_kid(key_id_01)) is None
            assert (await manager.from_kid(key_id_02))["multikey"] == test_multikey
            assert (await manager.from_kid(key_id_03))["multikey"] == test_multikey

    async def test_key_transformations(self):
        for alg, multikey, verkey in [
            (self.ed25519_alg, self.ed25519_multikey, self.ed25519_verkey),
            (self.p256_alg, self.p256_multikey, self.p256_verkey),
            (self.bls12381g2_alg, self.bls12381g2_multikey, self.bls12381g2_verkey),
        ]:
            assert multikey_to_verkey(multikey) == verkey
            assert verkey_to_multikey(verkey, alg=alg) == multikey

    async def test_jwk_to_multikey_ed25519_and_p256(self):
        for alg, key_alg, expected_multikey in [
            (self.ed25519_alg, KeyAlg.ED25519, self.ed25519_multikey),
            (self.p256_alg, KeyAlg.P256, self.p256_multikey),
        ]:
            async with self.profile.session() as session:
                created = await MultikeyManager(session=session).create(
                    seed=self.seed, alg=alg
                )

            askar_key = Key.from_public_bytes(
                key_alg, base58.b58decode(multikey_to_verkey(created["multikey"]))
            )
            jwk = json.loads(askar_key.get_jwk_public())
            assert jwk_to_multikey(jwk) == expected_multikey

            # Private material must be ignored for public conversion.
            jwk_with_d = {**jwk, "d": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"}
            assert jwk_to_multikey(jwk_with_d) == expected_multikey

    async def test_jwk_to_multikey_unsupported(self):
        with self.assertRaises(MultikeyManagerError):
            jwk_to_multikey({"kty": "EC", "crv": "secp256k1", "x": "x", "y": "y"})
        with self.assertRaises(MultikeyManagerError):
            jwk_to_multikey("not-a-jwk")

    async def test_multikey_from_json_web_key_verification_method(self):
        async with self.profile.session() as session:
            created = await MultikeyManager(session=session).create(
                seed=self.seed, alg=self.ed25519_alg
            )

        askar_key = Key.from_public_bytes(
            KeyAlg.ED25519,
            base58.b58decode(multikey_to_verkey(created["multikey"])),
        )
        jwk = json.loads(askar_key.get_jwk_public())

        for vm_type in ("JsonWebKey2020", "JsonWebKey"):
            if vm_type == "JsonWebKey2020":
                vm = JsonWebKey2020.deserialize(
                    {
                        "id": "did:web:example.com#key-01-jwk",
                        "type": vm_type,
                        "controller": "did:web:example.com",
                        "publicKeyJwk": jwk,
                    }
                )
            else:
                vm = VerificationMethod.deserialize(
                    {
                        "id": "did:web:example.com#key-01-jwk",
                        "type": vm_type,
                        "controller": "did:web:example.com",
                        "publicKeyJwk": jwk,
                    }
                )
            assert multikey_from_verification_method(vm) == created["multikey"]

    async def test_multikey_from_json_web_key_missing_jwk(self):
        vm = mock.MagicMock(spec=VerificationMethod)
        vm.type = "JsonWebKey2020"
        vm.public_key_jwk = None
        with self.assertRaises(MultikeyManagerError):
            multikey_from_verification_method(vm)
