"""Test MultikeypManager."""

from unittest import IsolatedAsyncioTestCase
from aries_cloudagent.wallet.keys.manager import MultikeyManager
from aries_cloudagent.core.in_memory import InMemoryProfile


class TestDiCryptosuites(IsolatedAsyncioTestCase):
    profile = InMemoryProfile.test_profile()
    seed = "00000000000000000000000000000000"
    multikey = "z6MkgKA7yrw5kYSiDuQFcye4bMaJpcfHFry3Bx45pdWh3s8i"
    verkey = "2ru5PcgeQzxF7QZYwQgDkG2K13PRqyigVw99zMYg8eML"
    kid = "did:web:example.com#key-01"

    async def test_key_creation(self):
        pass
