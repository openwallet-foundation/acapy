import asyncio

from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ..task_queue import CompletedTask, PendingTask, TaskQueue, task_exc_info


async def retval(val, *, delay=0):
    if delay:
        await asyncio.sleep(delay)
    return val


class TestTaskQueue(AsyncTestCase):
    async def test_run(self):
        queue = TaskQueue()
        task = None
        completed = []

        def done(complete: CompletedTask):
            assert complete.task is task
            assert not complete.exc_info
            completed.append(complete.task.result())

        task = queue.run(retval(1), done)
        assert queue.current_active == 1
        assert len(queue) == queue.current_size == 1
        assert not queue.current_pending
        await queue.flush()
        assert completed == [1]
        assert task.result() == 1

        with self.assertRaises(ValueError):
            queue.run(None, done)

    async def test_put_no_limit(self):
        queue = TaskQueue()
        completed = []

        def done(complete: CompletedTask):
            assert not complete.exc_info
            completed.append(complete.task.result())

        pend = queue.put(retval(1), done)
        assert not queue.pending_tasks
        await queue.flush()
        assert completed == [1]
        assert pend.task.result() == 1

        with self.assertRaises(ValueError):
            queue.put(None, done)

    async def test_put_limited(self):
        queue = TaskQueue(1)
        assert queue.max_active == 1
        assert not queue.cancelled
        completed = set()

        def done(complete: CompletedTask):
            assert not complete.exc_info
            completed.add(complete.task.result())

        pend1 = queue.put(retval(1), done)
        pend2 = queue.put(retval(2), done)
        assert queue.pending_tasks
        await queue.flush()
        assert completed == {1, 2}
        assert pend1.task.result() == 1
        assert pend2.task.result() == 2

    async def test_pending(self):
        coro = retval(1, delay=1)
        pend = PendingTask(coro, None)
        assert str(pend).startswith("<PendingTask")
        task = asyncio.get_event_loop().create_task(coro)
        assert task_exc_info(task) is None
        pend.task = task
        assert pend.task is task
        assert pend.task_future.result() is task
        with self.assertRaises(ValueError):
            pend.task = task
        pend.cancel()
        assert pend.cancelled
        task.cancel()

        with async_mock.patch.object(pend, "task_future", autospec=True) as mock_future:
            mock_future.cancelled.return_value = True
            pend.task = "a suffusion of yellow"
            mock_future.set_result.assert_not_called()

    async def test_complete(self):
        queue = TaskQueue()
        completed = set()

        def done(complete: CompletedTask):
            assert not complete.exc_info
            completed.add(complete.task.result())

        queue.run(retval(1), done)
        await queue.put(retval(2), done)
        queue.put(retval(3), done)
        await queue.complete()
        assert completed == {1, 2, 3}

        async def noop():
            return

        with async_mock.patch.object(
            queue, "drain", async_mock.MagicMock()
        ) as mock_drain, async_mock.patch.object(
            queue, "wait_for", async_mock.CoroutineMock()
        ) as mock_wait_for:
            mock_drain.side_effect = [queue.loop.create_task(noop()), None]
            await queue.complete(cleanup=True)

    async def test_cancel_pending(self):
        queue = TaskQueue(1)
        completed = set()

        def done(complete: CompletedTask):
            assert not complete.exc_info
            completed.add(complete.task.result())

        queue.run(retval(1), done)
        sleep = queue.run(retval(1, delay=1), done)
        queue.put(retval(2), done)
        queue.put(retval(3), done)
        queue.cancel_pending()
        sleep.cancel()

        await queue.flush()
        assert completed == {1}

    async def test_drain_done(self):
        coro = retval(1, delay=1)
        pend = PendingTask(coro, None)
        queue = TaskQueue(1)
        queue.add_pending(pend)

        with async_mock.patch.object(
            queue.pending_tasks[0], "task_future", autospec=True
        ) as mock_future:
            mock_future.cancelled.return_value = False
            mock_future.done.return_value = True
            mock_future.set_result.assert_not_called()
            await queue._drain_loop()

    async def test_cancel_all(self):
        queue = TaskQueue(1)
        completed = set()

        def done(complete: CompletedTask):
            assert not complete.exc_info
            completed.add(complete.task.result())

        queue.run(retval(1, delay=1), done)
        queue.put(retval(2), done)
        queue.put(retval(3), done)
        queue.cancel()
        assert queue.cancelled
        await queue.flush()
        assert not completed
        assert not queue.current_size

        co = retval(1)
        with self.assertRaises(RuntimeError):
            queue.run(co, done)
        co.close()

        co = retval(1)
        pend = queue.put(co)
        assert pend.cancelled

    async def test_cancel_long(self):
        queue = TaskQueue()
        task = queue.run(retval(1, delay=5))
        queue.cancel()
        await queue

        # cancellation may take a second
        # assert task.cancelled()

        with self.assertRaises(asyncio.CancelledError):
            await task

    async def test_complete_with_timeout(self):
        queue = TaskQueue()
        task = queue.run(retval(1, delay=5))
        await queue.complete(0.01)

        # cancellation may take a second
        # assert task.cancelled()

        with self.assertRaises(asyncio.CancelledError):
            await task

    async def test_repeat_callback(self):
        # check that running the callback twice does not throw an exception

        queue = TaskQueue()
        completed = []

        def done(complete: CompletedTask):
            assert not complete.exc_info
            completed.append(complete.task.result())

        task = queue.run(retval(1), done)
        await task
        queue.completed_task(task, done, None, dict())
        assert completed == [1, 1]

    async def test_timed(self):
        completed = []

        def done(complete: CompletedTask):
            assert not complete.exc_info
            completed.append((complete.task.result(), complete.timing))

        queue = TaskQueue(max_active=1, timed=True, trace_fn=done)
        assert bool(queue)
        task1 = queue.run(retval(1))
        task2 = await queue.put(retval(2))
        assert bool(queue)
        await queue.complete(0.1)

        assert len(completed) == 2
        assert "queued" not in completed[0][1]
        assert "queued" in completed[1][1]
