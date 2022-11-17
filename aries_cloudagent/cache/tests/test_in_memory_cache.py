import pytest

from asyncio import ensure_future, sleep, wait_for

from ..base import CacheError
from ..in_memory import InMemoryCache


@pytest.fixture()
async def cache():
    cache = InMemoryCache()
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
    async def test_set_multi(self, cache):
        item = await cache.set([f"key{i}" for i in range(4)], {"dictkey": "dval"})
        for key in [f"key{i}" for i in range(4)]:
            assert cache._cache[key] is not None
            assert cache._cache[key]["value"] == {"dictkey": "dval"}

    @pytest.mark.asyncio
    async def test_set_expires(self, cache):
        item = await cache.set("key", {"dictkey": "dval"}, 0.05)
        assert cache._cache["key"] is not None
        assert cache._cache["key"]["value"] == {"dictkey": "dval"}

        await sleep(0.05)

        item = await cache.get("key")
        assert item is None

    @pytest.mark.asyncio
    async def test_set_expires_multi(self, cache):
        item = await cache.set([f"key{i}" for i in range(4)], {"dictkey": "dval"}, 0.05)
        for key in [f"key{i}" for i in range(4)]:
            assert cache._cache[key] is not None
            assert cache._cache[key]["value"] == {"dictkey": "dval"}

        await sleep(0.05)

        for key in [f"key{i}" for i in range(4)]:
            item = await cache.get(key)
            assert item is None

    @pytest.mark.asyncio
    async def test_flush(self, cache):
        await cache.flush()
        assert cache._cache == {}

    @pytest.mark.asyncio
    async def test_clear(self, cache):
        await cache.set("key", "value")
        await cache.clear("key")
        item = await cache.get("key")
        assert item is None

    @pytest.mark.asyncio
    async def test_acquire_release(self, cache):
        test_key = "test_key"
        lock = cache.acquire(test_key)
        await lock.__aenter__()
        assert test_key in cache._key_locks
        await lock.__aexit__(None, None, None)
        assert test_key not in cache._key_locks
        assert await cache.get(test_key) is None

    @pytest.mark.asyncio
    async def test_acquire_with_future(self, cache):
        test_key = "test_key"
        test_result = "test_result"
        lock = cache.acquire(test_key)
        await lock.__aenter__()
        await lock.set_result(test_result)
        await lock.__aexit__(None, None, None)
        assert await wait_for(lock, 1) == test_result
        assert lock.done
        assert lock.result == test_result
        assert lock.future.result() == test_result

    @pytest.mark.asyncio
    async def test_acquire_release_with_waiter(self, cache):
        test_key = "test_key"
        test_result = "test_result"
        lock = cache.acquire(test_key)
        await lock.__aenter__()

        lock2 = cache.acquire(test_key)
        assert lock.parent is None
        assert lock2.parent is lock
        await lock.set_result(test_result)
        await lock.__aexit__(None, None, None)

        assert await cache.get(test_key) == test_result
        assert await wait_for(lock, 1) == test_result
        assert await wait_for(lock2, 1) == test_result

    @pytest.mark.asyncio
    async def test_duplicate_set(self, cache):
        test_key = "test_key"
        test_result = "test_result"
        lock = cache.acquire(test_key)
        async with lock:
            assert not lock.done
            await lock.set_result(test_result)
            with pytest.raises(CacheError):
                await lock.set_result(test_result)
        assert lock.done
        assert test_key not in cache._key_locks

    @pytest.mark.asyncio
    async def test_populated(self, cache):
        test_key = "test_key"
        test_result = "test_result"
        await cache.set(test_key, test_result)
        lock = cache.acquire(test_key)
        lock2 = cache.acquire(test_key)

        async def check():
            async with lock as entry:
                async with lock2 as entry2:
                    assert entry2.done  # parent value located
                    assert entry2.result == test_result
                assert entry.done
                assert entry.result == test_result
            assert test_key not in cache._key_locks

        await wait_for(check(), 1)

    @pytest.mark.asyncio
    async def test_acquire_exception(self, cache):
        test_key = "test_key"
        test_result = "test_result"
        lock = cache.acquire(test_key)
        with pytest.raises(ValueError):
            async with lock:
                raise ValueError
        assert isinstance(lock.exception, ValueError)
        assert lock.done
        assert lock.result is None

    @pytest.mark.asyncio
    async def test_repr(self, cache):
        assert isinstance(repr(cache), str)
