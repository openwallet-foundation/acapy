import asyncio

from asynctest import mock as async_mock, TestCase as AsyncTestCase

from .. import basic as test_module
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

        queue.task_done()
        await queue.join()

    async def test_dequeue_x(self):
        queue = BasicMessageQueue()
        test_value = "test value"
        await queue.enqueue(test_value)

        with async_mock.patch.object(
            test_module.asyncio, "get_event_loop", async_mock.MagicMock()
        ) as mock_get_event_loop, async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait:
            mock_wait.return_value = (
                async_mock.MagicMock(),
                [
                    async_mock.MagicMock(
                        done=async_mock.MagicMock(), cancel=async_mock.MagicMock()
                    )
                ],
            )
            mock_get_event_loop.return_value = async_mock.MagicMock(
                create_task=async_mock.MagicMock(
                    side_effect=[
                        async_mock.MagicMock(),  # stopped
                        async_mock.MagicMock(  # dequeued
                            done=async_mock.MagicMock(return_value=True),
                            exception=async_mock.MagicMock(return_value=KeyError()),
                        ),
                    ]
                )
            )
            with self.assertRaises(KeyError):
                await queue.dequeue(timeout=0)

    async def test_dequeue_none(self):
        queue = BasicMessageQueue()
        test_value = "test value"
        await queue.enqueue(test_value)

        with async_mock.patch.object(
            test_module.asyncio, "get_event_loop", async_mock.MagicMock()
        ) as mock_get_event_loop, async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait:
            mock_wait.return_value = (
                async_mock.MagicMock(),
                [
                    async_mock.MagicMock(
                        done=async_mock.MagicMock(), cancel=async_mock.MagicMock()
                    )
                ],
            )
            mock_get_event_loop.return_value = async_mock.MagicMock(
                create_task=async_mock.MagicMock(
                    side_effect=[
                        async_mock.MagicMock(  # stopped
                            done=async_mock.MagicMock(return_value=True)
                        ),
                        async_mock.MagicMock(  # dequeued
                            done=async_mock.MagicMock(return_value=False)
                        ),
                    ]
                )
            )
            assert await queue.dequeue(timeout=0) is None

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
