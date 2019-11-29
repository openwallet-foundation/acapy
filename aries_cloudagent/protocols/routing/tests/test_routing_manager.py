import pytest

from aries_cloudagent.messaging.request_context import RequestContext
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.storage.basic import BasicStorage
from aries_cloudagent.transport.inbound.receipt import MessageReceipt

from ..manager import RoutingManager, RoutingManagerError
from ..models.route_record import RouteRecord

TEST_CONN_ID = "conn-id"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_ROUTE_VERKEY = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"


@pytest.fixture()
def request_context() -> RequestContext:
    ctx = RequestContext()
    ctx.message_receipt = MessageReceipt(sender_verkey=TEST_VERKEY)
    ctx.injector.bind_instance(BaseStorage, BasicStorage())
    yield ctx


@pytest.fixture()
def manager() -> RoutingManager:
    ctx = RequestContext()
    ctx.message_receipt = MessageReceipt(sender_verkey=TEST_VERKEY)
    ctx.injector.bind_instance(BaseStorage, BasicStorage())
    return RoutingManager(ctx)


class TestRoutingManager:
    @pytest.mark.asyncio
    async def test_retrieve_none(self, manager):
        results = await manager.get_routes()
        assert results == []

    @pytest.mark.asyncio
    async def test_create_retrieve(self, manager):
        await manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        record = await manager.get_recipient(TEST_ROUTE_VERKEY)
        assert isinstance(record, RouteRecord)
        assert record.connection_id == TEST_CONN_ID
        assert record.recipient_key == TEST_ROUTE_VERKEY

        results = await manager.get_routes()
        assert len(results) == 1
        assert results[0].connection_id == TEST_CONN_ID
        assert results[0].recipient_key == TEST_ROUTE_VERKEY

    @pytest.mark.asyncio
    async def test_create_delete(self, manager):
        record = await manager.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        await manager.delete_route_record(record)
        results = await manager.get_routes()
        assert not results

    @pytest.mark.asyncio
    async def test_no_recipient(self, manager):
        with pytest.raises(RoutingManagerError):
            await manager.get_recipient(TEST_ROUTE_VERKEY)
