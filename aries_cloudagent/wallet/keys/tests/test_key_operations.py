"""Test MultikeypManager."""

from unittest import IsolatedAsyncioTestCase
from aries_cloudagent.wallet.keys.manager import MultikeyManager
from aries_cloudagent.core.in_memory import InMemoryProfile


class TestKeyOperations(IsolatedAsyncioTestCase):
    profile = InMemoryProfile.test_profile()
    manager = MultikeyManager(profile=profile)
    seed = "00000000000000000000000000000000"
    multikey = "z6MkgKA7yrw5kYSiDuQFcye4bMaJpcfHFry3Bx45pdWh3s8i"
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
