from aiohttp import web as aio_web
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .....storage.error import StorageNotFoundError
from .. import routes as test_module


class TestProofRoutes(AsyncTestCase):
    def setUp(self):
        self.mock_context = async_mock.MagicMock()
        self.test_instance = test_module.PresentationManager(self.mock_context)

    async def test_present_proof_credentials_list_single_referent(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"pres_ex_id": "123-456-789", "referent": "myReferent1"}
        mock.query = {"extra_query": {}}
        mock.app = {"request_context": self.mock_context}

        with async_mock.patch.object(
            test_module, "V10PresentationExchange", autospec=True
        ) as mock_presentation_exchange:

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_presentation_exchange.return_value.retrieve_by_id.return_value = (
                async_mock.MagicMock()
            )

            # mock BaseHolder injection
            inject = self.test_instance.context.inject = async_mock.CoroutineMock()
            mock_holder = inject.return_value
            mock_holder.get_credentials_for_presentation_request_by_referent = (
                async_mock.CoroutineMock()
            )

            returned_credentials = [{"name": "Credential1"}, {"name": "Credential2"}]
            mock_holder.get_credentials_for_presentation_request_by_referent.return_value = (
                returned_credentials
            )

            await test_module.presentation_exchange_credentials_list(mock)

            test_module.web.json_response.assert_called_once_with(returned_credentials)

    async def test_present_proof_credentials_list_multiple_referents(self):
        mock = async_mock.MagicMock()
        mock.match_info = {
            "pres_ex_id": "123-456-789",
            "referent": "myReferent1,myReferent2",
        }
        mock.query = {"extra_query": {}}
        mock.app = {"request_context": self.mock_context}

        with async_mock.patch.object(
            test_module, "V10PresentationExchange", autospec=True
        ) as mock_presentation_exchange:

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_presentation_exchange.return_value.retrieve_by_id.return_value = (
                async_mock.MagicMock()
            )

            # mock BaseHolder injection
            inject = self.test_instance.context.inject = async_mock.CoroutineMock()
            mock_holder = inject.return_value
            mock_holder.get_credentials_for_presentation_request_by_referent = (
                async_mock.CoroutineMock()
            )

            returned_credentials = [{"name": "Credential1"}, {"name": "Credential2"}]
            mock_holder.get_credentials_for_presentation_request_by_referent.return_value = (
                returned_credentials
            )

            await test_module.presentation_exchange_credentials_list(mock)

            test_module.web.json_response.assert_called_once_with(returned_credentials)

    async def test_present_proof_send_proposal(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "PresentationManager", autospec=True
        ) as mock_presentation_manager, async_mock.patch.object(
            test_module, "PresentationPreview", autospec=True
        ) as mock_presentation_proposal:

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_presentation_manager.return_value.create_exchange_for_proposal = (
                async_mock.CoroutineMock()
            )

            mock_presentation_exchange_record = async_mock.MagicMock()

            mock_presentation_manager.return_value.create_exchange_for_proposal.return_value = (
                mock_presentation_exchange_record
            )

            mock_presentation_proposal.return_value.deserialize.return_value = (
                async_mock.MagicMock()
            )

            await test_module.presentation_exchange_send_proposal(mock)

            test_module.web.json_response.assert_called_once_with(
                mock_presentation_exchange_record.serialize.return_value
            )

    async def test_present_proof_send_proposal_no_conn_record(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "PresentationManager", autospec=True
        ) as mock_presentation_manager:

            test_module.web.json_response = async_mock.CoroutineMock()

            # Emulate storage not found (bad connection id)
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )

            mock_presentation_manager.return_value.create_exchange_for_proposal = (
                async_mock.CoroutineMock()
            )
            mock_presentation_manager.return_value.create_exchange_for_proposal.return_value = (
                async_mock.MagicMock()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.presentation_exchange_send_proposal(mock)

    async def test_present_proof_send_proposal_not_ready(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "PresentationManager", autospec=True
        ) as mock_presentation_manager:

            test_module.web.json_response = async_mock.CoroutineMock()

            # Emulate connection not ready
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()
            mock_connection_record.retrieve_by_id.return_value.is_ready = False

            mock_presentation_manager.return_value.create_exchange_for_proposal = (
                async_mock.CoroutineMock()
            )
            mock_presentation_manager.return_value.create_exchange_for_proposal.return_value = (
                async_mock.MagicMock()
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.presentation_exchange_send_proposal(mock)
