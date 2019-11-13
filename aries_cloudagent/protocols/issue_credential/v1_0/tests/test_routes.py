from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from aiohttp import web as aio_web

from .....config.injection_context import InjectionContext
from .....storage.error import StorageNotFoundError
from .....holder.base import BaseHolder
from .....messaging.request_context import RequestContext
from .. import routes as test_module


class TestCredentialRoutes(AsyncTestCase):
    async def test_attribute_mime_types_get(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"credential_id": "dummy"}
        context = RequestContext(
            base_context=InjectionContext(enforce_typing=False)
        )
        holder = async_mock.MagicMock()
        holder.get_mime_type = async_mock.CoroutineMock(
            return_value=None
        )
        context.injector.bind_instance(BaseHolder, holder)

        mock.app = {
            "request_context": context,
        }

        test_module.web.json_response = async_mock.CoroutineMock()

        await test_module.attribute_mime_types_get(mock)
        test_module.web.json_response.assert_called_once_with(
            holder.get_mime_type.return_value
        )

    async def test_credential_exchange_list(self):
        mock = async_mock.MagicMock()
        mock.query = {
            "thread_id": "dummy",
            "connection_id": "dummy",
            "role": "dummy",
            "state": "dummy"
        }
        mock.app = {
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.query = async_mock.CoroutineMock()
            mock_cred_ex.query.return_value = [mock_cred_ex]
            mock_cred_ex.serialize = async_mock.MagicMock()
            mock_cred_ex.serialize.return_value = {"hello": "world"}

            test_module.web.json_response = async_mock.CoroutineMock()

            await test_module.credential_exchange_list(mock)
            test_module.web.json_response.assert_called_once_with(
                {"results": [mock_cred_ex.serialize.return_value]}
            )

    async def test_credential_exchange_retrieve(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"cred_ex_id": "dummy"}
        mock.app = {
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value = mock_cred_ex
            mock_cred_ex.serialize = async_mock.MagicMock()
            mock_cred_ex.serialize.return_value = {"hello": "world"}

            test_module.web.json_response = async_mock.CoroutineMock()

            await test_module.credential_exchange_retrieve(mock)
            test_module.web.json_response.assert_called_once_with(
                mock_cred_ex.serialize.return_value
            )

    async def test_credential_exchange_retrieve_not_found(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"cred_ex_id": "dummy"}
        mock.app = {
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()

            # Emulate storage not found (bad credential exchange id)
            mock_cred_ex.retrieve_by_id.side_effect = StorageNotFoundError

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_retrieve(mock)

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
        ) as mock_credential_manager, async_mock.patch.object(
            test_module.CredentialPreview, "deserialize", autospec=True
        ):
            test_module.web.json_response = async_mock.CoroutineMock()

            mock_credential_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )

            mock_credential_manager.return_value.create_offer.return_value = (
                async_mock.CoroutineMock(),
                async_mock.CoroutineMock(),
            )

            mock_cred_ex_record = async_mock.MagicMock()
            mock_cred_offer = async_mock.MagicMock()

            mock_credential_manager.return_value.prepare_send.return_value = (
                (mock_cred_ex_record, mock_cred_offer)
            )

            await test_module.credential_exchange_send(mock)

            test_module.web.json_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_send_no_proposal(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()
        mock.json.return_value = {
            "comment": "comment",
            "connection_id": "dummy",
        }

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credential_exchange_send(mock)

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
            mock_connection_record.retrieve_by_id.side_effect = StorageNotFoundError

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
            mock_connection_record.retrieve_by_id.return_value.is_ready = False

            mock_credential_manager.return_value.create_offer.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send(mock)

    async def test_credential_exchange_send_proposal(self):
        conn_id = "connection-id"
        preview_spec = {"attributes": [{"name": "attr", "value": "value"}]}

        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock(
            return_value={"connection_id": conn_id, "credential_proposal": preview_spec}
        )
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module.CredentialProposal, "deserialize", autospec=True
        ) as mock_proposal_deserialize:

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_cred_ex_record = async_mock.MagicMock()

            mock_credential_manager.return_value.create_proposal.return_value = (
                mock_cred_ex_record
            )

            await test_module.credential_exchange_send_proposal(mock)

            test_module.web.json_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

            mock.app["outbound_message_router"].assert_called_once_with(
                mock_proposal_deserialize.return_value, connection_id=conn_id
            )

    async def test_credential_exchange_send_proposal_no_proposal(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()
        mock.json.return_value = {
            "comment": "comment",
            "connection_id": "dummy",
        }

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credential_exchange_send_proposal(mock)

    async def test_credential_exchange_send_proposal_no_conn_record(self):
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
        ) as mock_credential_manager, async_mock.patch.object(
            test_module.CredentialPreview, "deserialize", autospec=True
        ) as mock_preview_deserialize:

            test_module.web.json_response = async_mock.CoroutineMock()

            # Emulate storage not found (bad connection id)
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )

            mock_credential_manager.return_value.create_proposal.return_value = (
                async_mock.MagicMock()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_proposal(mock)

    async def test_credential_exchange_send_proposal_not_ready(self):
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
        ) as mock_credential_manager, async_mock.patch.object(
            test_module.CredentialPreview, "deserialize", autospec=True
        ) as mock_preview_deserialize:

            test_module.web.json_response = async_mock.CoroutineMock()

            # Emulate connection not ready
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()
            mock_connection_record.retrieve_by_id.return_value.is_ready = False

            mock_credential_manager.return_value.create_proposal.return_value = (
                async_mock.MagicMock()
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send_proposal(mock)

    async def test_credential_exchange_send_free_offer(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "cred_def_id": "cred-def-id",
            }
        )

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": async_mock.patch.object(
                aio_web, "BaseRequest", autospec=True
            ),
        }
        mock.app["request_context"].settings = {}

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager:

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_credential_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )

            mock_cred_ex_record = async_mock.MagicMock()

            mock_credential_manager.return_value.create_offer.return_value = (
                mock_cred_ex_record,
                async_mock.MagicMock(),
            )

            await test_module.credential_exchange_send_free_offer(mock)

            test_module.web.json_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_send_free_offer_no_cred_def_id(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()
        mock.json.return_value = {
            "comment": "comment",
            "credential_preview": "dummy",
        }

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": async_mock.patch.object(
                aio_web, "BaseRequest", autospec=True
            ),
        }
        mock.app["request_context"].settings = {}

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credential_exchange_send_free_offer(mock)

    async def test_credential_exchange_send_free_offer_auto_issue_no_preview(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()
        mock.json.return_value = {
            "comment": "comment",
            "cred_def_id": "dummy",
            "auto_issue": True,
        }

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": async_mock.patch.object(
                aio_web, "BaseRequest", autospec=True
            ),
        }
        mock.app["request_context"].settings = {}

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credential_exchange_send_free_offer(mock)

    async def test_credential_exchange_send_free_offer_no_conn_record(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "cred_def_id": "cred-def-id",
            }
        )

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": async_mock.patch.object(
                aio_web, "BaseRequest", autospec=True
            ),
        }
        mock.app["request_context"].settings = {}

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

            mock_credential_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )
            mock_credential_manager.return_value.create_offer.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_free_offer(mock)

    async def test_credential_exchange_send_free_offer_not_ready(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()
        mock.json.return_value["auto_issue"] = True

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": async_mock.patch.object(
                aio_web, "BaseRequest", autospec=True
            ),
        }
        mock.app["request_context"].settings = {}

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
                await test_module.credential_exchange_send_free_offer(mock)

    async def test_credential_exchange_send_free_offer_with_preview(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "cred_def_id": "cred-def-id",
                "credential_preview": {
                    "attributes": [
                        {
                            "name": "hello",
                            "value": "world"
                        }
                    ]
                }
            }
        )

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": async_mock.patch.object(
                aio_web, "BaseRequest", autospec=True
            ),
        }
        mock.app["request_context"].settings = {}

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager:

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_credential_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )

            mock_cred_ex_record = async_mock.MagicMock()

            mock_credential_manager.return_value.create_offer.return_value = (
                mock_cred_ex_record,
                async_mock.MagicMock(),
            )

            await test_module.credential_exchange_send_free_offer(mock)

            test_module.web.json_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_send_bound_offer(self):
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
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_PROPOSAL_RECEIVED
            )

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_credential_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )

            mock_cred_ex_record = async_mock.MagicMock()

            mock_credential_manager.return_value.create_offer.return_value = (
                mock_cred_ex_record,
                async_mock.MagicMock(),
            )

            await test_module.credential_exchange_send_bound_offer(mock)

            test_module.web.json_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_send_bound_offer_no_conn_record(self):
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
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_PROPOSAL_RECEIVED
            )

            test_module.web.json_response = async_mock.CoroutineMock()

            # Emulate storage not found (bad connection id)
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )

            mock_credential_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )
            mock_credential_manager.return_value.create_offer.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_bound_offer(mock)

    async def test_credential_exchange_send_bound_offer_not_ready(self):
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
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_PROPOSAL_RECEIVED
            )

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
                await test_module.credential_exchange_send_bound_offer(mock)

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
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_OFFER_RECEIVED
            )

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_cred_ex_record = async_mock.MagicMock()

            mock_credential_manager.return_value.create_request.return_value = (
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
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
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

            mock_credential_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )
            mock_credential_manager.return_value.create_offer.return_value = (
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
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_OFFER_RECEIVED
            )

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
                await test_module.credential_exchange_send_request(mock)

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
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex, async_mock.patch.object(
            test_module, "CredentialPreview", autospec=True
        ) as mock_cred_preview:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_REQUEST_RECEIVED
            )

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_cred_ex_record = async_mock.MagicMock()

            mock_credential_manager.return_value.issue_credential.return_value = (
                mock_cred_ex_record,
                async_mock.MagicMock(),
            )

            mock_cred_preview.return_value.deserialize.return_value = (
                async_mock.MagicMock()
            )
            mock_cred_preview.return_value.attr_dict.return_value = (
                async_mock.MagicMock()
            )

            await test_module.credential_exchange_issue(mock)

            test_module.web.json_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_issue_no_preview(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()
        mock.json.return_value = {
            "comment": "comment",
        }

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credential_exchange_issue(mock)

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
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex, async_mock.patch.object(
            test_module, "CredentialPreview", autospec=True
        ) as mock_cred_preview:

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_REQUEST_RECEIVED
            )

            # Emulate storage not found (bad connection id)
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )

            mock_credential_manager.return_value.issue_credential = (
                async_mock.CoroutineMock()
            )
            mock_credential_manager.return_value.issue_credential.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            mock_cred_preview.return_value.deserialize.return_value = (
                async_mock.MagicMock()
            )
            mock_cred_preview.return_value.attr_dict.return_value = (
                async_mock.MagicMock()
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
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex, async_mock.patch.object(
            test_module, "CredentialPreview", autospec=True
        ) as mock_cred_preview:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_REQUEST_RECEIVED
            )

            test_module.web.json_response = async_mock.CoroutineMock()

            # Emulate connection not ready
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()
            mock_connection_record.retrieve_by_id.return_value.is_ready = False

            mock_credential_manager.return_value.issue_credential = (
                async_mock.CoroutineMock()
            )
            mock_credential_manager.return_value.issue_credential.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            mock_cred_preview.return_value.deserialize.return_value = (
                async_mock.MagicMock()
            )
            mock_cred_preview.return_value.attr_dict.return_value = (
                async_mock.MagicMock()
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_issue(mock)

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
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_CREDENTIAL_RECEIVED
            )

            test_module.web.json_response = async_mock.CoroutineMock()

            mock_cred_ex_record = async_mock.MagicMock()

            mock_credential_manager.return_value.store_credential.return_value = (
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
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
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

            mock_credential_manager.return_value.store_credential.return_value = (
                mock_cred_ex,
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
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_CREDENTIAL_RECEIVED
            )

            test_module.web.json_response = async_mock.CoroutineMock()

            # Emulate connection not ready
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()
            mock_connection_record.retrieve_by_id.return_value.is_ready = False

            mock_credential_manager.return_value.store_credential.return_value = (
                mock_cred_ex,
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_store(mock)

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
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
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
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex, async_mock.patch.object(
            test_module, "ProblemReport", autospec=True
        ) as mock_prob_report:

            # Emulate storage not found (bad cred ex id)
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_problem_report(mock_request)

    async def test_credential_exchange_remove(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"cred_ex_id": "dummy"}

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value = mock_cred_ex

            mock_cred_ex.delete_record = async_mock.CoroutineMock()

            test_module.web.json_response = async_mock.CoroutineMock()

            await test_module.credential_exchange_remove(mock)

            test_module.web.json_response.assert_called_once_with({})

    async def test_credential_exchange_remove_not_found(self):
        mock_request = async_mock.MagicMock()
        mock_request.json = async_mock.CoroutineMock()

        mock_outbound = async_mock.CoroutineMock()

        mock_request.app = {
            "outbound_message_router": mock_outbound,
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            # Emulate storage not found (bad cred ex id)
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_remove(mock_request)

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()
