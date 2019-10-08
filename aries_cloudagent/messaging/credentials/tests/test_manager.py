from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .. import manager as test_module

from ....storage.error import StorageNotFoundError


class TestCredentialManager(AsyncTestCase):
    def setUp(self):
        self.mock_context = async_mock.MagicMock()
        self.test_instance = test_module.CredentialManager(self.mock_context)

    async def test_receive_offer_sets_cache(self):
        mock_credential_offer_message = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "CredentialExchange", autospec=True
        ) as mock_credential_exchange, async_mock.patch.object(
            test_module, "BaseCache", autospec=True
        ) as mock_base_cache, async_mock.patch.object(
            test_module, "json", autospec=True
        ) as mock_json:

            mock_json.loads.return_value = async_mock.MagicMock()

            mock_credential_exchange_instance = (
                mock_credential_exchange.return_value
            ) = async_mock.CoroutineMock()

            mock_credential_exchange_instance.save = async_mock.CoroutineMock()

            inject = self.test_instance.context.inject = async_mock.CoroutineMock()
            mock_cache = inject.return_value
            mock_cache.set = async_mock.CoroutineMock()

            await self.test_instance.receive_offer(
                mock_credential_exchange.return_value, ""
            )

            # Assert cache set
            mock_cache.set.assert_called_once_with(
                "credential_exchange::offer_exchange_id::"
                + f"{mock_credential_exchange_instance.credential_definition_id}::"
                + f"{mock_credential_exchange_instance.connection_id}",
                mock_credential_exchange_instance.credential_id,
            )

    async def test_receive_offer_sets_cache(self):
        mock_credential_offer_message = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "CredentialExchange", autospec=True
        ) as mock_credential_exchange, async_mock.patch.object(
            test_module, "BaseCache", autospec=True
        ) as mock_base_cache, async_mock.patch.object(
            test_module, "json", autospec=True
        ) as mock_json:

            mock_json.loads.return_value = async_mock.MagicMock()

            mock_credential_exchange_instance = (
                mock_credential_exchange.return_value
            ) = async_mock.CoroutineMock()

            mock_credential_exchange_instance.save = async_mock.CoroutineMock()

            inject = self.test_instance.context.inject = async_mock.CoroutineMock()
            mock_cache = inject.return_value
            mock_cache.set = async_mock.CoroutineMock()

            await self.test_instance.receive_offer(
                mock_credential_exchange.return_value, ""
            )

            # Assert cache set
            mock_cache.set.assert_called_once_with(
                "credential_exchange::offer_exchange_id::"
                + f"{mock_credential_exchange_instance.credential_definition_id}::"
                + f"{mock_credential_exchange_instance.connection_id}",
                mock_credential_exchange_instance.credential_id,
            )
