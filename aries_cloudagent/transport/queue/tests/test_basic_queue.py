import asyncio

from asynctest import TestCase as AsyncTestCase

from ..basic import BasicMessageQueue


async def collect(queue, count=1):
    found = []
    async for result in queue:
        found.append(result)
        if len(found) >= count:
            queue.stop()
    return found


class TestBasicQueue(AsyncTestCase):
    async def test_enqueue_dequeue(self):
        queue = BasicMessageQueue()

        with self.assertRaises(asyncio.TimeoutError):
            await queue.dequeue(timeout=0)

        test_value = "test value"
        await queue.enqueue(test_value)
        assert await queue.dequeue(timeout=0) == test_value
        with self.assertRaises(asyncio.TimeoutError):
            await queue.dequeue(timeout=0)

    async def test_async_iter(self):
        queue = BasicMessageQueue()

        results = asyncio.wait_for(collect(queue), timeout=1.0)
        test_value = "test value"
        await queue.enqueue(test_value)
        found = await results
        assert found == [test_value]

    async def test_stopped(self):
        queue = BasicMessageQueue()
        queue.stop()

        with self.assertRaises(asyncio.CancelledError):
            await queue.dequeue(timeout=0)

        test_value = "test value"
        with self.assertRaises(asyncio.CancelledError):
            await queue.enqueue(test_value)
        results = asyncio.wait_for(collect(queue), timeout=1.0)
        assert await results == []
        with self.assertRaises(asyncio.CancelledError):
            await queue.dequeue(timeout=0)

        queue.reset()
        results = asyncio.wait_for(collect(queue), timeout=1.0)
        await queue.enqueue(test_value)
        found = await results
        assert found == [test_value]
