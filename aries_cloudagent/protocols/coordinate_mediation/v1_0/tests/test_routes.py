from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock


from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.messaging.request_context import RequestContext

from .. import routes as test_module
from ..models.mediation_record import MediationRecord
from aries_cloudagent.admin.request_context import AdminRequestContext
from aries_cloudagent.protocols.coordinate_mediation.v1_0.manager import MediationManager
import json


class TestCoordinateMediationRoutes(AsyncTestCase):
    async def setUp(self):
        self.session_inject = {}
        self.context = AdminRequestContext.test_context(self.session_inject)
        self.request_dict = {"context": self.context}
        self.request = async_mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
        )

    async def test_mediation_records_list(self):
        records = [MediationRecord(
            mediation_id="fake_id",
            state=MediationRecord.STATE_GRANTED,
            role=MediationRecord.ROLE_SERVER,
            connection_id="c3dd00cf-f6a2-4ddf-93d8-49ae74bdacef",
            mediator_terms=[],
            recipient_terms=[],
            routing_keys=["EwUKjVLboiLSuoWSEtDvrgrd41EUxG5bLecQrkHB63Up"],
            endpoint="http://192.168.1.13:3005"),
        ]
        self.session_inject[MediationRecord] = async_mock.MagicMock(
            query=async_mock.CoroutineMock(
                return_value=records
            )
        )
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            result = await test_module.mediation_records_list(self.request)
            json_response.assert_called_once_with([])  # TODO: is this right?
            assert result is json_response.return_value

    async def test_mediation_records_list_state_filter(self):
        self.request.query = {"state": MediationRecord.STATE_GRANTED}
        records = [MediationRecord(
            state=MediationRecord.STATE_GRANTED,
            role=MediationRecord.ROLE_SERVER,
            connection_id="c3dd00cf-f6a2-4ddf-93d8-49ae74bdacef",
            mediator_terms=[],
            recipient_terms=[],
            routing_keys=["EwUKjVLboiLSuoWSEtDvrgrd41EUxG5bLecQrkHB63Up"],
            endpoint="http://192.168.1.13:3005")
        ]
        self.session_inject[MediationRecord] = async_mock.MagicMock(
            query=async_mock.CoroutineMock(
                return_value=records
            )
        )
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            result = await test_module.mediation_records_list(self.request)
            # json_response.assert_called_once_with(["state"])
            assert result is json_response.return_value

    async def test_mediation_records_list_x(self):
        self.session_inject[MediationRecord] = async_mock.MagicMock(
            query=async_mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )
        )
        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.mediation_records_list(self.request)

    async def test_mediation_records_retrieve(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {"request_context": context}
        mock_req.match_info = {"mediation_id": "c3dd00cf-f6a2-4ddf-93d8-49ae74bdacef"}
        mock_mediation_rec = async_mock.MagicMock()
        mock_mediation_rec.serialize = async_mock.MagicMock(
            return_value={
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
        )
        with async_mock.patch.object(
            test_module.MediationRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_mediation_record_retrieve, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_mediation_rec_retrieve_by_id.return_value = mock_mediation_rec

            await test_module.mediation_record_retrieve(mock_req)
            mock_response.assert_called_once_with(
                {
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
            )

    async def test_mediation_records_retrieve_x(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_bad_req = async_mock.MagicMock()
        mock_bad_req.app = {"request_context": context}
        mock_bad_req.match_info = {
            "mediation_id": "c3dd00cf-f6a2-4ddf-93d8-49ae74bdacef"
        }
        with async_mock.patch.object(
            test_module, "MediationRecord", autospec=True
        ) as mock_med_rec:
            mock_med_rec.query = async_mock.CoroutineMock(
                side_effect=test_module.StorageError()
            )
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.mediation_record_retrieve(mock_bad_req)

    async def test_mediation_records_create(self):
        pass

    async def test_mediation_records_create_send(self):
        pass

    async def test_mediation_records_send_stored(self):
        pass

    async def test_mediation_invitation(self):
        pass

    async def test_mediation_record_grant(self):
        pass

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
