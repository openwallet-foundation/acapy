from asyncio import sleep
import pytest

from ..basic import BasicCache


@pytest.fixture()
async def cache():
    cache = BasicCache()
    await cache.set("valid key", "value")
    return cache


class TestBasicCache:
    @pytest.mark.asyncio
    async def test_get_none(self, cache):
        item = await cache.get("doesn't exist")
        assert item is None

    @pytest.mark.asyncio
    async def test_get_valid(self, cache):
        item = await cache.get("valid key")
        assert item == "value"

    @pytest.mark.asyncio
    async def test_set_str(self, cache):
        item = await cache.set("key", "newval")
        assert cache._cache["key"] is not None
        assert cache._cache["key"]["value"] == "newval"

    @pytest.mark.asyncio
    async def test_set_dict(self, cache):
        item = await cache.set("key", {"dictkey": "dval"})
        assert cache._cache["key"] is not None
        assert cache._cache["key"]["value"] == {"dictkey": "dval"}

    @pytest.mark.asyncio
    async def test_set_expires(self, cache):
        item = await cache.set("key", {"dictkey": "dval"}, 0.05)
        assert cache._cache["key"] is not None
        assert cache._cache["key"]["value"] == {"dictkey": "dval"}

        await sleep(0.05)

        item = await cache.get("key")
        assert item is None

    @pytest.mark.asyncio
    async def test_flush(self, cache):
        await cache.flush()
        assert cache._cache == {}
