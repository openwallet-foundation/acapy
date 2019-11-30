from aiohttp import web as aio_web
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .....storage.error import StorageNotFoundError
from .. import routes as test_module


class TestProofRoutes(AsyncTestCase):
    def setUp(self):
        self.mock_context = async_mock.MagicMock()
        self.test_instance = test_module.PresentationManager(self.mock_context)

    async def test_presentation_exchange_list(self):
        mock = async_mock.MagicMock()
        mock.query = {
            "thread_id": "thread_id_0",
            "connection_id": "conn_id_0",
            "role": "dummy",
            "state": "dummy",
        }
        mock.app = {"request_context": self.mock_context}

        with async_mock.patch.object(
            test_module, "V10PresentationExchange", autospec=True
        ) as mock_presentation_exchange:

            mock_presentation_exchange.query = async_mock.CoroutineMock()
            mock_presentation_exchange.query.return_value = [mock_presentation_exchange]
            mock_presentation_exchange.serialize = async_mock.MagicMock()
            mock_presentation_exchange.serialize.return_value = {"hello": "world"}

            test_module.web.json_response = async_mock.CoroutineMock()

            await test_module.presentation_exchange_list(mock)
            test_module.web.json_response.assert_called_once_with(
                {"results": [mock_presentation_exchange.serialize.return_value]}
            )

    async def test_presentation_exchange_credentials_list_not_found(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"pres_ex_id": "dummy"}
        mock.app = {"request_context": "context"}

        with async_mock.patch.object(
            test_module, "V10PresentationExchange", autospec=True
        ) as mock_pres_ex:
            mock_pres_ex.retrieve_by_id = async_mock.CoroutineMock()

            # Emulate storage not found (bad presentation exchange id)
            mock_pres_ex.retrieve_by_id.side_effect = StorageNotFoundError

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.presentation_exchange_credentials_list(mock)

    async def test_presentation_exchange_credentials_list_single_referent(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"pres_ex_id": "123-456-789", "referent": "myReferent1"}
        mock.query = {"extra_query": {}}
        mock.app = {"request_context": self.mock_context}

        with async_mock.patch.object(
            test_module, "V10PresentationExchange", autospec=True
        ) as mock_presentation_exchange:

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_presentation_exchange.return_value.retrieve_by_id.return_value = (
                mock_presentation_exchange
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

    async def test_presentation_exchange_credentials_list_multiple_referents(self):
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
                mock_presentation_exchange
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

    async def test_presentation_exchange_retrieve(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"pres_ex_id": "dummy"}
        mock.app = {"request_context": "context"}

        with async_mock.patch.object(
            test_module, "V10PresentationExchange", autospec=True
        ) as mock_pres_ex:
            mock_pres_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_pres_ex.retrieve_by_id.return_value = mock_pres_ex
            mock_pres_ex.serialize = async_mock.MagicMock()
            mock_pres_ex.serialize.return_value = {"hello": "world"}

            test_module.web.json_response = async_mock.CoroutineMock()

            await test_module.presentation_exchange_retrieve(mock)
            test_module.web.json_response.assert_called_once_with(
                mock_pres_ex.serialize.return_value
            )

    async def test_presentation_exchange_retrieve_not_found(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"pres_ex_id": "dummy"}
        mock.app = {"request_context": "context"}

        with async_mock.patch.object(
            test_module, "V10PresentationExchange", autospec=True
        ) as mock_pres_ex:
            mock_pres_ex.retrieve_by_id = async_mock.CoroutineMock()

            # Emulate storage not found (bad presentation exchange id)
            mock_pres_ex.retrieve_by_id.side_effect = StorageNotFoundError

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.presentation_exchange_retrieve(mock)

    async def test_presentation_exchange_send_proposal(self):
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

    async def test_presentation_exchange_send_proposal_no_conn_record(self):
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

    async def test_presentation_exchange_send_proposal_not_ready(self):
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

    async def test_presentation_exchange_create_request(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock(
            return_value={"comment": "dummy", "proof_request": {}}
        )

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch.object(
            test_module, "PresentationManager", autospec=True
        ) as mock_presentation_manager, async_mock.patch.object(
            test_module, "PresentationPreview", autospec=True
        ) as mock_presentation_proposal, async_mock.patch.object(
            test_module, "PresentationRequest", autospec=True
        ) as mock_presentation_request, async_mock.patch.object(
            test_module, "AttachDecorator", autospec=True
        ) as mock_attach_decorator, async_mock.patch.object(
            test_module, "V10PresentationExchange", autospec=True
        ) as mock_presentation_exchange:

            mock_attach_decorator.from_indy_dict = async_mock.MagicMock(
                return_value=mock_attach_decorator
            )

            mock_presentation_exchange.serialize = async_mock.MagicMock()
            mock_presentation_exchange.serialize.return_value = {"hello": "world"}

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_presentation_manager.return_value.create_exchange_for_request = async_mock.CoroutineMock(
                return_value=mock_presentation_exchange
            )

            await test_module.presentation_exchange_create_request(mock)

            test_module.web.json_response.assert_called_once_with(
                mock_presentation_exchange.serialize.return_value
            )

    async def test_presentation_exchange_send_free_request(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock(
            return_value={
                "connection_id": "dummy",
                "comment": "dummy",
                "proof_request": {},
            }
        )

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
        ) as mock_presentation_proposal, async_mock.patch.object(
            test_module, "PresentationRequest", autospec=True
        ) as mock_presentation_request, async_mock.patch.object(
            test_module, "AttachDecorator", autospec=True
        ) as mock_attach_decorator, async_mock.patch.object(
            test_module, "V10PresentationExchange", autospec=True
        ) as mock_presentation_exchange:

            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_connection_record
            )
            mock_attach_decorator.from_indy_dict = async_mock.MagicMock(
                return_value=mock_attach_decorator
            )

            mock_presentation_exchange.serialize = async_mock.MagicMock()
            mock_presentation_exchange.serialize.return_value = {"hello": "world"}

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_presentation_manager.return_value.create_exchange_for_request = async_mock.CoroutineMock(
                return_value=mock_presentation_exchange
            )

            await test_module.presentation_exchange_send_free_request(mock)

            test_module.web.json_response.assert_called_once_with(
                mock_presentation_exchange.serialize.return_value
            )

    async def test_presentation_exchange_send_free_request_not_found(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock(return_value={"connection_id": "dummy"})

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record:
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()
            mock_connection_record.retrieve_by_id.side_effect = StorageNotFoundError

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.presentation_exchange_send_free_request(mock)

    async def test_presentation_exchange_send_free_request_not_ready(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock(
            return_value={"connection_id": "dummy", "proof_request": {}}
        )

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record:
            mock_connection_record.is_ready = False
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_connection_record
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.presentation_exchange_send_free_request(mock)

    async def test_presentation_exchange_send_bound_request(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock(
            return_value={
                "connection_id": "dummy",
                "comment": "dummy",
                "proof_request": {},
            }
        )
        mock.match_info = {"pres_ex_id": "dummy"}

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
        ) as mock_presentation_proposal, async_mock.patch.object(
            test_module, "PresentationRequest", autospec=True
        ) as mock_presentation_request, async_mock.patch.object(
            test_module, "AttachDecorator", autospec=True
        ) as mock_attach_decorator, async_mock.patch.object(
            test_module, "V10PresentationExchange", autospec=True
        ) as mock_presentation_exchange:

            mock_presentation_exchange.state = (
                test_module.V10PresentationExchange.STATE_PROPOSAL_RECEIVED
            )
            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_presentation_exchange
            )
            mock_presentation_exchange.serialize = async_mock.MagicMock()
            mock_presentation_exchange.serialize.return_value = {"hello": "world"}

            mock_connection_record.is_ready = True
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_connection_record
            )

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_presentation_manager.return_value.create_bound_request = async_mock.CoroutineMock(
                return_value=(mock_presentation_exchange, mock_presentation_request)
            )

            await test_module.presentation_exchange_send_bound_request(mock)

            test_module.web.json_response.assert_called_once_with(
                mock_presentation_exchange.serialize.return_value
            )

    async def test_presentation_exchange_send_bound_request_not_found(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock(
            return_value={
                "connection_id": "dummy",
                "comment": "dummy",
                "proof_request": {},
            }
        )
        mock.match_info = {"pres_ex_id": "dummy"}

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "V10PresentationExchange", autospec=True
        ) as mock_presentation_exchange:

            mock_presentation_exchange.state = (
                test_module.V10PresentationExchange.STATE_PROPOSAL_RECEIVED
            )
            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_presentation_exchange
            )

            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()
            mock_connection_record.retrieve_by_id.side_effect = StorageNotFoundError

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.presentation_exchange_send_bound_request(mock)

    async def test_presentation_exchange_send_bound_request_not_ready(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock(
            return_value={
                "connection_id": "dummy",
                "comment": "dummy",
                "proof_request": {},
            }
        )
        mock.match_info = {"pres_ex_id": "dummy"}

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "V10PresentationExchange", autospec=True
        ) as mock_presentation_exchange:

            mock_presentation_exchange.state = (
                test_module.V10PresentationExchange.STATE_PROPOSAL_RECEIVED
            )
            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_presentation_exchange
            )

            mock_connection_record.is_ready = False
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_connection_record
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.presentation_exchange_send_bound_request(mock)

    async def test_presentation_exchange_send_presentation(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock(
            return_value={
                "comment": "dummy",
                "self_attested_attributes": {},
                "requested_attributes": {},
                "requested_predicates": {},
            }
        )
        mock.match_info = {"pres_ex_id": "dummy"}

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
        ) as mock_presentation_proposal, async_mock.patch.object(
            test_module, "V10PresentationExchange", autospec=True
        ) as mock_presentation_exchange:

            mock_presentation_exchange.state = (
                test_module.V10PresentationExchange.STATE_REQUEST_RECEIVED
            )
            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_presentation_exchange
            )
            mock_presentation_exchange.connection_id = "dummy"
            mock_presentation_exchange.serialize = async_mock.MagicMock()
            mock_presentation_exchange.serialize.return_value = {"hello": "world"}

            mock_connection_record.is_ready = True
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_connection_record
            )

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_presentation_manager.return_value.create_presentation = async_mock.CoroutineMock(
                return_value=(mock_presentation_exchange, async_mock.MagicMock())
            )

            await test_module.presentation_exchange_send_presentation(mock)

            test_module.web.json_response.assert_called_once_with(
                mock_presentation_exchange.serialize.return_value
            )

    async def test_presentation_exchange_send_presentation_not_found(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()
        mock.match_info = {"pres_ex_id": "dummy"}

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "V10PresentationExchange", autospec=True
        ) as mock_presentation_exchange:

            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_presentation_exchange
            )
            mock_presentation_exchange.connection_id = "dummy"

            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.presentation_exchange_send_presentation(mock)

    async def test_presentation_exchange_send_presentation_not_ready(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()
        mock.match_info = {"pres_ex_id": "dummy"}

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "V10PresentationExchange", autospec=True
        ) as mock_presentation_exchange:

            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_presentation_exchange
            )
            mock_presentation_exchange.connection_id = "dummy"

            mock_connection_record.is_ready = False
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_connection_record
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.presentation_exchange_send_presentation(mock)

    async def test_presentation_exchange_verify_presentation(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"pres_ex_id": "dummy"}

        mock.app = {"request_context": self.mock_context}

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "PresentationManager", autospec=True
        ) as mock_presentation_manager, async_mock.patch.object(
            test_module, "V10PresentationExchange", autospec=True
        ) as mock_presentation_exchange:

            mock_presentation_exchange.state = (
                test_module.V10PresentationExchange.STATE_PRESENTATION_RECEIVED
            )
            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_presentation_exchange
            )
            mock_presentation_exchange.connection_id = "dummy"
            mock_presentation_exchange.serialize = async_mock.MagicMock()
            mock_presentation_exchange.serialize.return_value = {"hello": "world"}

            mock_connection_record.is_ready = True
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_connection_record
            )

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_presentation_manager.return_value.verify_presentation = async_mock.CoroutineMock(
                return_value=mock_presentation_exchange
            )

            await test_module.presentation_exchange_verify_presentation(mock)

            test_module.web.json_response.assert_called_once_with(
                mock_presentation_exchange.serialize.return_value
            )

    async def test_presentation_exchange_verify_presentation_not_found(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"pres_ex_id": "dummy"}

        mock.app = {"request_context": self.mock_context}

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "V10PresentationExchange", autospec=True
        ) as mock_presentation_exchange:

            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_presentation_exchange
            )
            mock_presentation_exchange.connection_id = "dummy"

            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.presentation_exchange_verify_presentation(mock)

    async def test_presentation_exchange_verify_presentation_not_ready(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"pres_ex_id": "dummy"}

        mock.app = {"request_context": self.mock_context}

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "V10PresentationExchange", autospec=True
        ) as mock_presentation_exchange:

            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_presentation_exchange
            )
            mock_presentation_exchange.connection_id = "dummy"

            mock_connection_record.is_ready = False
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_connection_record
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.presentation_exchange_verify_presentation(mock)

    async def test_presentation_exchange_remove(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"pres_ex_id": "dummy"}

        mock.app = {"request_context": "context"}

        with async_mock.patch.object(
            test_module, "V10PresentationExchange", autospec=True
        ) as mock_presentation_exchange:
            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock()
            mock_presentation_exchange.retrieve_by_id.return_value = (
                mock_presentation_exchange
            )

            mock_presentation_exchange.delete_record = async_mock.CoroutineMock()

            test_module.web.json_response = async_mock.CoroutineMock()

            await test_module.presentation_exchange_remove(mock)

            test_module.web.json_response.assert_called_once_with({})

    async def test_presentation_exchange_remove_not_found(self):
        mock_request = async_mock.MagicMock()
        mock_request.json = async_mock.CoroutineMock()

        mock_request.app = {"request_context": "context"}

        with async_mock.patch.object(
            test_module, "V10PresentationExchange", autospec=True
        ) as mock_presentation_exchange:
            # Emulate storage not found (bad pres ex id)
            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.presentation_exchange_remove(mock_request)

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()
