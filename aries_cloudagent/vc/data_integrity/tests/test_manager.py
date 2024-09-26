"""Test MultikeypManager."""

from unittest import IsolatedAsyncioTestCase
from aries_cloudagent.wallet.keys.manager import MultikeyManager
from aries_cloudagent.core.in_memory import InMemoryProfile


class TestDiManager(IsolatedAsyncioTestCase):
    profile = InMemoryProfile.test_profile()
    seed = "00000000000000000000000000000000"
    kid = "did:key:z6MkgKA7yrw5kYSiDuQFcye4bMaJpcfHFry3Bx45pdWh3s8i\
        #z6MkgKA7yrw5kYSiDuQFcye4bMaJpcfHFry3Bx45pdWh3s8i"

    async def test_add_proof(self):
        pass

    async def test_add_proof_set(self):
        pass

    async def test_add_proof_chain(self):
        pass

    async def test_verify_proof(self):
        pass

    async def test_verify_proof_set(self):
        pass

    async def test_verify_proof_chain(self):
        pass
