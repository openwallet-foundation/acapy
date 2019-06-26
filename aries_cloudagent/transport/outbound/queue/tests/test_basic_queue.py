import asyncio

from asynctest import TestCase as AsyncTestCase

from ..basic import BasicOutboundMessageQueue


async def collect(queue, count=1):
    found = []
    async for result in queue:
        found.append(result)
        if len(found) >= count:
            queue.stop()
    return found


class TestBasicQueue(AsyncTestCase):
    async def test_enqueue_dequeue(self):
        queue = BasicOutboundMessageQueue()

        assert await queue.dequeue(timeout=0) is None

        test_value = "test value"
        await queue.enqueue(test_value)
        assert await queue.dequeue(timeout=0) == test_value
        assert await queue.dequeue(timeout=0) is None

    async def test_async_iter(self):
        queue = BasicOutboundMessageQueue()

        results = asyncio.wait_for(collect(queue), timeout=1.0)
        test_value = "test value"
        await queue.enqueue(test_value)
        found = await results
        assert found == [test_value]

    async def test_stopped(self):
        queue = BasicOutboundMessageQueue()
        queue.stop()

        results = asyncio.wait_for(collect(queue), timeout=1.0)
        if await results:
            self.fail("queue should be empty")

        test_value = "test value"
        await queue.enqueue(test_value)
        results = asyncio.wait_for(collect(queue), timeout=1.0)
        if await results:
            self.fail("queue should be empty")

        queue.reset()
        results = asyncio.wait_for(collect(queue), timeout=1.0)
        await queue.enqueue(test_value)
        found = await results
        assert found == [test_value]
