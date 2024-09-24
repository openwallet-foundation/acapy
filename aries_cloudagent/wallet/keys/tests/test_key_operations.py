"""Test MultikeypManager."""

from unittest import IsolatedAsyncioTestCase
from aries_cloudagent.wallet.keys.manager import MultikeyManager
from aries_cloudagent.core.in_memory import InMemoryProfile


class TestKeyOperations(IsolatedAsyncioTestCase):
    profile = InMemoryProfile.test_profile()
    seed = "00000000000000000000000000000000"
    multikey = "z6MkgKA7yrw5kYSiDuQFcye4bMaJpcfHFry3Bx45pdWh3s8i"
    verkey = "2ru5PcgeQzxF7QZYwQgDkG2K13PRqyigVw99zMYg8eML"
    kid = "did:web:example.com#key-01"

    async def test_key_creation(self):
        async with self.profile.session() as session:
            key_info = await MultikeyManager(session=session).create(seed=self.seed)
            assert key_info["multikey"] == self.multikey
            assert key_info["kid"] is None

            key_info = await MultikeyManager(session=session).from_multikey(
                multikey=self.multikey
            )
            assert key_info["multikey"] == self.multikey
            assert key_info["kid"] is None

            key_info = await MultikeyManager(session=session).update(
                multikey=self.multikey, kid=self.kid
            )
            assert key_info["multikey"] == self.multikey
            assert key_info["kid"] == self.kid

            key_info = await MultikeyManager(session=session).from_kid(kid=self.kid)
            assert key_info["multikey"] == self.multikey
            assert key_info["kid"] == self.kid

    async def test_key_representations(self):
        async with self.profile.session() as session:
            assert (
                MultikeyManager(session=session)._multikey_to_verkey(self.multikey)
                == self.verkey
            )
            assert (
                MultikeyManager(session=session)._verkey_to_multikey(self.verkey)
                == self.multikey
            )
