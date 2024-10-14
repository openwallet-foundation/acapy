from unittest import IsolatedAsyncioTestCase

from acapy_agent.core.in_memory.profile import (
    InMemoryProfile,
    InMemoryProfileSession,
)
from acapy_agent.ledger.base import BaseLedger
from acapy_agent.tests import mock
from acapy_agent.wallet.askar import AskarWallet
from acapy_agent.wallet.did_info import DIDInfo
from acapy_agent.wallet.did_method import INDY, SOV, WEB
from acapy_agent.wallet.error import WalletError
from acapy_agent.wallet.key_type import ED25519


class TestAskar(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.profile = InMemoryProfile()
        self.session = InMemoryProfileSession(self.profile)

    def test_init(self):
        wallet = AskarWallet(self.session)
        assert wallet.session == self.session

    async def test_set_did_endpoint(self):
        wallet = AskarWallet(self.session)
        wallet.replace_local_did_metadata = mock.CoroutineMock()

        # Set endpoint for a Sov DID
        sov_did_info = DIDInfo("example123", "verkey", {}, SOV, ED25519.key_type)
        wallet.get_local_did = mock.CoroutineMock(return_value=sov_did_info)
        wallet.get_public_did = mock.CoroutineMock(return_value=sov_did_info)
        await wallet.set_did_endpoint(
            "did:example:123",
            "http://example.com",
            mock.MagicMock(BaseLedger, autospec=True),
        )

        # Set endpoint for an Indy DID
        indy_did_info = DIDInfo("did:indy:example", "verkey", {}, INDY, ED25519.key_type)
        wallet.get_local_did = mock.CoroutineMock(return_value=indy_did_info)
        wallet.get_public_did = mock.CoroutineMock(return_value=indy_did_info)
        await wallet.set_did_endpoint(
            "did:example:123",
            "http://example.com",
            mock.MagicMock(BaseLedger, autospec=True),
        )

        # Set endpoint for a Web DID should fail
        web_did_info = DIDInfo("did:web:example:123", "verkey", {}, WEB, ED25519.key_type)
        wallet.get_local_did = mock.CoroutineMock(return_value=web_did_info)
        wallet.get_public_did = mock.CoroutineMock(return_value=web_did_info)
        with self.assertRaises(WalletError):
            await wallet.set_did_endpoint(
                "did:example:123",
                "http://example.com",
                mock.MagicMock(BaseLedger, autospec=True),
            )
