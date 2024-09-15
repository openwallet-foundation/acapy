from unittest import IsolatedAsyncioTestCase
from ..did_key import DIDKey
from ...core.in_memory import InMemoryProfile


class TestDIDKeyOperations(IsolatedAsyncioTestCase):
    test_seed = "00000000000000000000000000000000"
    did = "did:key:z6MkgKA7yrw5kYSiDuQFcye4bMaJpcfHFry3Bx45pdWh3s8i"
    kid = "did:key:z6MkgKA7yrw5kYSiDuQFcye4bMaJpcfHFry3Bx45pdWh3s8i#z6MkgKA7yrw5kYSiDuQFcye4bMaJpcfHFry3Bx45pdWh3s8i"
    new_kid = "did:web:example.com#key-01"
    multikey = "z6MkgKA7yrw5kYSiDuQFcye4bMaJpcfHFry3Bx45pdWh3s8i"
    profile = InMemoryProfile.test_profile()

    async def test_create_ed25519_did_key(self):
        results = await DIDKey().create(
            key_type="ed25519", profile=self.profile, seed=self.test_seed
        )
        assert results["did"] == self.did
        assert results["kid"] == self.kid
        assert results["multikey"] == self.multikey

    async def test_bind_did_key(self):
        results = await DIDKey().create(
            key_type="ed25519", profile=self.profile, seed=self.test_seed
        )
        results = await DIDKey().bind(did=results["did"], kid=self.new_kid)
        assert results["did"] == self.did
        assert results["kid"] == self.new_kid
        assert results["multikey"] == self.multikey
