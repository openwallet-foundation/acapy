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

    async def asyncSetUp(self) -> None:
        self.profile = await create_test_profile()
        self.profile.context.injector.bind_instance(KeyTypes, KeyTypes())

    async def test_key_creation(self):
        async with self.profile.session() as session:
            for i, (alg, expected_multikey) in enumerate(
                [
                    (self.ed25519_alg, self.ed25519_multikey),
                    (self.p256_alg, self.p256_multikey),
                ]
            ):
                kid = f"did:web:example.com#key-0{i}"

                key_info = await MultikeyManager(session=session).create(
                    seed=self.seed, alg=alg
                )
                assert key_info["multikey"] == expected_multikey
                assert key_info["kid"] is None

                key_info = await MultikeyManager(session=session).from_multikey(
                    multikey=expected_multikey
                )
                assert key_info["multikey"] == expected_multikey
                assert key_info["kid"] is None

                key_info = await MultikeyManager(session=session).update(
                    multikey=expected_multikey, kid=kid
                )
                assert key_info["multikey"] == expected_multikey
                assert key_info["kid"] == kid

                key_info = await MultikeyManager(session=session).from_kid(kid=kid)
                assert key_info["multikey"] == expected_multikey
                assert key_info["kid"] == kid

    async def test_key_transformations(self):
        for alg, multikey, verkey in [
            (self.ed25519_alg, self.ed25519_multikey, self.ed25519_verkey),
            (self.p256_alg, self.p256_multikey, self.p256_verkey),
        ]:
            assert multikey_to_verkey(multikey) == verkey
            assert verkey_to_multikey(verkey, alg=alg) == multikey
