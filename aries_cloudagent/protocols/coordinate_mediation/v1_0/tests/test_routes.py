from asynctest import TestCase as AsyncTestCase, mock as async_mock

from .. import routes as test_module
from .....admin.request_context import AdminRequestContext
from .....core.in_memory import InMemoryProfile
from .....storage.error import StorageError, StorageNotFoundError
from ..models.mediation_record import MediationRecord
from ..route_manager import RouteManager
from .....wallet.did_method import DIDMethods


class TestCoordinateMediationRoutes(AsyncTestCase):
    def setUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.profile.context.injector.bind_instance(DIDMethods, DIDMethods())
        self.context = AdminRequestContext.test_context(profile=self.profile)
        self.outbound_message_router = async_mock.CoroutineMock()
        self.request_dict = {
            "context": self.context,
            "outbound_message_router": self.outbound_message_router,
        }
        self.request = async_mock.MagicMock(
            match_info={
                "mediation_id": "test-mediation-id",
                "conn_id": "test-conn-id",
            },
            query={},
            json=async_mock.CoroutineMock(return_value={}),
            __getitem__=lambda _, k: self.request_dict[k],
        )
        serialized = {
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
        self.mock_record = async_mock.MagicMock(
            **serialized,
            serialize=async_mock.MagicMock(return_value=serialized),
            save=async_mock.CoroutineMock()
        )

    def test_mediation_sort_key(self):
        assert (
            test_module.mediation_sort_key(
                {"state": MediationRecord.STATE_DENIED, "created_at": ""}
            )
            == "2"
        )
        assert (
            test_module.mediation_sort_key(
                {"state": MediationRecord.STATE_REQUEST, "created_at": ""}
            )
            == "1"
        )
        assert (
            test_module.mediation_sort_key(
                {"state": MediationRecord.STATE_GRANTED, "created_at": ""}
            )
            == "0"
        )

    async def test_list_mediation_requests(self):
        self.request.query = {}
        with async_mock.patch.object(
            test_module.MediationRecord,
            "query",
            async_mock.CoroutineMock(return_value=[self.mock_record]),
        ) as mock_query, async_mock.patch.object(
            test_module.web, "json_response"
        ) as json_response, async_mock.patch.object(
            self.profile,
            "session",
            async_mock.MagicMock(return_value=InMemoryProfile.test_session()),
        ) as session:
            await test_module.list_mediation_requests(self.request)
            json_response.assert_called_once_with(
                {"results": [self.mock_record.serialize.return_value]}
            )
            mock_query.assert_called_once_with(session.return_value, {})

    async def test_list_mediation_requests_filters(self):
        self.request.query = {
            "state": MediationRecord.STATE_GRANTED,
            "conn_id": "test-conn-id",
        }
        with async_mock.patch.object(
            test_module.MediationRecord,
            "query",
            async_mock.CoroutineMock(return_value=[self.mock_record]),
        ) as mock_query, async_mock.patch.object(
            test_module.web, "json_response"
        ) as json_response, async_mock.patch.object(
            self.profile,
            "session",
            async_mock.MagicMock(return_value=InMemoryProfile.test_session()),
        ) as session:
            await test_module.list_mediation_requests(self.request)
            json_response.assert_called_once_with(
                {"results": [self.mock_record.serialize.return_value]}
            )
            mock_query.assert_called_once_with(
                session.return_value,
                {
                    "connection_id": "test-conn-id",
                    "state": MediationRecord.STATE_GRANTED,
                },
            )

    async def test_list_mediation_requests_x(self):
        with async_mock.patch.object(
            test_module,
            "MediationRecord",
            async_mock.MagicMock(
                query=async_mock.CoroutineMock(side_effect=test_module.StorageError())
            ),
        ) as mock_med_rec:
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.list_mediation_requests(self.request)

    async def test_list_mediation_requests_no_records(self):
        with async_mock.patch.object(
            test_module,
            "MediationRecord",
            async_mock.MagicMock(query=async_mock.CoroutineMock(return_value=[])),
        ) as mock_med_rec, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            await test_module.list_mediation_requests(self.request)
            mock_response.assert_called_once_with({"results": []})

    async def test_retrieve_mediation_request(self):
        with async_mock.patch.object(
            test_module.MediationRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_mediation_record_retrieve, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_mediation_record_retrieve.return_value = self.mock_record
            await test_module.retrieve_mediation_request(self.request)
            mock_response.assert_called_once_with(
                self.mock_record.serialize.return_value
            )
            mock_mediation_record_retrieve.assert_called()

    async def test_retrieve_mediation_request_x_not_found(self):
        with async_mock.patch.object(
            test_module.MediationRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(side_effect=test_module.StorageNotFoundError()),
        ) as mock_mediation_record_retrieve, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response, self.assertRaises(
            test_module.web.HTTPNotFound
        ):
            await test_module.retrieve_mediation_request(self.request)

    async def test_retrieve_mediation_request_x_storage_error(self):
        with async_mock.patch.object(
            test_module.MediationRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(side_effect=test_module.StorageError()),
        ) as mock_mediation_record_retrieve, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response, self.assertRaises(
            test_module.web.HTTPBadRequest
        ):
            await test_module.retrieve_mediation_request(self.request)

    async def test_delete_mediation_request(self):
        with async_mock.patch.object(
            test_module.MediationRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_mediation_record_retrieve, async_mock.patch.object(
            self.mock_record, "delete_record", async_mock.CoroutineMock()
        ) as mock_delete_record, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_mediation_record_retrieve.return_value = self.mock_record
            await test_module.delete_mediation_request(self.request)
            mock_response.assert_called_once_with(
                self.mock_record.serialize.return_value
            )
            mock_mediation_record_retrieve.assert_called()
            mock_delete_record.assert_called()

    async def test_delete_mediation_request_x_not_found(self):
        with async_mock.patch.object(
            test_module.MediationRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(side_effect=test_module.StorageNotFoundError()),
        ) as mock_mediation_record_retrieve, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response, self.assertRaises(
            test_module.web.HTTPNotFound
        ):
            await test_module.delete_mediation_request(self.request)

    async def test_delete_mediation_request_x_storage_error(self):
        with async_mock.patch.object(
            test_module.MediationRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(side_effect=test_module.StorageError()),
        ) as mock_mediation_record_retrieve, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response, self.assertRaises(
            test_module.web.HTTPBadRequest
        ):
            await test_module.delete_mediation_request(self.request)

    async def test_request_mediation(self):
        body = {
            "mediator_terms": ["meaningless string because terms are not used"],
            "recipient_terms": ["meaningless string because terms are not a 'thing'"],
        }
        self.request.json.return_value = body
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
                    self.mock_record,
                    async_mock.MagicMock(  # mediation request
                        serialize=async_mock.MagicMock(return_value={"a": "value"}),
                    ),
                )
            )
            await test_module.request_mediation(self.request)
            mock_response.assert_called_once_with(
                self.mock_record.serialize.return_value, status=201
            )
            self.outbound_message_router.assert_called()

    async def test_request_mediation_x_conn_not_ready(self):
        body = {
            "mediator_terms": ["meaningless string because terms are not used"],
            "recipient_terms": ["meaningless string because terms are not a 'thing'"],
        }
        self.request.json.return_value = body
        with async_mock.patch.object(
            test_module.ConnRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(return_value=async_mock.MagicMock(is_ready=False)),
        ) as mock_conn_rec_retrieve_by_id, self.assertRaises(
            test_module.web.HTTPBadRequest
        ) as exc:
            await test_module.request_mediation(self.request)
            assert "request connection is not ready" in exc.msg

    async def test_request_mediation_x_already_exists(self):
        body = {
            "mediator_terms": ["meaningless string because terms are not used"],
            "recipient_terms": ["meaningless string because terms are not a 'thing'"],
        }
        self.request.json.return_value = body
        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            test_module.MediationRecord,
            "exists_for_connection_id",
            async_mock.CoroutineMock(return_value=True),
        ) as mock_exists_for_conn, self.assertRaises(
            test_module.web.HTTPBadRequest
        ) as exc:
            await test_module.request_mediation(self.request)
            assert "already exists for connection" in exc.msg

    async def test_request_mediation_x_conn_not_found(self):
        body = {
            "mediator_terms": ["meaningless string because terms are not used"],
            "recipient_terms": ["meaningless string because terms are not a 'thing'"],
        }
        self.request.json.return_value = body
        with async_mock.patch.object(
            test_module.ConnRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(side_effect=test_module.StorageNotFoundError()),
        ) as mock_conn_rec_retrieve_by_id, self.assertRaises(
            test_module.web.HTTPNotFound
        ):
            await test_module.request_mediation(self.request)

    async def test_request_mediation_x_storage_error(self):
        body = {
            "mediator_terms": ["meaningless string because terms are not used"],
            "recipient_terms": ["meaningless string because terms are not a 'thing'"],
        }
        self.request.json.return_value = body
        with async_mock.patch.object(
            test_module.ConnRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(side_effect=test_module.StorageError()),
        ) as mock_conn_rec_retrieve_by_id, self.assertRaises(
            test_module.web.HTTPBadRequest
        ):
            await test_module.request_mediation(self.request)

    async def test_mediation_request_grant_role_server(self):
        self.mock_record.role = MediationRecord.ROLE_SERVER
        with async_mock.patch.object(
            test_module.MediationRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(return_value=self.mock_record),
        ) as mock_mediation_record_retrieve, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            await test_module.mediation_request_grant(self.request)
            mock_response.assert_called_once_with(
                self.mock_record.serialize.return_value, status=201
            )
            self.outbound_message_router.assert_called()

    async def test_mediation_request_grant_role_client_x(self):
        self.mock_record.role = MediationRecord.ROLE_CLIENT
        with async_mock.patch.object(
            test_module.MediationRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(return_value=self.mock_record),
        ), self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.mediation_request_grant(self.request)

    async def test_mediation_request_grant_x_rec_not_found(self):
        with async_mock.patch.object(
            test_module.MediationRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(side_effect=test_module.StorageNotFoundError()),
        ), self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.mediation_request_grant(self.request)

    async def test_mediation_request_grant_x_storage_error(self):
        with async_mock.patch.object(
            test_module.MediationRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(side_effect=test_module.StorageError()),
        ), self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.mediation_request_grant(self.request)

    async def test_mediation_request_deny_role_server(self):
        self.mock_record.role = MediationRecord.ROLE_SERVER
        with async_mock.patch.object(
            test_module.MediationRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(return_value=self.mock_record),
        ) as mock_mediation_record_retrieve, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            await test_module.mediation_request_deny(self.request)
            mock_response.assert_called_once_with(
                self.mock_record.serialize.return_value, status=201
            )
            self.outbound_message_router.assert_called()

    async def test_mediation_request_deny_role_client_x(self):
        self.mock_record.role = MediationRecord.ROLE_CLIENT
        with async_mock.patch.object(
            test_module.MediationRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_mediation_record_retrieve, async_mock.patch.object(
            test_module.web, "json_response"
        ):
            mock_mediation_record_retrieve.return_value = async_mock.MagicMock(
                role=MediationRecord.ROLE_CLIENT
            )
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.mediation_request_deny(self.request)

    async def test_mediation_request_deny_x_rec_not_found(self):
        with async_mock.patch.object(
            test_module.MediationRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(side_effect=test_module.StorageNotFoundError()),
        ), self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.mediation_request_deny(self.request)

    async def test_mediation_request_deny_x_storage_error(self):
        with async_mock.patch.object(
            test_module.MediationRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(side_effect=test_module.StorageError()),
        ), self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.mediation_request_deny(self.request)

    async def test_get_keylist(self):
        session = await self.profile.session()
        self.request.query["role"] = MediationRecord.ROLE_SERVER
        self.request.query["conn_id"] = "test-id"

        query_results = [
            async_mock.MagicMock(
                serialize=async_mock.MagicMock(
                    return_value={"serialized": "route record"}
                )
            )
        ]

        with async_mock.patch.object(
            test_module.RouteRecord,
            "query",
            async_mock.CoroutineMock(return_value=query_results),
        ) as mock_query, async_mock.patch.object(
            self.profile,
            "session",
            async_mock.MagicMock(return_value=session),
        ) as mock_session, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            await test_module.get_keylist(self.request)
            mock_response.assert_called_once_with(
                {"results": [{"serialized": "route record"}]}, status=200
            )
            mock_query.assert_called_once_with(
                mock_session.return_value,
                {"connection_id": "test-id", "role": MediationRecord.ROLE_SERVER},
            )

    async def test_get_keylist_no_matching_records(self):
        session = await self.profile.session()
        with async_mock.patch.object(
            test_module.RouteRecord,
            "query",
            async_mock.CoroutineMock(return_value=[]),
        ) as mock_query, async_mock.patch.object(
            self.profile,
            "session",
            async_mock.MagicMock(return_value=session),
        ) as mock_session, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            await test_module.get_keylist(self.request)
            mock_query.assert_called_once_with(mock_session.return_value, {})
            mock_response.assert_called_once_with({"results": []}, status=200)

    async def test_get_keylist_storage_error(self):
        with async_mock.patch.object(
            test_module.RouteRecord,
            "query",
            async_mock.CoroutineMock(side_effect=test_module.StorageError),
        ) as mock_query, self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.get_keylist(self.request)

    async def test_send_keylist_update(self):
        body = {
            "updates": [
                {
                    "recipient_key": "EwUKjVLboiLSuoWSEtDvrgrd41EUxG5bLecQrkHB63Up",
                    "action": "add",
                },
                {
                    "recipient_key": "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
                    "action": "remove",
                },
            ]
        }
        body_with_didkey = {
            "updates": [
                {
                    "recipient_key": "did:key:z6MktPjNKjb39Fpv2JM8vTBmhnQcsaWLN9Kx2fXLh2FC1GGC",
                    "action": "add",
                },
                {
                    "recipient_key": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                    "action": "remove",
                },
            ]
        }

        self.request.json.return_value = body

        with async_mock.patch.object(
            test_module.MediationRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    state=MediationRecord.STATE_GRANTED, connection_id="test-conn-id"
                )
            ),
        ) as mock_retrieve_by_id, async_mock.patch.object(
            test_module.web,
            "json_response",
            async_mock.MagicMock(
                side_effect=lambda *args, **kwargs: [*args, *kwargs.values()]
            ),
        ) as mock_response:
            results, status = await test_module.send_keylist_update(self.request)
            assert results["updates"] == body_with_didkey["updates"]
            assert status == 201

    async def test_send_keylist_update_bad_action(self):
        self.request.json.return_value = {
            "updates": [
                {
                    "recipient_key": "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
                    "action": "wrong",
                },
            ]
        }

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.send_keylist_update(self.request)

    async def test_send_keylist_update_bad_mediation_state(self):
        self.request.json.return_value = {
            "updates": [
                {
                    "recipient_key": "EwUKjVLboiLSuoWSEtDvrgrd41EUxG5bLecQrkHB63Up",
                    "action": "add",
                },
            ]
        }

        with async_mock.patch.object(
            test_module.MediationRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    state=MediationRecord.STATE_DENIED, connection_id="test-conn-id"
                )
            ),
        ) as mock_retrieve_by_id, self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.send_keylist_update(self.request)

    async def test_send_keylist_update_bad_updates(self):
        self.request.json.return_value = {"updates": []}
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.send_keylist_update(self.request)

    async def test_send_keylist_update_x_no_mediation_rec(self):
        self.request.json.return_value = {
            "updates": [
                {
                    "recipient_key": "EwUKjVLboiLSuoWSEtDvrgrd41EUxG5bLecQrkHB63Up",
                    "action": "add",
                },
            ]
        }
        with async_mock.patch.object(
            test_module.MediationRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(side_effect=test_module.StorageNotFoundError()),
        ), self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.send_keylist_update(self.request)

    async def test_send_keylist_update_x_storage_error(self):
        self.request.json.return_value = {
            "updates": [
                {
                    "recipient_key": "EwUKjVLboiLSuoWSEtDvrgrd41EUxG5bLecQrkHB63Up",
                    "action": "add",
                },
            ]
        }

        with async_mock.patch.object(
            test_module.MediationRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(side_effect=test_module.StorageError()),
        ), self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.send_keylist_update(self.request)

    @async_mock.patch.object(test_module, "MediationManager", autospec=True)
    async def test_send_keylist_query(self, mock_manager):
        self.request.json.return_value = {"filter": {"test": "filter"}}
        self.request.query = {"paginate_limit": 10, "paginate_offset": 20}
        with async_mock.patch.object(
            test_module.MediationRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(return_value=self.mock_record),
        ) as mock_retrieve_by_id, async_mock.patch.object(
            mock_manager.return_value,
            "prepare_keylist_query",
            async_mock.CoroutineMock(),
        ) as mock_prepare_keylist_query, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            await test_module.send_keylist_query(self.request)
            mock_prepare_keylist_query.assert_called_once_with(
                filter_={"test": "filter"}, paginate_limit=10, paginate_offset=20
            )
            self.outbound_message_router.assert_called()
            mock_response.assert_called_once_with(
                mock_prepare_keylist_query.return_value.serialize.return_value,
                status=201,
            )

    async def test_send_keylist_query_x_no_mediation_record(self):
        with async_mock.patch.object(
            test_module.MediationRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(side_effect=test_module.StorageNotFoundError()),
        ) as mock_retrieve_by_id, self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.send_keylist_query(self.request)

    async def test_send_keylist_query_x_storage_error(self):
        with async_mock.patch.object(
            test_module.MediationRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(side_effect=test_module.StorageError()),
        ) as mock_retrieve_by_id, self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.send_keylist_query(self.request)

    async def test_get_default_mediator(self):
        self.request.query = {}
        with async_mock.patch.object(
            test_module.web, "json_response"
        ) as json_response, async_mock.patch.object(
            test_module.MediationManager,
            "get_default_mediator",
            async_mock.CoroutineMock(return_value=self.mock_record),
        ) as mock_mgr_get_default_record:
            await test_module.get_default_mediator(self.request)
            json_response.assert_called_once_with(
                self.mock_record.serialize.return_value,
                status=200,
            )

    async def test_get_empty_default_mediator(self):
        self.request.query = {}
        with async_mock.patch.object(
            test_module.web, "json_response"
        ) as json_response, async_mock.patch.object(
            test_module.MediationManager,
            "get_default_mediator",
            async_mock.CoroutineMock(return_value=None),
        ) as mock_mgr_get_default_record:
            await test_module.get_default_mediator(self.request)
            json_response.assert_called_once_with(
                {},
                status=200,
            )

    async def test_get_default_mediator_storage_error(self):
        self.request.query = {}
        with async_mock.patch.object(
            test_module.web, "json_response"
        ) as json_response, async_mock.patch.object(
            test_module.MediationManager,
            "get_default_mediator",
            async_mock.CoroutineMock(side_effect=test_module.StorageNotFoundError()),
        ) as mock_mgr_get_default_record:
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.get_default_mediator(self.request)

    async def test_set_default_mediator(self):
        self.request.match_info = {
            "mediation_id": "fake_id",
        }
        self.request.query = {}
        with async_mock.patch.object(
            test_module.MediationManager,
            "get_default_mediator",
            async_mock.CoroutineMock(return_value=self.mock_record),
        ) as mock_mgr_get_default_record, async_mock.patch.object(
            test_module.MediationManager,
            "set_default_mediator_by_id",
            async_mock.CoroutineMock(),
        ) as mock_mgr_set_default_record_by_id, async_mock.patch.object(
            test_module.web, "json_response"
        ) as json_response:
            await test_module.set_default_mediator(self.request)
            json_response.assert_called_once_with(
                self.mock_record.serialize.return_value,
                status=201,
            )

    async def test_set_default_mediator_storage_error(self):
        self.request.match_info = {
            "mediation_id": "bad_id",
        }
        self.request.query = {}
        with async_mock.patch.object(
            test_module.MediationManager,
            "get_default_mediator",
            async_mock.CoroutineMock(side_effect=test_module.StorageError()),
        ) as mock_mgr_get_default_record, async_mock.patch.object(
            test_module.MediationManager,
            "set_default_mediator_by_id",
            async_mock.CoroutineMock(side_effect=test_module.StorageError()),
        ) as mock_mgr_set_default_record_by_id, async_mock.patch.object(
            test_module.web, "json_response"
        ) as json_response:
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.set_default_mediator(self.request)

    async def test_clear_default_mediator(self):
        self.request.query = {}
        with async_mock.patch.object(
            test_module.MediationManager,
            "get_default_mediator",
            async_mock.CoroutineMock(return_value=self.mock_record),
        ) as mock_mgr_get_default_record, async_mock.patch.object(
            test_module.MediationManager,
            "clear_default_mediator",
            async_mock.CoroutineMock(),
        ) as mock_mgr_clear_default_record_by_id, async_mock.patch.object(
            test_module.web, "json_response"
        ) as json_response:
            await test_module.clear_default_mediator(self.request)
            json_response.assert_called_once_with(
                self.mock_record.serialize.return_value,
                status=201,
            )

    async def test_clear_default_mediator_storage_error(self):
        self.request.query = {}
        with async_mock.patch.object(
            test_module.MediationManager,
            "get_default_mediator",
            async_mock.CoroutineMock(side_effect=test_module.StorageError()),
        ) as mock_mgr_get_default_record, async_mock.patch.object(
            test_module.MediationManager,
            "clear_default_mediator",
            async_mock.CoroutineMock(),
        ) as mock_mgr_clear_default_record_by_id, async_mock.patch.object(
            test_module.web, "json_response"
        ) as json_response:
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.clear_default_mediator(self.request)

    async def test_update_keylist_for_connection(self):
        self.request.query = {}
        self.request.json.return_value = {"mediation_id": "test-mediation-id"}
        self.request.match_info = {
            "conn_id": "test-conn-id",
        }
        mock_route_manager = async_mock.MagicMock(RouteManager)
        mock_keylist_update = async_mock.MagicMock()
        mock_keylist_update.serialize.return_value = {"mock": "serialized"}
        mock_route_manager.route_connection = async_mock.CoroutineMock(
            return_value=mock_keylist_update
        )
        mock_route_manager.mediation_record_for_connection = async_mock.CoroutineMock()
        self.context.injector.bind_instance(RouteManager, mock_route_manager)
        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            test_module.web, "json_response"
        ) as json_response:
            await test_module.update_keylist_for_connection(self.request)
            json_response.assert_called_once_with({"mock": "serialized"}, status=200)

    async def test_update_keylist_for_connection_not_found(self):
        self.request.query = {}
        self.request.json.return_value = {"mediation_id": "test-mediation-id"}
        self.request.match_info = {
            "conn_id": "test-conn-id",
        }
        mock_route_manager = async_mock.MagicMock(RouteManager)
        mock_keylist_update = async_mock.MagicMock()
        mock_keylist_update.serialize.return_value = {"mock": "serialized"}
        mock_route_manager.route_connection = async_mock.CoroutineMock(
            return_value=mock_keylist_update
        )
        mock_route_manager.mediation_record_for_connection = async_mock.CoroutineMock()
        self.context.injector.bind_instance(RouteManager, mock_route_manager)
        with async_mock.patch.object(
            test_module.ConnRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(side_effect=StorageNotFoundError),
        ) as mock_conn_rec_retrieve_by_id:
            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.update_keylist_for_connection(self.request)

    async def test_update_keylist_for_connection_storage_error(self):
        self.request.query = {}
        self.request.json.return_value = {"mediation_id": "test-mediation-id"}
        self.request.match_info = {
            "conn_id": "test-conn-id",
        }
        mock_route_manager = async_mock.MagicMock(RouteManager)
        mock_keylist_update = async_mock.MagicMock()
        mock_keylist_update.serialize.return_value = {"mock": "serialized"}
        mock_route_manager.route_connection = async_mock.CoroutineMock(
            return_value=mock_keylist_update
        )
        mock_route_manager.mediation_record_for_connection = async_mock.CoroutineMock()
        self.context.injector.bind_instance(RouteManager, mock_route_manager)
        with async_mock.patch.object(
            test_module.ConnRecord,
            "retrieve_by_id",
            async_mock.CoroutineMock(side_effect=StorageError),
        ) as mock_conn_rec_retrieve_by_id:
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.update_keylist_for_connection(self.request)

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
