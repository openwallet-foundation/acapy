"""Test MultikeypManager."""

from unittest import IsolatedAsyncioTestCase
from aries_cloudagent.wallet.keys.manager import MultikeyManager
from aries_cloudagent.core.in_memory import InMemoryProfile


class TestKeyOperations(IsolatedAsyncioTestCase):
    profile = InMemoryProfile.test_profile()
    manager = MultikeyManager(profile=profile)
    seed = "00000000000000000000000000000000"
    multikey = "z6MkgKA7yrw5kYSiDuQFcye4bMaJpcfHFry3Bx45pdWh3s8i"
    verkey = "2ru5PcgeQzxF7QZYwQgDkG2K13PRqyigVw99zMYg8eML"
    kid = "did:web:example.com#key-01"

    async def test_key_creation(self):
        key_info = await self.manager.create(seed=self.seed)
        assert key_info["multikey"] == self.multikey
        assert key_info["kid"] is None

        key_info = await self.manager.from_multikey(multikey=self.multikey)
        assert key_info["multikey"] == self.multikey
        assert key_info["kid"] is None

        key_info = await self.manager.update(multikey=self.multikey, kid=self.kid)
        assert key_info["multikey"] == self.multikey
        assert key_info["kid"] == self.kid

        key_info = await self.manager.from_kid(kid=self.kid)
        assert key_info["multikey"] == self.multikey
        assert key_info["kid"] == self.kid

        assert self.manager.kid_exists(self.kid)

    async def test_key_representations(self):
        assert self.manager._multikey_to_verkey(self.multikey) == self.verkey
        assert self.manager._verkey_to_multikey(self.verkey) == self.multikey
