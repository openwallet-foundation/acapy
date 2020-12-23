from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock


from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.messaging.request_context import RequestContext

from .. import routes as test_module
from ..models.mediation_record import MediationRecord
from aries_cloudagent.admin.request_context import AdminRequestContext
from aries_cloudagent.protocols.coordinate_mediation.v1_0.manager import (
    MediationManager,
)
import json
import asynctest


class TestCoordinateMediationRoutes(AsyncTestCase):
    def setUp(self):
        self.session_inject = {}
        self.context = AdminRequestContext.test_context(self.session_inject)
        self.request_dict = {"context": self.context}
        self.request = async_mock.MagicMock(
            app={"outbound_message_router": async_mock.CoroutineMock()},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
        )
        self.record = {
            "mediation_id": "fake_id",
            "state": "granted",
            "role": "server",
            "connection_id": "c3dd00cf-f6a2-4ddf-93d8-49ae74bdacef",
            "mediator_terms": [],
            "recipient_terms": [],
            "routing_keys": ["EwUKjVLboiLSuoWSEtDvrgrd41EUxG5bLecQrkHB63Up"],
            "endpoint": "http://192.168.1.13:3005",
            "created_at": "1234567890",
        }
        self.records = [
            async_mock.MagicMock(
                serialize=async_mock.MagicMock(return_value=self.record)
            )
        ]

    async def test_mediation_records_list(self):
        self.request.query = {}
        with async_mock.patch.object(
            test_module, "MediationRecord", autospec=True
        ) as mock_med_rec:
            mock_med_rec.query = async_mock.CoroutineMock(return_value=self.records)
            with async_mock.patch.object(
                test_module.web, "json_response"
            ) as json_response:
                result = await test_module.mediation_records_list(self.request)
                json_response.assert_called_once_with([self.record])
                mock_med_rec.query.assert_called()
                assert result is json_response.return_value

    async def test_mediation_records_list_state_filter(self):
        self.request.query = {"state": MediationRecord.STATE_GRANTED}
        with async_mock.patch.object(
            test_module, "MediationRecord", autospec=True
        ) as mock_med_rec:
            mock_med_rec.query = async_mock.CoroutineMock(return_value=self.records)
            with async_mock.patch.object(
                test_module.web, "json_response"
            ) as json_response:
                result = await test_module.mediation_records_list(self.request)
                json_response.assert_called_once_with([self.record])
                mock_med_rec.query.assert_called()
                # mock_med_rec.query.assert_called_once_with(["state"])#FIXME
                assert result is json_response.return_value

    async def test_mediation_records_list_x(self):
        with async_mock.patch.object(
            test_module, "MediationRecord", autospec=True
        ) as mock_med_rec:
            mock_med_rec.query = async_mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.mediation_records_list(self.request)
            # with async_mock.patch.object(
            #     test_module.web, "json_response"
            # ) as json_response:
            #     result = await test_module.mediation_records_list(self.request)
            #     json_response.assert_called_once_with([])
            #     mock_med_rec.query.assert_called()
            #     assert result is json_response.return_value

    async def test_mediation_records_retrieve(self):
        self.request.match_info = {
            "mediation_id": "c3dd00cf-f6a2-4ddf-93d8-49ae74bdacef"
        }
        mock_mediation_rec = async_mock.MagicMock()
        record = {
            "recipient_keys": ["5r4SX9xRHmfv3iC4EWMY4ZLSwUY8tXiTrP29y54zqE2Y"],
            "created_at": "2020-12-02 16:50:56.751163Z",
            "state": "granted",
            "role": "server",
            "endpoint": "http://192.168.1.13:3005",
            "routing_keys": ["EwUKjVLboiLSuoWSEtDvrgrd41EUxG5bLecQrkHB63Up"],
            "connection_id": "c3dd00cf-f6a2-4ddf-93d8-49ae74bdacef",
            "updated_at": "2020-12-02 16:50:56.870189Z",
            "mediator_terms": [],
            "mediation_id": "57a445ce-add4-4536-bc65-b630e6cef759",
            "recipient_terms": [],
        }
        mock_mediation_rec.serialize = async_mock.MagicMock(return_value=record)
        with async_mock.patch.object(
            test_module.MediationRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_mediation_record_retrieve, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_mediation_record_retrieve.return_value = mock_mediation_rec
            await test_module.mediation_record_retrieve(self.request)
            mock_response.assert_called_once_with(record)
            mock_mediation_record_retrieve.assert_called()

    async def test_mediation_records_retrieve_x(self):
        self.request.match_info = {
            "mediation_id": "c3dd00cf-f6a2-4ddf-93d8-49ae74bdacef"
        }

        with async_mock.patch.object(
            test_module, "MediationRecord", autospec=True
        ) as mock_med_rec, async_mock.patch.object(
            test_module.MediationRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_mediation_record_retrieve, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_mediation_record_retrieve = async_mock.CoroutineMock(
                side_effect=test_module.StorageError()
            )
            # with self.assertRaises(test_module.web.HTTPBadRequest):
            #    await test_module.mediation_record_retrieve(self.request)
            await test_module.mediation_record_retrieve(
                self.request
            )  # TODO: desired behavior?

    async def test_mediation_records_create(self):
        self.request.match_info = {"conn_id": "c3dd00cf-f6a2-4ddf-93d8-49ae74bdacef"}
        body = {
            "mediator_terms": ["meaningless string because terms are not used"],
            "recipient_terms": ["meaningless string because terms are not a 'thing'"],
            "role": MediationRecord.ROLE_SERVER
        }
        self.request.json = async_mock.CoroutineMock(return_value=body)
        self.request.query = {
            "auto_send": "false",
        }
        mock_mediation_rec = async_mock.MagicMock()
        record = {
            "fake": "mediation record",
            "but": "serialized",
            "role": MediationRecord.ROLE_CLIENT
        }
        mock_mediation_rec.serialize = async_mock.MagicMock(return_value=record)
        mock_mediation_rec.save = async_mock.CoroutineMock()
        with async_mock.patch.object(
            test_module, "MediationManager", autospec=True
        ) as mock_med_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response, async_mock.patch.object(
            test_module.MediationRecord,
            "exists_for_connection_id",
            async_mock.CoroutineMock(return_value=False),
        ) as mock_mediation_record_exists, async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_med_mgr.return_value.prepare_request = async_mock.CoroutineMock(
                return_value=(
                    mock_mediation_rec,
                    async_mock.MagicMock(  # mediation request
                        serialize=async_mock.MagicMock(return_value={"a": "value"}),
                    ),
                )
            )
            await test_module.mediation_create_request(self.request)
            mock_response.assert_called_once_with(
                mock_mediation_rec.serialize.return_value, status=201
            )
            self.request.app["outbound_message_router"].assert_not_called()

    async def test_mediation_records_create_send(self):
        self.request.match_info = {"conn_id": "c3dd00cf-f6a2-4ddf-93d8-49ae74bdacef"}
        body = {
            "mediator_terms": ["meaningless string because terms are not used"],
            "recipient_terms": ["meaningless string because terms are not a 'thing'"],
            "role": MediationRecord.ROLE_CLIENT
        }
        self.request.json = async_mock.CoroutineMock(return_value=body)
        self.request.query = {
            "auto_send": "true",
        }
        mock_mediation_rec = async_mock.MagicMock()
        record = {
            "fake": "mediation record",
            "but": "serialized",
            "role": MediationRecord.ROLE_CLIENT
        }
        mock_mediation_rec.serialize = async_mock.MagicMock(return_value=record)
        mock_mediation_rec.save = async_mock.CoroutineMock()
        with async_mock.patch.object(
            test_module, "MediationManager", autospec=True
        ) as mock_med_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response, async_mock.patch.object(
            test_module.MediationRecord,
            "exists_for_connection_id",
            async_mock.CoroutineMock(return_value=False),
        ) as mock_mediation_record_exists, async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_med_mgr.return_value.prepare_request = async_mock.CoroutineMock(
                return_value=(
                    mock_mediation_rec,
                    async_mock.MagicMock(  # mediation request
                        serialize=async_mock.MagicMock(return_value={"a": "value"}),
                    ),
                )
            )
            await test_module.mediation_create_request(self.request)
            mock_response.assert_called_once_with(
                mock_mediation_rec.serialize.return_value, status=201
            )
            self.request.app["outbound_message_router"].assert_called_once()
            self.request.app["outbound_message_router"].assert_called_once_with(
                mock_med_mgr.return_value.prepare_request.return_value[1],
                connection_id='c3dd00cf-f6a2-4ddf-93d8-49ae74bdacef')

    async def test_mediation_records_create_auto_send_role_server(self):
        self.request.match_info = {"conn_id": "c3dd00cf-f6a2-4ddf-93d8-49ae74bdacef"}
        body = {
            "mediator_terms": ["meaningless string because terms are not used"],
            "recipient_terms": ["meaningless string because terms are not a 'thing'"],
            "role": MediationRecord.ROLE_SERVER
        }
        self.request.json = async_mock.CoroutineMock(return_value=body)
        self.request.query = {
            "auto_send": "true",
        }
        mock_mediation_rec = async_mock.MagicMock()
        record = {
            "fake": "mediation record",
            "but": "serialized",
            "role": MediationRecord.ROLE_CLIENT
        }
        mock_mediation_rec.serialize = async_mock.MagicMock(return_value=record)
        mock_mediation_rec.save = async_mock.CoroutineMock()
        with async_mock.patch.object(
            test_module, "MediationManager", autospec=True
        ) as mock_med_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response, async_mock.patch.object(
            test_module.MediationRecord,
            "exists_for_connection_id",
            async_mock.CoroutineMock(return_value=False),
        ) as mock_mediation_record_exists, async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_med_mgr.return_value.prepare_request = async_mock.CoroutineMock(
                return_value=(
                    mock_mediation_rec,
                    async_mock.MagicMock(  # mediation request
                        serialize=async_mock.MagicMock(return_value={"a": "value"}),
                    ),
                )
            )
            await test_module.mediation_create_request(self.request)
            mock_response.assert_called_once_with(
                mock_mediation_rec.serialize.return_value, status=201
            )
            self.request.app["outbound_message_router"].assert_not_called()

    async def test_mediation_records_send_stored(self):
        self.request.match_info = {"mediation_id": "c3dd00cf-f6a2-4ddf-93d8-49ae74bdacef"}
        body = {
            "mediator_terms": ["meaningless string because terms are not used"],
            "recipient_terms": ["meaningless string because terms are not a 'thing'"]
        }
        self.request.json = async_mock.CoroutineMock(return_value=body)
        self.request.query = {
            "auto_send": "true",
        }
        mock_mediation_rec = async_mock.MagicMock()
        record = {
            "fake": "mediation record",
            "but": "serialized",
            "role": MediationRecord.ROLE_CLIENT,
            "connection_id": "c3dd00cf-f6a2-4ddf-93d8-49ae74bdacef"
        }
        mock_mediation_rec.serialize = async_mock.MagicMock(return_value=record)
        with async_mock.patch.object(
            test_module.MediationRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_mediation_record_retrieve, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:  # TODO: mock MediationRequest, check mocked msg sent
            mock_mediation_record_retrieve.return_value = mock_mediation_rec
            await test_module.send_mediation_request(self.request)
            mock_response.assert_called_once_with(
                mock_mediation_rec.serialize.return_value, status=201
            )
            self.request.app["outbound_message_router"].assert_called()
    
    async def test_mediation_invitation(self):
        pass  # Todo: implement in connection manager tests if not already.

    async def test_mediation_record_grant_role_server(self):
        self.request.match_info = {"mediation_id": "c3dd00cf-f6a2-4ddf-93d8-49ae74bdacef"}
        self.request.json = async_mock.CoroutineMock(return_value={})  # must have body
        mock_mediation_rec = async_mock.MagicMock()
        record = {
            "fake": "mediation record",
            "but": "serialized",
            # "role": MediationRecord.ROLE_SERVER,
            "connection_id": "c3dd00cf-f6a2-4ddf-93d8-49ae74bdacef"
        }
        mock_mediation_rec.serialize = async_mock.MagicMock(return_value=record)
        mock_mediation_rec.role = MediationRecord.ROLE_SERVER
        mock_mediation_rec.save = async_mock.CoroutineMock()
        with async_mock.patch.object(
            test_module.MediationRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_mediation_record_retrieve, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:  # TODO: mock MediationRequest, check mocked msg sent
            mock_mediation_record_retrieve.return_value = mock_mediation_rec
            await test_module.mediation_record_grant(self.request)
            mock_response.assert_called_once_with(
                mock_mediation_rec.serialize.return_value, status=201
            )
            self.request.app["outbound_message_router"].assert_called()

    async def test_mediation_record_grant_role_client(self):
        self.request.match_info = {"mediation_id": "c3dd00cf-f6a2-4ddf-93d8-49ae74bdacef"}
        self.request.json = async_mock.CoroutineMock(return_value={})
        mock_mediation_rec = async_mock.MagicMock()
        record = {
            "fake": "mediation record",
            "but": "serialized",
            "role": MediationRecord.ROLE_CLIENT,
            "connection_id": "c3dd00cf-f6a2-4ddf-93d8-49ae74bdacef"
        }
        mock_mediation_rec.serialize = async_mock.MagicMock(return_value=record)
        with async_mock.patch.object(
            test_module.MediationRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_mediation_record_retrieve, async_mock.patch.object(
            test_module.web, "json_response"
        ):
            mock_mediation_record_retrieve.return_value = mock_mediation_rec
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.mediation_record_grant(self.request)

    async def test_mediation_record_deny_role_server(self):
        self.request.match_info = {"mediation_id": "c3dd00cf-f6a2-4ddf-93d8-49ae74bdacef"}
        self.request.json = async_mock.CoroutineMock(return_value={})  # must have body
        mock_mediation_rec = async_mock.MagicMock()
        record = {
            "fake": "mediation record",
            "but": "serialized",
            # "role": MediationRecord.ROLE_SERVER,
            "connection_id": "c3dd00cf-f6a2-4ddf-93d8-49ae74bdacef"
        }
        mock_mediation_rec.serialize = async_mock.MagicMock(return_value=record)
        mock_mediation_rec.role = MediationRecord.ROLE_SERVER
        mock_mediation_rec.save = async_mock.CoroutineMock()
        with async_mock.patch.object(
            test_module.MediationRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_mediation_record_retrieve, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:  # TODO: mock Request, check mocked msg sent
            mock_mediation_record_retrieve.return_value = mock_mediation_rec
            await test_module.mediation_record_deny(self.request)
            mock_response.assert_called_once_with(
                mock_mediation_rec.serialize.return_value, status=201
            )
            self.request.app["outbound_message_router"].assert_called()

    async def test_mediation_record_deny_role_client(self):
        self.request.match_info = {"mediation_id": "c3dd00cf-f6a2-4ddf-93d8-49ae74bdacef"}
        self.request.json = async_mock.CoroutineMock(return_value={})
        mock_mediation_rec = async_mock.MagicMock()
        record = {
            "fake": "mediation record",
            "but": "serialized",
            "role": MediationRecord.ROLE_CLIENT,
            "connection_id": "c3dd00cf-f6a2-4ddf-93d8-49ae74bdacef"
        }
        mock_mediation_rec.serialize = async_mock.MagicMock(return_value=record)
        with async_mock.patch.object(
            test_module.MediationRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_mediation_record_retrieve, async_mock.patch.object(
            test_module.web, "json_response"
        ):
            mock_mediation_record_retrieve.return_value = mock_mediation_rec
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.mediation_record_deny(self.request)

    async def test_keylist_list_all_records(self):
        pass

    async def test_send_keylists_request(self):
        pass

    async def test_update_keylists(self):
        pass

    async def test_send_update_keylists(self):
        pass

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
