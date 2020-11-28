from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .....core.in_memory import InMemoryProfile
from .....messaging.request_context import RequestContext
from .....storage.error import (
    StorageDuplicateError,
    StorageError,
    StorageNotFoundError,
)
from .....storage.in_memory import InMemoryStorage
from .....transport.inbound.receipt import MessageReceipt

from ..manager import RoutingManager, RoutingManagerError, RouteNotFoundError
from ..models.route_record import RouteRecord
from ..models.route_update import RouteUpdate
from ..models.route_updated import RouteUpdated

TEST_CONN_ID = "conn-id"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_ROUTE_VERKEY = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"


class TestRoutingManager(AsyncTestCase):
    async def setUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.context = RequestContext(self.profile)
        self.context.message_receipt = MessageReceipt(sender_verkey=TEST_VERKEY)
        self.manager = RoutingManager(self.context)
        assert self.manager.context

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

    async def test_get_recipient_no_recipient(self):
        with self.assertRaises(RoutingManagerError):
            await self.manager.get_recipient(TEST_ROUTE_VERKEY)

    async def test_get_recipient_duplicate_routes(self):
        with async_mock.patch.object(
            InMemoryStorage, "find_record", autospec=True
        ) as mock_search:
            mock_search.side_effect = StorageDuplicateError
            with self.assertRaises(RouteNotFoundError):
                await self.manager.get_recipient(TEST_ROUTE_VERKEY)

    async def test_get_recipient_no_routes(self):
        with async_mock.patch.object(
            InMemoryStorage, "find_record", autospec=True
        ) as mock_search:
            mock_search.side_effect = StorageNotFoundError
            with self.assertRaises(RouteNotFoundError):
                await self.manager.get_recipient(TEST_ROUTE_VERKEY)

    async def test_get_routes_connection_id(self):
        record = await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        results = await self.manager.get_routes(
            client_connection_id=TEST_CONN_ID, tag_filter=None
        )
        assert len(results) == 1
        assert results[0].connection_id == TEST_CONN_ID
        assert results[0].recipient_key == TEST_ROUTE_VERKEY

    async def test_get_routes_connection_id_tag_filter_vacuous(self):
        record = await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        results = await self.manager.get_routes(
            client_connection_id=None, tag_filter={"for": "coverage"}
        )
        assert len(results) == 1
        assert results[0].connection_id == TEST_CONN_ID
        assert results[0].recipient_key == TEST_ROUTE_VERKEY

    async def test_get_routes_connection_id_tag_filter_str(self):
        record = await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        results = await self.manager.get_routes(
            client_connection_id=None, tag_filter={"recipient_key": TEST_ROUTE_VERKEY}
        )
        assert len(results) == 1
        assert results[0].connection_id == TEST_CONN_ID
        assert results[0].recipient_key == TEST_ROUTE_VERKEY

    async def test_get_routes_connection_id_tag_filter_list(self):
        record = await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        results = await self.manager.get_routes(
            client_connection_id=None, tag_filter={"recipient_key": [TEST_ROUTE_VERKEY]}
        )
        assert len(results) == 1
        assert results[0].connection_id == TEST_CONN_ID
        assert results[0].recipient_key == TEST_ROUTE_VERKEY

    async def test_get_routes_connection_id_tag_filter_list_miss(self):
        record = await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        results = await self.manager.get_routes(
            client_connection_id=None,
            tag_filter={"recipient_key": ["none", "of", "these"]},
        )
        assert len(results) == 0

    async def test_get_routes_connection_id_tag_filter_list_among_plural(self):
        record = await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        results = await self.manager.get_routes(
            client_connection_id=None,
            tag_filter={"recipient_key": ["none", TEST_ROUTE_VERKEY, "of", "these"]},
        )
        assert len(results) == 1
        assert results[0].connection_id == TEST_CONN_ID
        assert results[0].recipient_key == TEST_ROUTE_VERKEY

    async def test_get_routes_connection_id_tag_filter_x(self):
        record = await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        with self.assertRaises(RoutingManagerError):
            await self.manager.get_routes(
                client_connection_id=None, tag_filter={"recipient_key": None}
            )

    async def test_update_routes_delete(self):
        record = await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
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
        record = await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
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
        record = await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        results = await self.manager.update_routes(
            client_connection_id=TEST_CONN_ID,
            updates=[RouteUpdate(recipient_key=None, action=RouteUpdate.ACTION_DELETE)],
        )
        assert len(results) == 1
        assert results[0].recipient_key == None
        assert results[0].action == RouteUpdate.ACTION_DELETE
        assert results[0].result == RouteUpdated.RESULT_CLIENT_ERROR

    async def test_update_routes_unsupported_action(self):
        record = await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
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
        record = await self.manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
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
