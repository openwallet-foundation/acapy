# from asynctest import TestCase as AsyncTestCase
# from asynctest import mock as async_mock

# from aiohttp import web as aio_web

# from aries_cloudagent.storage.error import StorageNotFoundError
# from aries_cloudagent.holder.base import BaseHolder
# from aries_cloudagent.config.injection_context import InjectionContext
# from aries_cloudagent.messaging.request_context import RequestContext

# from .. import routes as test_module
# from aries_cloudagent.protocols.coordinate_mediation.v1_0.models.mediation_record import MediationRecord


# class TestCoordinateMediationRoutes(AsyncTestCase):
#     def setUp(self):
#         self.context = async_mock.MagicMock()

#         self.app = {
#             "request_context": self.context,
#             "outbound_message_router": async_mock.CoroutineMock(),
#         }
    
#     # async def test_mediation_record_structure(self):
#     #     record = MediationRecord()
#     #     # assert hasattr(record,"routing_keys")
#     #     assert hasattr(record,"endpoint")
        
#     async def test_mediation_records_list(self):
#         context = RequestContext(base_context=InjectionContext(enforce_typing=False))
#         mock_req = async_mock.MagicMock()
#         mock_req.app = {"request_context": context}
#         mock_req.query = {}
#         with async_mock.patch.object(
#             test_module,
#             "MediationRecord",
#             autospec=True
#         ) as mock_records:
#             mock_records.query = async_mock.CoroutineMock()
#             records = [
#                 async_mock.MagicMock(
#                     serialize=async_mock.MagicMock(
#                         return_value={
#                             "state": MediationRecord.STATE_REQUEST_RECEIVED,
#                             "role": MediationRecord.ROLE_CLIENT,
#                             "created_at": "1234567890",
#                         }
#                     )
#                 ),
#                 async_mock.MagicMock(
#                     serialize=async_mock.MagicMock(
#                         return_value={
#                             "state": MediationRecord.STATE_GRANTED,
#                             "role": MediationRecord.ROLE_CLIENT,
#                             "created_at": "1234567890",
#                         }
#                     )
#                 ),
#                 async_mock.MagicMock(
#                     serialize=async_mock.MagicMock(
#                         return_value={
#                             "state": MediationRecord.STATE_DENIED,
#                             "role": MediationRecord.ROLE_CLIENT,
#                             "created_at": "1234567890",
#                         }
#                     )
#                 ),       
#             ]
#             mock_records.query.return_value = [records[2], records[0], records[1]]


#             with async_mock.patch.object(test_module.web, "json_response") as mock_response:
#                 res = await test_module.mediation_records_list(mock_req)
#                 mock_response.assert_called_once_with(
#                     {
#                         "results": [
#                             {
#                                 k: c.serialize.return_value[k]
#                                 for k in ["state","role", "created_at"]
#                             }
#                             for c in records
#                         ]
#                     }
#                 )
    
#     async def test_mediation_records_list_x(self):
#         context = RequestContext(
#             base_context=InjectionContext(enforce_typing=False)
#         )
#         mock_req = async_mock.MagicMock()
#         mock_req.app = {
#             "request_context": context,
#         }
#         mock_req.query = {
#             "conn_id": "dummy"
#         }

#         with async_mock.patch.object(
#             test_module, "MediationRecord", autospec=True
#         ) as mock_med_rec:
#             mock_med_rec.query = async_mock.CoroutineMock(
#                 side_effect=test_module.StorageError()
#             )

#             with self.assertRaises(test_module.web.HTTPBadRequest):
#                 await test_module.mediation_records_list(mock_req)
    
#     async def test_mediation_records_retrieve(self):
#         context = RequestContext(base_context=InjectionContext(enforce_typing=False))
#         mock_req = async_mock.MagicMock()
#         mock_req.app = {
#             "request_context": context,
#         }
#         mock_req.match_info = {"conn_id": "dummy"}
#         mock_conn_rec = async_mock.MagicMock()
#         mock_conn_rec.serialize = async_mock.MagicMock(return_value={"hello": "world"})

#         with async_mock.patch.object(
#             test_module.ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
#         ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
#             test_module.web, "json_response"
#         ) as mock_response:
#             mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec

#             await test_module.connections_retrieve(mock_req)
#             mock_response.assert_called_once_with({"hello": "world"})
    
#     async def test_mediation_records_retrieve_x(self):
#         pass
#     async def test_mediation_records_create(self):
#         pass
#     async def test_mediation_records_create_send(self):
#         pass
#     async def test_mediation_records_send_stored(self):
#         pass
#     async def test_mediation_invitation(self):
#         pass
#     async def test_mediation_record_grant(self):
#         pass
#     async def test_keylist_list_all_records(self):
#         pass
#     async def test_send_keylists_request(self):
#         pass
#     async def test_update_keylists(self):
#         pass
    
#     async def test_send_update_keylists(self):
#         pass

#     async def test_register(self):
#         mock_app = async_mock.MagicMock()
#         mock_app.add_routes = async_mock.MagicMock()

#         await test_module.register(mock_app)
#         mock_app.add_routes.assert_called_once()

#     async def test_post_process_routes(self):
#         mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
#         test_module.post_process_routes(mock_app)
#         assert "tags" in mock_app._state["swagger_dict"]
