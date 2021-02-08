from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from marshmallow import ValidationError

from .....messaging.request_context import RequestContext
from .....storage.error import (
    StorageDuplicateError,
    StorageError,
    StorageNotFoundError,
)
from .....storage.in_memory import InMemoryStorage
from .....transport.inbound.receipt import MessageReceipt

from ..manager import RoutingManager, RoutingManagerError, RouteNotFoundError
from ..models.route_record import RouteRecord, RouteRecordSchema
from ..models.route_update import RouteUpdate
from ..models.route_updated import RouteUpdated

TEST_CONN_ID = "conn-id"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_ROUTE_VERKEY = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"


class TestRoutingManager(AsyncTestCase):
    async def setUp(self):
        self.context = RequestContext.test_context()
        self.context.message_receipt = MessageReceipt(sender_verkey=TEST_VERKEY)
        self.transaction = await self.context.transaction()  # for coverage
        self.profile = self.context.profile
        self.manager = RoutingManager(self.profile)

    async def test_create_manager_no_context(self):
        with self.assertRaises(RoutingManagerError):
            await RoutingManager(None)

    async def test_create_retrieve(self):
        await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        record = await self.manager.get_recipient(TEST_ROUTE_VERKEY)
        assert isinstance(record, RouteRecord)
        assert record.connection_id == TEST_CONN_ID
        assert record.recipient_key == TEST_ROUTE_VERKEY

        results = await self.manager.get_routes()
        assert len(results) == 1
        assert results[0].connection_id == TEST_CONN_ID
        assert results[0].recipient_key == TEST_ROUTE_VERKEY

    async def test_route_record_schema_validate(self):
        route_rec_schema = RouteRecordSchema()
        with self.assertRaises(ValidationError):
            route_rec_schema.validate_fields({})

    async def test_get_routes_retrieve_none(self):
        results = await self.manager.get_routes()
        assert results == []

    async def test_create_x(self):
        with self.assertRaises(RoutingManagerError):
            await self.manager.create_route_record(None, TEST_ROUTE_VERKEY)

        with self.assertRaises(RoutingManagerError):
            await self.manager.create_route_record(TEST_CONN_ID, None)

    async def test_create_delete(self):
        record = await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        await self.manager.delete_route_record(record)
        results = await self.manager.get_routes()
        assert not results

    async def test_get_recipient_no_verkey(self):
        with self.assertRaises(RoutingManagerError) as context:
            await self.manager.get_recipient(None)
        assert "Must pass non-empty" in str(context.exception)

    async def test_get_recipient_duplicate_routes(self):
        with async_mock.patch.object(
            RouteRecord, "retrieve_by_recipient_key", async_mock.CoroutineMock()
        ) as mock_retrieve:
            mock_retrieve.side_effect = StorageDuplicateError()
            with self.assertRaises(RouteNotFoundError) as context:
                await self.manager.get_recipient(TEST_ROUTE_VERKEY)
        assert "More than one route" in str(context.exception)

    async def test_get_recipient_no_routes(self):
        with async_mock.patch.object(
            RouteRecord, "retrieve_by_recipient_key", async_mock.CoroutineMock()
        ) as mock_retrieve:
            mock_retrieve.side_effect = StorageNotFoundError()
            with self.assertRaises(RouteNotFoundError) as context:
                await self.manager.get_recipient(TEST_ROUTE_VERKEY)
        assert "No route found" in str(context.exception)

    async def test_get_routes_connection_id(self):
        await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        results = await self.manager.get_routes(
            client_connection_id=TEST_CONN_ID, tag_filter=None
        )
        assert len(results) == 1
        assert results[0].connection_id == TEST_CONN_ID
        assert results[0].recipient_key == TEST_ROUTE_VERKEY

    async def test_get_routes_connection_id_tag_filter_vacuous(self):
        await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        results = await self.manager.get_routes(
            client_connection_id=None, tag_filter={"for": "coverage"}
        )
        assert len(results) == 1
        assert results[0].connection_id == TEST_CONN_ID
        assert results[0].recipient_key == TEST_ROUTE_VERKEY

    async def test_get_routes_connection_id_tag_filter_str(self):
        await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        results = await self.manager.get_routes(
            client_connection_id=None, tag_filter={"recipient_key": TEST_ROUTE_VERKEY}
        )
        assert len(results) == 1
        assert results[0].connection_id == TEST_CONN_ID
        assert results[0].recipient_key == TEST_ROUTE_VERKEY

    async def test_get_routes_connection_id_tag_filter_list(self):
        await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        results = await self.manager.get_routes(
            client_connection_id=None, tag_filter={"recipient_key": [TEST_ROUTE_VERKEY]}
        )
        assert len(results) == 1
        assert results[0].connection_id == TEST_CONN_ID
        assert results[0].recipient_key == TEST_ROUTE_VERKEY

    async def test_get_routes_connection_id_tag_filter_list_miss(self):
        await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        results = await self.manager.get_routes(
            client_connection_id=None,
            tag_filter={"recipient_key": ["none", "of", "these"]},
        )
        assert len(results) == 0

    async def test_get_routes_connection_id_tag_filter_list_among_plural(self):
        await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        results = await self.manager.get_routes(
            client_connection_id=None,
            tag_filter={"recipient_key": ["none", TEST_ROUTE_VERKEY, "of", "these"]},
        )
        assert len(results) == 1
        assert results[0].connection_id == TEST_CONN_ID
        assert results[0].recipient_key == TEST_ROUTE_VERKEY

    async def test_get_routes_connection_id_tag_filter_x(self):
        await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        with self.assertRaises(RoutingManagerError):
            await self.manager.get_routes(
                client_connection_id=None, tag_filter={"recipient_key": None}
            )

    async def test_get_routes_client_routes_not_returned(self):
        await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        async with self.profile.session() as session:
            await RouteRecord(
                role=RouteRecord.ROLE_CLIENT,
                connection_id=TEST_CONN_ID,
                recipient_key=TEST_ROUTE_VERKEY,
            ).save(session)
        results = await self.manager.get_routes()
        assert len(results) == 1
        assert results[0].connection_id == TEST_CONN_ID
        assert results[0].recipient_key == TEST_ROUTE_VERKEY

    async def test_route_rec_retrieve_eq(self):
        route_rec = RouteRecord(
            role=RouteRecord.ROLE_CLIENT,
            connection_id=TEST_CONN_ID,
            recipient_key=TEST_ROUTE_VERKEY,
        )
        async with self.profile.session() as session:
            await route_rec.save(session)
            by_conn_id = await RouteRecord.retrieve_by_connection_id(
                session=session,
                connection_id=TEST_CONN_ID,
            )
        assert by_conn_id == route_rec
        assert route_rec != ValueError()

    async def test_update_routes_delete(self):
        await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        results = await self.manager.update_routes(
            client_connection_id=TEST_CONN_ID,
            updates=[
                RouteUpdate(
                    recipient_key=TEST_ROUTE_VERKEY, action=RouteUpdate.ACTION_DELETE
                )
            ],
        )
        assert len(results) == 1
        assert results[0].recipient_key == TEST_ROUTE_VERKEY
        assert results[0].action == RouteUpdate.ACTION_DELETE
        assert results[0].result == RouteUpdated.RESULT_SUCCESS

    async def test_update_routes_create(self):
        results = await self.manager.update_routes(
            client_connection_id=TEST_CONN_ID,
            updates=[
                RouteUpdate(
                    recipient_key=TEST_ROUTE_VERKEY, action=RouteUpdate.ACTION_CREATE
                )
            ],
        )
        assert len(results) == 1
        assert results[0].recipient_key == TEST_ROUTE_VERKEY
        assert results[0].action == RouteUpdate.ACTION_CREATE
        assert results[0].result == RouteUpdated.RESULT_SUCCESS

    async def test_update_routes_create_existing(self):
        await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        results = await self.manager.update_routes(
            client_connection_id=TEST_CONN_ID,
            updates=[
                RouteUpdate(
                    recipient_key=TEST_ROUTE_VERKEY, action=RouteUpdate.ACTION_CREATE
                )
            ],
        )
        assert len(results) == 1
        assert results[0].recipient_key == TEST_ROUTE_VERKEY
        assert results[0].action == RouteUpdate.ACTION_CREATE
        assert results[0].result == RouteUpdated.RESULT_NO_CHANGE

    async def test_update_routes_no_recipient_key(self):
        await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        results = await self.manager.update_routes(
            client_connection_id=TEST_CONN_ID,
            updates=[RouteUpdate(recipient_key=None, action=RouteUpdate.ACTION_DELETE)],
        )
        assert len(results) == 1
        assert results[0].recipient_key is None
        assert results[0].action == RouteUpdate.ACTION_DELETE
        assert results[0].result == RouteUpdated.RESULT_CLIENT_ERROR

    async def test_update_routes_unsupported_action(self):
        await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        results = await self.manager.update_routes(
            client_connection_id=TEST_CONN_ID,
            updates=[RouteUpdate(recipient_key=TEST_ROUTE_VERKEY, action="mystery")],
        )
        assert len(results) == 1
        assert results[0].recipient_key == TEST_ROUTE_VERKEY
        assert results[0].action == "mystery"
        assert results[0].result == RouteUpdated.RESULT_CLIENT_ERROR

    async def test_update_routes_create_server_error(self):
        with async_mock.patch.object(
            self.manager, "create_route_record", async_mock.CoroutineMock()
        ) as mock_mgr_create_route_record:
            mock_mgr_create_route_record.side_effect = RoutingManagerError()
            results = await self.manager.update_routes(
                client_connection_id=TEST_CONN_ID,
                updates=[
                    RouteUpdate(
                        recipient_key=TEST_ROUTE_VERKEY,
                        action=RouteUpdate.ACTION_CREATE,
                    )
                ],
            )
            assert len(results) == 1
            assert results[0].recipient_key == TEST_ROUTE_VERKEY
            assert results[0].action == RouteUpdate.ACTION_CREATE
            assert results[0].result == RouteUpdated.RESULT_SERVER_ERROR

    async def test_update_routes_delete_absent(self):
        results = await self.manager.update_routes(
            client_connection_id=TEST_CONN_ID,
            updates=[
                RouteUpdate(
                    recipient_key=TEST_ROUTE_VERKEY, action=RouteUpdate.ACTION_DELETE
                )
            ],
        )
        assert len(results) == 1
        assert results[0].recipient_key == TEST_ROUTE_VERKEY
        assert results[0].action == RouteUpdate.ACTION_DELETE
        assert results[0].result == RouteUpdated.RESULT_NO_CHANGE

    async def test_update_routes_delete_server_error(self):
        await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        with async_mock.patch.object(
            self.manager, "delete_route_record", async_mock.CoroutineMock()
        ) as mock_mgr_delete_route_record:
            mock_mgr_delete_route_record.side_effect = StorageError()
            results = await self.manager.update_routes(
                client_connection_id=TEST_CONN_ID,
                updates=[
                    RouteUpdate(
                        recipient_key=TEST_ROUTE_VERKEY,
                        action=RouteUpdate.ACTION_DELETE,
                    )
                ],
            )
            assert len(results) == 1
            assert results[0].recipient_key == TEST_ROUTE_VERKEY
            assert results[0].action == RouteUpdate.ACTION_DELETE
            assert results[0].result == RouteUpdated.RESULT_SERVER_ERROR

    async def test_send_create_route(self):
        mock_outbound_handler = async_mock.CoroutineMock()
        await self.manager.send_create_route(
            router_connection_id=TEST_CONN_ID,
            recip_key=TEST_ROUTE_VERKEY,
            outbound_handler=mock_outbound_handler,
        )
        mock_outbound_handler.assert_called_once()
