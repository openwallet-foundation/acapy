from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .. import routes as test_module

from ....storage.error import StorageNotFoundError


class TestCredentialRoutes(AsyncTestCase):
    async def test_credential_exchange_send(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager:

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_cred_ex_record = async_mock.MagicMock()

            # mock_credential_manager.return_value.create_offer = async_mock.MagicMock()

            mock_credential_manager.return_value.create_offer.return_value = (
                mock_cred_ex_record,
                async_mock.MagicMock(),
            )

            await test_module.credential_exchange_send(mock)

            test_module.web.json_response.assert_called_once_with(
                mock_credential_manager.return_value.create_offer.return_value[0].serialize.return_value
            )

    async def test_credential_exchange_send_no_conn_record(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager:

            test_module.web.json_response = async_mock.CoroutineMock()

            # Emulate storage not found (bad connection id)
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )

            mock_credential_manager.return_value.create_offer = async_mock.MagicMock()

            mock_credential_manager.return_value.create_offer.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send(mock)

    async def test_credential_exchange_send_not_ready(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager:

            test_module.web.json_response = async_mock.CoroutineMock()

            # Emulate connection not ready
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()
            mock_connection_record.retrieve_by_id.return_value.is_ready = False

            mock_credential_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )

            mock_credential_manager.return_value.create_offer.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send(mock)

    async def test_credential_exchange_send_offer(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_connection_manager:

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_connection_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )

            mock_cred_ex_record = async_mock.MagicMock()

            mock_connection_manager.return_value.create_offer.return_value = (
                mock_cred_ex_record,
                async_mock.MagicMock(),
            )

            await test_module.credential_exchange_send_offer(mock)

            test_module.web.json_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_send_offer_no_conn_record(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_connection_manager:

            test_module.web.json_response = async_mock.CoroutineMock()

            # Emulate storage not found (bad connection id)
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )

            mock_connection_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )

            mock_connection_manager.return_value.create_offer.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_offer(mock)

    async def test_credential_exchange_send_offer_not_ready(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_connection_manager:

            test_module.web.json_response = async_mock.CoroutineMock()

            # Emulate connection not ready
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()
            mock_connection_record.retrieve_by_id.return_value.is_ready = False

            mock_connection_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )

            mock_connection_manager.return_value.create_offer.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send_offer(mock)

    async def test_credential_exchange_send_request(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_connection_manager, async_mock.patch.object(
            test_module, "CredentialExchange", autospec=True
        ) as mock_cred_ex:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_OFFER_RECEIVED
            )

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_cred_ex_record = async_mock.MagicMock()

            mock_connection_manager.return_value.create_request.return_value = (
                mock_cred_ex_record,
                async_mock.MagicMock(),
            )

            await test_module.credential_exchange_send_request(mock)

            test_module.web.json_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_send_request_no_conn_record(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_connection_manager, async_mock.patch.object(
            test_module, "CredentialExchange", autospec=True
        ) as mock_cred_ex:

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_OFFER_RECEIVED
            )

            # Emulate storage not found (bad connection id)
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )

            mock_connection_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )

            mock_connection_manager.return_value.create_offer.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_request(mock)

    async def test_credential_exchange_send_request_not_ready(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_connection_manager, async_mock.patch.object(
            test_module, "CredentialExchange", autospec=True
        ) as mock_cred_ex:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_OFFER_RECEIVED
            )

            test_module.web.json_response = async_mock.CoroutineMock()

            # Emulate connection not ready
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()
            mock_connection_record.retrieve_by_id.return_value.is_ready = False

            mock_connection_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )

            mock_connection_manager.return_value.create_offer.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send_request(mock)

    async def test_credential_exchange_store(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_connection_manager, async_mock.patch.object(
            test_module, "CredentialExchange", autospec=True
        ) as mock_cred_ex:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_CREDENTIAL_RECEIVED
            )

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_cred_ex_record = async_mock.MagicMock()

            mock_connection_manager.return_value.store_credential.return_value = (
                mock_cred_ex_record,
                async_mock.MagicMock(),
            )

            await test_module.credential_exchange_store(mock)

            test_module.web.json_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_store_no_conn_record(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_connection_manager, async_mock.patch.object(
            test_module, "CredentialExchange", autospec=True
        ) as mock_cred_ex:

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_CREDENTIAL_RECEIVED
            )

            # Emulate storage not found (bad connection id)
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )

            mock_connection_manager.return_value.store_credential.return_value = (
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_store(mock)

    async def test_credential_exchange_store_not_ready(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_connection_manager, async_mock.patch.object(
            test_module, "CredentialExchange", autospec=True
        ) as mock_cred_ex:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_CREDENTIAL_RECEIVED
            )

            test_module.web.json_response = async_mock.CoroutineMock()

            # Emulate connection not ready
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()
            mock_connection_record.retrieve_by_id.return_value.is_ready = False

            mock_connection_manager.return_value.store_credential.return_value = (
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_store(mock)

    async def test_credential_exchange_issue(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_connection_manager, async_mock.patch.object(
            test_module, "CredentialExchange", autospec=True
        ) as mock_cred_ex:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_REQUEST_RECEIVED
            )

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_cred_ex_record = async_mock.MagicMock()

            mock_connection_manager.return_value.issue_credential.return_value = (
                mock_cred_ex_record,
                async_mock.MagicMock(),
            )

            await test_module.credential_exchange_issue(mock)

            test_module.web.json_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_issue_no_conn_record(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_connection_manager, async_mock.patch.object(
            test_module, "CredentialExchange", autospec=True
        ) as mock_cred_ex:

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_REQUEST_RECEIVED
            )

            # Emulate storage not found (bad connection id)
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )

            mock_connection_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )

            mock_connection_manager.return_value.issue_credential.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_issue(mock)

    async def test_credential_exchange_issue_not_ready(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_connection_manager, async_mock.patch.object(
            test_module, "CredentialExchange", autospec=True
        ) as mock_cred_ex:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_REQUEST_RECEIVED
            )

            test_module.web.json_response = async_mock.CoroutineMock()

            # Emulate connection not ready
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()
            mock_connection_record.retrieve_by_id.return_value.is_ready = False

            mock_connection_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )

            mock_connection_manager.return_value.issue_credential.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_issue(mock)

    async def test_credential_exchange_problem_report(self):
        mock_request = async_mock.MagicMock()
        mock_request.json = async_mock.CoroutineMock()

        mock_outbound = async_mock.CoroutineMock()

        mock_request.app = {
            "outbound_message_router": mock_outbound,
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_connection_manager, async_mock.patch.object(
            test_module, "CredentialExchange", autospec=True
        ) as mock_cred_ex, async_mock.patch.object(
            test_module, "ProblemReport", autospec=True
        ) as mock_prob_report:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()

            test_module.web.json_response = async_mock.CoroutineMock()

            await test_module.credential_exchange_problem_report(mock_request)

            test_module.web.json_response.assert_called_once_with({})
            mock_outbound.assert_called_once_with(
                mock_prob_report.return_value,
                connection_id=mock_cred_ex.retrieve_by_id.return_value.connection_id,
            )

    async def test_credential_exchange_problem_report_no_cred_record(self):

        mock_request = async_mock.MagicMock()
        mock_request.json = async_mock.CoroutineMock()

        mock_outbound = async_mock.CoroutineMock()

        mock_request.app = {
            "outbound_message_router": mock_outbound,
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_connection_manager, async_mock.patch.object(
            test_module, "CredentialExchange", autospec=True
        ) as mock_cred_ex, async_mock.patch.object(
            test_module, "ProblemReport", autospec=True
        ) as mock_prob_report:

            # Emulate storage not found (bad connection id)
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_problem_report(mock_request)
