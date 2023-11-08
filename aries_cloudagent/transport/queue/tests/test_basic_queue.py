import asyncio

from aries_cloudagent.tests import mock
from unittest import IsolatedAsyncioTestCase

from .. import basic as test_module
from ..basic import BasicMessageQueue


async def collect(queue, count=1):
    found = []
    async for result in queue:
        found.append(result)
        if len(found) >= count:
            queue.stop()
    return found


class TestBasicQueue(IsolatedAsyncioTestCase):
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

        with mock.patch.object(
            test_module.asyncio, "get_event_loop", mock.MagicMock()
        ) as mock_get_event_loop, mock.patch.object(
            test_module.asyncio, "wait", mock.CoroutineMock()
        ) as mock_wait, mock.patch.object(
            queue, "stop_event"
        ) as mock_stop_event, mock.patch.object(
            queue, "queue"
        ):
            mock_stop_event.is_set.return_value = False
            mock_wait.return_value = (
                mock.MagicMock(),
                [mock.MagicMock(done=mock.MagicMock(), cancel=mock.MagicMock())],
            )
            mock_get_event_loop.return_value = mock.MagicMock(
                create_task=mock.MagicMock(
                    side_effect=[
                        mock.MagicMock(),  # stopped
                        mock.MagicMock(  # dequeued
                            done=mock.MagicMock(return_value=True),
                            exception=mock.MagicMock(return_value=KeyError()),
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

        with mock.patch.object(
            test_module.asyncio, "get_event_loop", mock.MagicMock()
        ) as mock_get_event_loop, mock.patch.object(
            test_module.asyncio, "wait", mock.CoroutineMock()
        ) as mock_wait, mock.patch.object(
            queue, "stop_event"
        ) as mock_stop_event, mock.patch.object(
            queue, "queue"
        ):
            mock_stop_event.is_set.return_value = False
            mock_wait.return_value = (
                mock.MagicMock(),
                [mock.MagicMock(done=mock.MagicMock(), cancel=mock.MagicMock())],
            )
            mock_get_event_loop.return_value = mock.MagicMock(
                create_task=mock.MagicMock(
                    side_effect=[
                        mock.MagicMock(  # stopped
                            done=mock.MagicMock(return_value=True)
                        ),
                        mock.MagicMock(  # dequeued
                            done=mock.MagicMock(return_value=False)
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
