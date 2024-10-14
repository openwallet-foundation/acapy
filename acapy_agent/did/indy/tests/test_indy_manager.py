from unittest import IsolatedAsyncioTestCase

from aries_askar import AskarError

from acapy_agent.core.in_memory.profile import (
    InMemoryProfile,
    InMemoryProfileSession,
)
from acapy_agent.did.indy.indy_manager import DidIndyManager
from acapy_agent.tests import mock
from acapy_agent.wallet.did_method import DIDMethods
from acapy_agent.wallet.error import WalletError


class TestIndyManager(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.profile = InMemoryProfile.test_profile()

    def test_init(self):
        assert DidIndyManager(self.profile)

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_register(self, mock_handle):
        self.profile.context.injector.bind_instance(
            DIDMethods, mock.MagicMock(auto_spec=DIDMethods)
        )
        mock_handle.insert_key = mock.CoroutineMock()
        mock_handle.insert = mock.CoroutineMock()
        manager = DidIndyManager(self.profile)
        result = await manager.register()
        assert result.get("did")
        assert result.get("verkey")
        mock_handle.insert_key.assert_called_once()
        mock_handle.insert.assert_called_once()

        # error saving key
        mock_handle.insert_key.side_effect = AskarError(
            code=1, message="Error saving key"
        )
        with self.assertRaises(WalletError):
            await manager.register()

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_register_with_seed_without_allow_insecure(self, mock_handle):
        self.profile.context.injector.bind_instance(
            DIDMethods, mock.MagicMock(auto_spec=DIDMethods)
        )
        mock_handle.insert_key = mock.CoroutineMock()
        mock_handle.insert = mock.CoroutineMock()
        manager = DidIndyManager(self.profile)
        with self.assertRaises(WalletError):
            await manager.register("000000000000000000000000Steward1")

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_register_with_seed_with_allow_insecure(self, mock_handle):
        self.profile.context.injector.bind_instance(
            DIDMethods, mock.MagicMock(auto_spec=DIDMethods)
        )
        self.profile.settings.set_value("wallet.allow_insecure_seed", True)
        mock_handle.insert_key = mock.CoroutineMock()
        mock_handle.insert = mock.CoroutineMock()
        manager = DidIndyManager(self.profile)

        assert await manager.register("000000000000000000000000Steward1")
