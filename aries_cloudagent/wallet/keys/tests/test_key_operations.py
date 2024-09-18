from unittest import IsolatedAsyncioTestCase
from ..manager import MultikeyManager
from ....core.in_memory import InMemoryProfile


class TestKeyOperations(IsolatedAsyncioTestCase):
    profile = InMemoryProfile.test_profile()
    manager = MultikeyManager(profile=profile)
    seed = "00000000000000000000000000000000"
    multikey = "z6MkgKA7yrw5kYSiDuQFcye4bMaJpcfHFry3Bx45pdWh3s8i"
    kid = "did:web:example.com#key-01"
    new_kid = "did:web:example.com#key-02"

    async def test_key_creation(self):
        multikey = await self.manager.create(seed=self.seed)
        assert multikey == self.multikey
        multikey = await self.manager.from_multikey(multikey=multikey)
        assert multikey == self.multikey

    async def test_key_binding(self):
        multikey = await self.manager.create(
            seed=self.seed, kid=self.kid
        )
        assert multikey == self.multikey
        multikey = await self.manager.from_kid(
            kid=self.kid
        )
        assert multikey == self.multikey
        multikey = await self.manager.update(
            multikey=multikey, kid=self.new_kid
        )
        assert multikey == self.multikey
        multikey = await self.manager.from_kid(
            kid=self.new_kid
        )
        assert multikey == self.multikey
