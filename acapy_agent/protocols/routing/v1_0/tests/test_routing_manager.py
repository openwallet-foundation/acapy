from unittest import IsolatedAsyncioTestCase

from marshmallow import ValidationError

from .....messaging.request_context import RequestContext
from .....storage.error import StorageDuplicateError, StorageNotFoundError
from .....tests import mock
from .....transport.inbound.receipt import MessageReceipt
from .....utils.testing import create_test_profile
from ..manager import RouteNotFoundError, RoutingManager, RoutingManagerError
from ..models.route_record import RouteRecord, RouteRecordSchema

TEST_CONN_ID = "conn-id"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_ROUTE_VERKEY = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"


class TestRoutingManager(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.profile = await create_test_profile()
        self.context = RequestContext.test_context(self.profile)
        self.context.message_receipt = MessageReceipt(sender_verkey=TEST_VERKEY)
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
        with mock.patch.object(
            RouteRecord, "retrieve_by_recipient_key", mock.CoroutineMock()
        ) as mock_retrieve:
            mock_retrieve.side_effect = StorageDuplicateError()
            with self.assertRaises(RouteNotFoundError) as context:
                await self.manager.get_recipient(TEST_ROUTE_VERKEY)
        assert "More than one route" in str(context.exception)

    async def test_get_recipient_no_routes(self):
        with mock.patch.object(
            RouteRecord, "retrieve_by_recipient_key", mock.CoroutineMock()
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
