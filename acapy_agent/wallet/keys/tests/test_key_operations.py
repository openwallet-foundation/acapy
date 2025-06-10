"""Test MultikeypManager."""

from unittest import IsolatedAsyncioTestCase

from acapy_agent.utils.testing import create_test_profile
from acapy_agent.wallet.key_type import KeyTypes
from acapy_agent.wallet.keys.manager import (
    MultikeyManager,
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
