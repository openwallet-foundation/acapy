import pytest

from indy_catalyst_agent.messaging.request_context import RequestContext
from indy_catalyst_agent.messaging.routing.manager import (
    RoutingManager,
    RoutingManagerError,
)
from indy_catalyst_agent.storage.basic import BasicStorage

TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_ROUTE_VERKEY = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"


@pytest.fixture()
def request_context() -> RequestContext:
    ctx = RequestContext()
    ctx.sender_verkey = TEST_VERKEY
    ctx.storage = BasicStorage()
    yield ctx


@pytest.fixture()
def manager() -> RoutingManager:
    return RoutingManager(next(request_context()))


class TestBasicStorage:
    @pytest.mark.asyncio
    async def test_require_sender(self):
        with pytest.raises(RoutingManagerError):
            RoutingManager(None)
        with pytest.raises(RoutingManagerError):
            RoutingManager(RequestContext())

    @pytest.mark.asyncio
    async def test_retrieve_none(self, manager):
        results = await manager.get_routes()
        assert results == []

    @pytest.mark.asyncio
    async def test_create_retrieve(self, manager):
        await manager.create_routes([TEST_ROUTE_VERKEY])
        results = await manager.get_routes()
        assert results == [TEST_ROUTE_VERKEY]

        recip = await manager.get_recipient(TEST_ROUTE_VERKEY)
        assert recip == TEST_VERKEY

    @pytest.mark.asyncio
    async def test_create_delete(self, manager):
        await manager.create_routes([TEST_ROUTE_VERKEY])
        await manager.delete_routes([TEST_ROUTE_VERKEY])
        results = await manager.get_routes()
        assert results == []

    @pytest.mark.asyncio
    async def test_no_recipient(self, manager):
        with pytest.raises(RoutingManagerError):
            await manager.get_recipient(TEST_ROUTE_VERKEY)
