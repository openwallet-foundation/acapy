import importlib

from aiohttp import web as aio_web
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .....indy.holder import IndyHolder
from .....indy.verifier import IndyVerifier
from .....ledger.base import BaseLedger
from .....messaging.request_context import RequestContext
from .....storage.error import StorageNotFoundError

from .. import routes as test_module


class TestProofRoutes(AsyncTestCase):
    def setUp(self):
        self.mock_context = RequestContext.test_context()

    async def test_validate_non_revoked(self):
        non_revo = test_module.IndyProofReqNonRevokedSchema()
        non_revo.validate_fields({"fro": 1234567890})
        non_revo.validate_fields({"to": 1234567890})
        non_revo.validate_fields({"fro": 1234567890, "to": 1234567890})
        with self.assertRaises(test_module.ValidationError):
            non_revo.validate_fields({})

    async def test_validate_proof_req_attr_spec(self):
        aspec = test_module.IndyProofReqAttrSpecSchema()
        aspec.validate_fields({"name": "attr0"})
        aspec.validate_fields(
            {
                "names": ["attr0", "attr1"],
                "restrictions": [{"attr::attr1::value": "my-value"}],
            }
        )
        aspec.validate_fields(
            {"name": "attr0", "restrictions": [{"schema_name": "preferences"}]}
        )
        with self.assertRaises(test_module.ValidationError):
            aspec.validate_fields({})
        with self.assertRaises(test_module.ValidationError):
            aspec.validate_fields({"name": "attr0", "names": ["attr1", "attr2"]})
        with self.assertRaises(test_module.ValidationError):
            aspec.validate_fields({"names": ["attr1", "attr2"]})
        with self.assertRaises(test_module.ValidationError):
            aspec.validate_fields({"names": ["attr0", "attr1"], "restrictions": []})
        with self.assertRaises(test_module.ValidationError):
            aspec.validate_fields({"names": ["attr0", "attr1"], "restrictions": [{}]})

    async def test_presentation_exchange_list(self):
        mock = async_mock.MagicMock()
        mock.query = {
            "thread_id": "thread_id_0",
            "connection_id": "conn_id_0",
            "role": "dummy",
            "state": "dummy",
        }
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange.query = async_mock.CoroutineMock()
            mock_presentation_exchange.query.return_value = [mock_presentation_exchange]
            mock_presentation_exchange.serialize = async_mock.MagicMock()
            mock_presentation_exchange.serialize.return_value = {
                "thread_id": "sample-thread-id"
            }

            with async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:
                await test_module.presentation_exchange_list(mock)
                mock_response.assert_called_once_with(
                    {"results": [mock_presentation_exchange.serialize.return_value]}
                )

    async def test_presentation_exchange_list_x(self):
        mock = async_mock.MagicMock()
        mock.query = {
            "thread_id": "thread_id_0",
            "connection_id": "conn_id_0",
            "role": "dummy",
            "state": "dummy",
        }
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange.query = async_mock.CoroutineMock(
                side_effect=test_module.StorageError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.presentation_exchange_list(mock)

    async def test_presentation_exchange_credentials_list_not_found(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"pres_ex_id": "dummy"}
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock()

            # Emulate storage not found (bad presentation exchange id)
            mock_presentation_exchange.retrieve_by_id.side_effect = StorageNotFoundError

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.presentation_exchange_credentials_list(mock)

    async def test_presentation_exchange_credentials_x(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"pres_ex_id": "123-456-789", "referent": "myReferent1"}
        mock.query = {"extra_query": {}}
        returned_credentials = [{"name": "Credential1"}, {"name": "Credential2"}]
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }
        self.mock_context._context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credentials_for_presentation_request_by_referent=(
                    async_mock.CoroutineMock(side_effect=test_module.IndyHolderError())
                )
            ),
        )

        with async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange.return_value.retrieve_by_id.return_value = (
                mock_presentation_exchange
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.presentation_exchange_credentials_list(mock)

    async def test_presentation_exchange_credentials_list_single_referent(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"pres_ex_id": "123-456-789", "referent": "myReferent1"}
        mock.query = {"extra_query": {}}

        returned_credentials = [{"name": "Credential1"}, {"name": "Credential2"}]
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }
        self.mock_context._context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credentials_for_presentation_request_by_referent=async_mock.CoroutineMock(
                    return_value=returned_credentials
                )
            ),
        )

        with async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange.return_value.retrieve_by_id.return_value = (
                mock_presentation_exchange
            )

            with async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:
                await test_module.presentation_exchange_credentials_list(mock)
                mock_response.assert_called_once_with(returned_credentials)

    async def test_presentation_exchange_credentials_list_multiple_referents(self):
        mock = async_mock.MagicMock()
        mock.match_info = {
            "pres_ex_id": "123-456-789",
            "referent": "myReferent1,myReferent2",
        }
        mock.query = {"extra_query": {}}

        returned_credentials = [{"name": "Credential1"}, {"name": "Credential2"}]
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }
        self.mock_context._context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credentials_for_presentation_request_by_referent=async_mock.CoroutineMock(
                    return_value=returned_credentials
                )
            ),
        )

        with async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange.return_value.retrieve_by_id.return_value = (
                mock_presentation_exchange
            )

            with async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:
                await test_module.presentation_exchange_credentials_list(mock)
                mock_response.assert_called_once_with(returned_credentials)

    async def test_presentation_exchange_retrieve(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"pres_ex_id": "dummy"}
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_pres_ex:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_pres_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_pres_ex.retrieve_by_id.return_value = mock_pres_ex
            mock_pres_ex.serialize = async_mock.MagicMock()
            mock_pres_ex.serialize.return_value = {"thread_id": "sample-thread-id"}

            with async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:
                await test_module.presentation_exchange_retrieve(mock)
                mock_response.assert_called_once_with(
                    mock_pres_ex.serialize.return_value
                )

    async def test_presentation_exchange_retrieve_not_found(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"pres_ex_id": "dummy"}
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_pres_ex:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_pres_ex.retrieve_by_id = async_mock.CoroutineMock()

            # Emulate storage not found (bad presentation exchange id)
            mock_pres_ex.retrieve_by_id.side_effect = StorageNotFoundError

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.presentation_exchange_retrieve(mock)

    async def test_presentation_exchange_retrieve_ser_x(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"pres_ex_id": "dummy"}
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        mock_pres_ex_rec = async_mock.MagicMock(
            connection_id="abc123", thread_id="thid123"
        )
        with async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_pres_ex:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_pres_ex.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_pres_ex_rec
            )
            mock_pres_ex_rec.serialize = async_mock.MagicMock(
                side_effect=test_module.BaseModelError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.presentation_exchange_retrieve(mock)

    async def test_presentation_exchange_send_proposal(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch(
            "aries_cloudagent.connections.models.conn_record.ConnRecord",
            autospec=True,
        ) as mock_connection_record, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.manager.PresentationManager",
            autospec=True,
        ) as mock_presentation_manager, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.messages.inner.presentation_preview.PresentationPreview",
            autospec=True,
        ) as mock_preview:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange_record = async_mock.MagicMock()
            mock_presentation_manager.return_value.create_exchange_for_proposal = (
                async_mock.CoroutineMock(return_value=mock_presentation_exchange_record)
            )

            mock_preview.return_value.deserialize.return_value = async_mock.MagicMock()

            with async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:
                await test_module.presentation_exchange_send_proposal(mock)
                mock_response.assert_called_once_with(
                    mock_presentation_exchange_record.serialize.return_value
                )

    async def test_presentation_exchange_send_proposal_no_conn_record(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch(
            "aries_cloudagent.connections.models.conn_record.ConnRecord",
            autospec=True,
        ) as mock_connection_record:

            # Since we are mocking import
            importlib.reload(test_module)

            # Emulate storage not found (bad connection id)
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
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

        with async_mock.patch(
            "aries_cloudagent.connections.models.conn_record.ConnRecord",
            autospec=True,
        ) as mock_connection_record, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.messages.inner.presentation_preview.PresentationPreview",
            autospec=True,
        ) as mock_preview, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.messages.presentation_proposal.PresentationProposal",
            autospec=True,
        ) as mock_proposal:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()
            mock_connection_record.retrieve_by_id.return_value.is_ready = False

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.presentation_exchange_send_proposal(mock)

    async def test_presentation_exchange_send_proposal_x(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch(
            "aries_cloudagent.connections.models.conn_record.ConnRecord",
            autospec=True,
        ) as mock_connection_record, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.manager.PresentationManager",
            autospec=True,
        ) as mock_presentation_manager, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.messages.inner.presentation_preview.PresentationPreview",
            autospec=True,
        ) as mock_preview:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange_record = async_mock.MagicMock()
            mock_presentation_manager.return_value.create_exchange_for_proposal = (
                async_mock.CoroutineMock(side_effect=test_module.StorageError())
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
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

        with async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.manager.PresentationManager",
            autospec=True,
        ) as mock_presentation_manager, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.messages.inner.presentation_preview.PresentationPreview",
            autospec=True,
        ) as mock_preview, async_mock.patch.object(
            test_module, "PresentationRequest", autospec=True
        ) as mock_presentation_request, async_mock.patch(
            "aries_cloudagent.messaging.decorators.attach_decorator.AttachDecorator",
            autospec=True,
        ) as mock_attach_decorator, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange, async_mock.patch(
            "aries_cloudagent.indy.util.generate_pr_nonce",
            autospec=True,
        ) as mock_generate_nonce:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_generate_nonce = async_mock.CoroutineMock()

            mock_attach_decorator.from_indy_dict = async_mock.MagicMock(
                return_value=mock_attach_decorator
            )
            mock_presentation_exchange.serialize = async_mock.MagicMock()
            mock_presentation_exchange.serialize.return_value = {
                "thread_id": "sample-thread-id"
            }
            mock_mgr = async_mock.MagicMock(
                create_exchange_for_request=async_mock.CoroutineMock(
                    return_value=mock_presentation_exchange
                )
            )
            mock_presentation_manager.return_value = mock_mgr

            with async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:
                await test_module.presentation_exchange_create_request(mock)
                mock_response.assert_called_once_with(
                    mock_presentation_exchange.serialize.return_value
                )

    async def test_presentation_exchange_create_request_x(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock(
            return_value={"comment": "dummy", "proof_request": {}}
        )
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.manager.PresentationManager",
            autospec=True,
        ) as mock_presentation_manager, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.messages.inner.presentation_preview.PresentationPreview",
            autospec=True,
        ) as mock_preview, async_mock.patch.object(
            test_module, "PresentationRequest", autospec=True
        ) as mock_presentation_request, async_mock.patch(
            "aries_cloudagent.messaging.decorators.attach_decorator.AttachDecorator",
            autospec=True,
        ) as mock_attach_decorator, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange, async_mock.patch(
            "aries_cloudagent.indy.util.generate_pr_nonce",
            autospec=True,
        ) as mock_generate_nonce:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange.serialize = async_mock.MagicMock()
            mock_presentation_exchange.serialize.return_value = {
                "thread_id": "sample-thread-id"
            }
            mock_mgr = async_mock.MagicMock(
                create_exchange_for_request=async_mock.CoroutineMock(
                    side_effect=test_module.StorageError()
                )
            )
            mock_presentation_manager.return_value = mock_mgr

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.presentation_exchange_create_request(mock)

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

        with async_mock.patch(
            "aries_cloudagent.connections.models.conn_record.ConnRecord",
            autospec=True,
        ) as mock_connection_record, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.manager.PresentationManager",
            autospec=True,
        ) as mock_presentation_manager, async_mock.patch(
            "aries_cloudagent.indy.util.generate_pr_nonce",
            autospec=True,
        ) as mock_generate_nonce, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.messages.inner.presentation_preview.PresentationPreview",
            autospec=True,
        ) as mock_preview, async_mock.patch.object(
            test_module, "PresentationRequest", autospec=True
        ) as mock_presentation_request, async_mock.patch(
            "aries_cloudagent.messaging.decorators.attach_decorator.AttachDecorator",
            autospec=True,
        ) as mock_attach_decorator, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_connection_record
            )
            mock_attach_decorator.from_indy_dict = async_mock.MagicMock(
                return_value=mock_attach_decorator
            )
            mock_presentation_exchange.serialize = async_mock.MagicMock()
            mock_presentation_exchange.serialize.return_value = {
                "thread_id": "sample-thread-id"
            }

            mock_mgr = async_mock.MagicMock(
                create_exchange_for_request=async_mock.CoroutineMock(
                    return_value=mock_presentation_exchange
                )
            )
            mock_presentation_manager.return_value = mock_mgr

            with async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:
                await test_module.presentation_exchange_send_free_request(mock)
                mock_response.assert_called_once_with(
                    mock_presentation_exchange.serialize.return_value
                )

    async def test_presentation_exchange_send_free_request_not_found(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock(return_value={"connection_id": "dummy"})
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch(
            "aries_cloudagent.connections.models.conn_record.ConnRecord",
            autospec=True,
        ) as mock_connection_record:

            # Since we are mocking import
            importlib.reload(test_module)

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

        with async_mock.patch(
            "aries_cloudagent.connections.models.conn_record.ConnRecord",
            autospec=True,
        ) as mock_connection_record:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_connection_record.is_ready = False
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_connection_record
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.presentation_exchange_send_free_request(mock)

    async def test_presentation_exchange_send_free_request_x(self):
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

        with async_mock.patch(
            "aries_cloudagent.connections.models.conn_record.ConnRecord",
            autospec=True,
        ) as mock_connection_record, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.manager.PresentationManager",
            autospec=True,
        ) as mock_presentation_manager, async_mock.patch(
            "aries_cloudagent.indy.util.generate_pr_nonce",
            autospec=True,
        ) as mock_generate_nonce, async_mock.patch.object(
            test_module, "PresentationPreview", autospec=True
        ) as mock_presentation_proposal, async_mock.patch.object(
            test_module, "PresentationRequest", autospec=True
        ) as mock_presentation_request, async_mock.patch(
            "aries_cloudagent.messaging.decorators.attach_decorator.AttachDecorator",
            autospec=True,
        ) as mock_attach_decorator, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_generate_nonce = async_mock.CoroutineMock()

            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_connection_record
            )
            mock_attach_decorator.from_indy_dict = async_mock.MagicMock(
                return_value=mock_attach_decorator
            )
            mock_presentation_exchange.serialize = async_mock.MagicMock()
            mock_presentation_exchange.serialize.return_value = {
                "thread_id": "sample-thread-id"
            }

            mock_mgr = async_mock.MagicMock(
                create_exchange_for_request=async_mock.CoroutineMock(
                    side_effect=test_module.StorageError()
                )
            )
            mock_presentation_manager.return_value = mock_mgr

            with self.assertRaises(test_module.web.HTTPBadRequest):
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

        self.mock_context._context.injector.bind_instance(
            BaseLedger,
            async_mock.MagicMock(
                __aenter__=async_mock.CoroutineMock(),
                __aexit__=async_mock.CoroutineMock(),
            ),
        )
        self.mock_context._context.injector.bind_instance(
            IndyVerifier,
            async_mock.MagicMock(
                verify_presentation=async_mock.CoroutineMock(),
            ),
        )

        with async_mock.patch(
            "aries_cloudagent.connections.models.conn_record.ConnRecord",
            autospec=True,
        ) as mock_connection_record, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.manager.PresentationManager",
            autospec=True,
        ) as mock_presentation_manager, async_mock.patch(
            "aries_cloudagent.indy.util.generate_pr_nonce",
            autospec=True,
        ) as mock_generate_nonce, async_mock.patch.object(
            test_module, "PresentationPreview", autospec=True
        ) as mock_presentation_proposal, async_mock.patch.object(
            test_module, "PresentationRequest", autospec=True
        ) as mock_presentation_request, async_mock.patch(
            "aries_cloudagent.messaging.decorators.attach_decorator.AttachDecorator",
            autospec=True,
        ) as mock_attach_decorator, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange.state = (
                test_module.V10PresentationExchange.STATE_PROPOSAL_RECEIVED
            )
            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_presentation_exchange
            )
            mock_presentation_exchange.serialize = async_mock.MagicMock()
            mock_presentation_exchange.serialize.return_value = {
                "thread_id": "sample-thread-id"
            }
            mock_connection_record.is_ready = True
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_connection_record
            )

            mock_mgr = async_mock.MagicMock(
                create_bound_request=async_mock.CoroutineMock(
                    return_value=(mock_presentation_exchange, mock_presentation_request)
                )
            )
            mock_presentation_manager.return_value = mock_mgr

            with async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:
                await test_module.presentation_exchange_send_bound_request(mock)
                mock_response.assert_called_once_with(
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

        with async_mock.patch(
            "aries_cloudagent.connections.models.conn_record.ConnRecord",
            autospec=True,
        ) as mock_connection_record, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.manager.PresentationManager",
            autospec=True,
        ) as mock_presentation_manager, async_mock.patch(
            "aries_cloudagent.indy.util.generate_pr_nonce",
            autospec=True,
        ) as mock_generate_nonce, async_mock.patch.object(
            test_module, "PresentationPreview", autospec=True
        ) as mock_presentation_proposal, async_mock.patch.object(
            test_module, "PresentationRequest", autospec=True
        ) as mock_presentation_request, async_mock.patch(
            "aries_cloudagent.messaging.decorators.attach_decorator.AttachDecorator",
            autospec=True,
        ) as mock_attach_decorator, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

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

        with async_mock.patch(
            "aries_cloudagent.connections.models.conn_record.ConnRecord",
            autospec=True,
        ) as mock_connection_record, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.manager.PresentationManager",
            autospec=True,
        ) as mock_presentation_manager, async_mock.patch(
            "aries_cloudagent.indy.util.generate_pr_nonce",
            autospec=True,
        ) as mock_generate_nonce, async_mock.patch.object(
            test_module, "PresentationPreview", autospec=True
        ) as mock_presentation_proposal, async_mock.patch.object(
            test_module, "PresentationRequest", autospec=True
        ) as mock_presentation_request, async_mock.patch(
            "aries_cloudagent.messaging.decorators.attach_decorator.AttachDecorator",
            autospec=True,
        ) as mock_attach_decorator, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

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

    async def test_presentation_exchange_send_bound_request_bad_state(self):
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

        with async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    state=mock_presentation_exchange.STATE_PRESENTATION_ACKED
                )
            )
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.presentation_exchange_send_bound_request(mock)

    async def test_presentation_exchange_send_bound_request_x(self):
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

        with async_mock.patch(
            "aries_cloudagent.connections.models.conn_record.ConnRecord",
            autospec=True,
        ) as mock_connection_record, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.manager.PresentationManager",
            autospec=True,
        ) as mock_presentation_manager, async_mock.patch(
            "aries_cloudagent.indy.util.generate_pr_nonce",
            autospec=True,
        ) as mock_generate_nonce, async_mock.patch.object(
            test_module, "PresentationPreview", autospec=True
        ) as mock_presentation_proposal, async_mock.patch.object(
            test_module, "PresentationRequest", autospec=True
        ) as mock_presentation_request, async_mock.patch(
            "aries_cloudagent.messaging.decorators.attach_decorator.AttachDecorator",
            autospec=True,
        ) as mock_attach_decorator, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange.state = (
                test_module.V10PresentationExchange.STATE_PROPOSAL_RECEIVED
            )
            mock_presentation_exchange.connection_id = "abc123"
            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_presentation_exchange
            )
            mock_presentation_exchange.serialize = async_mock.MagicMock()
            mock_presentation_exchange.serialize.return_value = {
                "thread_id": "sample-thread-id",
            }
            mock_connection_record.is_ready = True
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_connection_record
            )

            mock_mgr = async_mock.MagicMock(
                create_bound_request=async_mock.CoroutineMock(
                    side_effect=test_module.StorageError()
                )
            )
            mock_presentation_manager.return_value = mock_mgr

            with self.assertRaises(test_module.web.HTTPBadRequest):
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
        self.mock_context._context.injector.bind_instance(
            BaseLedger,
            async_mock.MagicMock(
                __aenter__=async_mock.CoroutineMock(),
                __aexit__=async_mock.CoroutineMock(),
            ),
        )
        self.mock_context._context.injector.bind_instance(
            IndyVerifier,
            async_mock.MagicMock(
                verify_presentation=async_mock.CoroutineMock(),
            ),
        )

        with async_mock.patch(
            "aries_cloudagent.connections.models.conn_record.ConnRecord",
            autospec=True,
        ) as mock_connection_record, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.manager.PresentationManager",
            autospec=True,
        ) as mock_presentation_manager, async_mock.patch.object(
            test_module, "PresentationPreview", autospec=True
        ) as mock_presentation_proposal, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange.state = (
                test_module.V10PresentationExchange.STATE_REQUEST_RECEIVED
            )
            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    state=mock_presentation_exchange.STATE_REQUEST_RECEIVED,
                    connection_id="dummy",
                    serialize=async_mock.MagicMock(
                        return_value={"thread_id": "sample-thread-id"}
                    ),
                )
            )
            mock_connection_record.is_ready = True
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_connection_record
            )
            mock_mgr = async_mock.MagicMock(
                create_presentation=async_mock.CoroutineMock(
                    return_value=(mock_presentation_exchange, async_mock.MagicMock())
                )
            )
            mock_presentation_manager.return_value = mock_mgr

            with async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:
                await test_module.presentation_exchange_send_presentation(mock)
                mock_response.assert_called_once_with(
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

        with async_mock.patch(
            "aries_cloudagent.connections.models.conn_record.ConnRecord",
            autospec=True,
        ) as mock_connection_record, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.manager.PresentationManager",
            autospec=True,
        ) as mock_presentation_manager, async_mock.patch(
            "aries_cloudagent.indy.util.generate_pr_nonce",
            autospec=True,
        ) as mock_generate_nonce, async_mock.patch.object(
            test_module, "PresentationPreview", autospec=True
        ) as mock_presentation_proposal, async_mock.patch.object(
            test_module, "PresentationRequest", autospec=True
        ) as mock_presentation_request, async_mock.patch(
            "aries_cloudagent.messaging.decorators.attach_decorator.AttachDecorator",
            autospec=True,
        ) as mock_attach_decorator, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    state=mock_presentation_exchange.STATE_REQUEST_RECEIVED,
                    connection_id="dummy",
                )
            )

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

        with async_mock.patch(
            "aries_cloudagent.connections.models.conn_record.ConnRecord",
            autospec=True,
        ) as mock_connection_record, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.manager.PresentationManager",
            autospec=True,
        ) as mock_presentation_manager, async_mock.patch(
            "aries_cloudagent.indy.util.generate_pr_nonce",
            autospec=True,
        ) as mock_generate_nonce, async_mock.patch.object(
            test_module, "PresentationPreview", autospec=True
        ) as mock_presentation_proposal, async_mock.patch.object(
            test_module, "PresentationRequest", autospec=True
        ) as mock_presentation_request, async_mock.patch(
            "aries_cloudagent.messaging.decorators.attach_decorator.AttachDecorator",
            autospec=True,
        ) as mock_attach_decorator, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    state=mock_presentation_exchange.STATE_REQUEST_RECEIVED,
                    connection_id="dummy",
                )
            )

            mock_connection_record.is_ready = False
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_connection_record
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.presentation_exchange_send_presentation(mock)

    async def test_presentation_exchange_send_presentation_bad_state(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()
        mock.match_info = {"pres_ex_id": "dummy"}
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    state=mock_presentation_exchange.STATE_PRESENTATION_ACKED
                )
            )
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.presentation_exchange_send_presentation(mock)

    async def test_presentation_exchange_send_presentation_x(self):
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

        with async_mock.patch(
            "aries_cloudagent.connections.models.conn_record.ConnRecord",
            autospec=True,
        ) as mock_connection_record, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.manager.PresentationManager",
            autospec=True,
        ) as mock_presentation_manager, async_mock.patch(
            "aries_cloudagent.indy.util.generate_pr_nonce",
            autospec=True,
        ) as mock_generate_nonce, async_mock.patch.object(
            test_module, "PresentationPreview", autospec=True
        ) as mock_presentation_proposal, async_mock.patch.object(
            test_module, "PresentationRequest", autospec=True
        ) as mock_presentation_request, async_mock.patch(
            "aries_cloudagent.messaging.decorators.attach_decorator.AttachDecorator",
            autospec=True,
        ) as mock_attach_decorator, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange.state = (
                test_module.V10PresentationExchange.STATE_REQUEST_RECEIVED
            )
            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    state=mock_presentation_exchange.STATE_REQUEST_RECEIVED,
                    connection_id="dummy",
                    serialize=async_mock.MagicMock(
                        return_value={"thread_id": "sample-thread-id"}
                    ),
                )
            )
            mock_connection_record.is_ready = True
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_connection_record
            )
            mock_mgr = async_mock.MagicMock(
                create_presentation=async_mock.CoroutineMock(
                    side_effect=test_module.LedgerError()
                )
            )
            mock_presentation_manager.return_value = mock_mgr

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.presentation_exchange_send_presentation(mock)

    async def test_presentation_exchange_verify_presentation(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"pres_ex_id": "dummy"}
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch(
            "aries_cloudagent.connections.models.conn_record.ConnRecord",
            autospec=True,
        ) as mock_connection_record, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.manager.PresentationManager",
            autospec=True,
        ) as mock_presentation_manager, async_mock.patch(
            "aries_cloudagent.indy.util.generate_pr_nonce",
            autospec=True,
        ) as mock_generate_nonce, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.messages.inner.presentation_preview.PresentationPreview",
            autospec=True,
        ) as mock_preview, async_mock.patch.object(
            test_module, "PresentationRequest", autospec=True
        ) as mock_presentation_request, async_mock.patch(
            "aries_cloudagent.messaging.decorators.attach_decorator.AttachDecorator",
            autospec=True,
        ) as mock_attach_decorator, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    state=mock_presentation_exchange.STATE_PRESENTATION_RECEIVED,
                    connection_id="dummy",
                    thread_id="dummy",
                    serialize=async_mock.MagicMock(
                        return_value={"thread_id": "sample-thread-id"}
                    ),
                )
            )
            mock_connection_record.is_ready = True
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_connection_record
            )
            mock_mgr = async_mock.MagicMock(
                verify_presentation=async_mock.CoroutineMock(
                    return_value=mock_presentation_exchange.retrieve_by_id.return_value
                )
            )
            mock_presentation_manager.return_value = mock_mgr

            with async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:
                await test_module.presentation_exchange_verify_presentation(mock)
                mock_response.assert_called_once_with({"thread_id": "sample-thread-id"})

    async def test_presentation_exchange_verify_presentation_not_found(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"pres_ex_id": "dummy"}
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }
        self.mock_context._context.injector.bind_instance(
            BaseLedger,
            async_mock.MagicMock(
                __aenter__=async_mock.CoroutineMock(),
                __aexit__=async_mock.CoroutineMock(),
            ),
        )
        self.mock_context._context.injector.bind_instance(
            IndyVerifier,
            async_mock.MagicMock(
                verify_presentation=async_mock.CoroutineMock(),
            ),
        )

        with async_mock.patch(
            "aries_cloudagent.connections.models.conn_record.ConnRecord",
            autospec=True,
        ) as mock_connection_record, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.manager.PresentationManager",
            autospec=True,
        ) as mock_presentation_manager, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    state=mock_presentation_exchange.STATE_PRESENTATION_RECEIVED,
                    connection_id="dummy",
                )
            )

            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.presentation_exchange_verify_presentation(mock)

    async def test_presentation_exchange_verify_presentation_not_ready(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"pres_ex_id": "dummy"}
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch(
            "aries_cloudagent.connections.models.conn_record.ConnRecord",
            autospec=True,
        ) as mock_connection_record, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.manager.PresentationManager",
            autospec=True,
        ) as mock_presentation_manager, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    state=mock_presentation_exchange.STATE_PRESENTATION_RECEIVED,
                    connection_id="dummy",
                )
            )

            mock_connection_record.is_ready = False
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_connection_record
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.presentation_exchange_verify_presentation(mock)

    async def test_presentation_exchange_verify_presentation_bad_state(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()
        mock.match_info = {"pres_ex_id": "dummy"}
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    state=mock_presentation_exchange.STATE_PRESENTATION_ACKED
                )
            )
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.presentation_exchange_verify_presentation(mock)

    async def test_presentation_exchange_verify_presentation_x(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"pres_ex_id": "dummy"}
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }
        self.mock_context._context.injector.bind_instance(
            BaseLedger,
            async_mock.MagicMock(
                __aenter__=async_mock.CoroutineMock(),
                __aexit__=async_mock.CoroutineMock(),
            ),
        )
        self.mock_context._context.injector.bind_instance(
            IndyVerifier,
            async_mock.MagicMock(
                verify_presentation=async_mock.CoroutineMock(),
            ),
        )

        with async_mock.patch(
            "aries_cloudagent.connections.models.conn_record.ConnRecord",
            autospec=True,
        ) as mock_connection_record, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.manager.PresentationManager",
            autospec=True,
        ) as mock_presentation_manager, async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    state=mock_presentation_exchange.STATE_PRESENTATION_RECEIVED,
                    connection_id="dummy",
                    thread_id="dummy",
                    serialize=async_mock.MagicMock(
                        return_value={"thread_id": "sample-thread-id"}
                    ),
                )
            )

            mock_connection_record.is_ready = True
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_connection_record
            )
            mock_mgr = async_mock.MagicMock(
                verify_presentation=async_mock.CoroutineMock(
                    side_effect=test_module.LedgerError()
                ),
            )
            mock_presentation_manager.return_value = mock_mgr

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.presentation_exchange_verify_presentation(mock)

    async def test_presentation_exchange_remove(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"pres_ex_id": "dummy"}
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    state=mock_presentation_exchange.STATE_VERIFIED,
                    connection_id="dummy",
                    delete_record=async_mock.CoroutineMock(),
                )
            )

            with async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:
                await test_module.presentation_exchange_remove(mock)
                mock_response.assert_called_once_with({})

    async def test_presentation_exchange_remove_not_found(self):
        mock = async_mock.MagicMock()
        mock.json = async_mock.CoroutineMock()

        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            # Emulate storage not found (bad pres ex id)
            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.presentation_exchange_remove(mock)

    async def test_presentation_exchange_remove_x(self):
        mock = async_mock.MagicMock()
        mock.match_info = {"pres_ex_id": "dummy"}
        mock.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.mock_context,
        }

        with async_mock.patch(
            "aries_cloudagent.protocols.present_proof.v1_0.models.presentation_exchange.V10PresentationExchange",
            autospec=True,
        ) as mock_presentation_exchange:

            # Since we are mocking import
            importlib.reload(test_module)

            mock_presentation_exchange.retrieve_by_id = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    state=mock_presentation_exchange.STATE_VERIFIED,
                    connection_id="dummy",
                    delete_record=async_mock.CoroutineMock(
                        side_effect=test_module.StorageError()
                    ),
                )
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.presentation_exchange_remove(mock)

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
