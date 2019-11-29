import asyncio
from asynctest import TestCase

from ..task_queue import CompletedTask, TaskQueue


async def retval(val):
    return val


class TestTaskQueue(TestCase):
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

        fut = queue.put(retval(1), done)
        assert not queue.pending_tasks
        await queue.flush()
        assert completed == [1]
        assert fut.result().result() == 1

        with self.assertRaises(ValueError):
            queue.add_pending(None, done)

    async def test_put_limited(self):
        queue = TaskQueue(1)
        assert queue.max_active == 1
        assert not queue.cancelled
        completed = set()

        def done(complete: CompletedTask):
            assert not complete.exc_info
            completed.add(complete.task.result())

        fut1 = queue.put(retval(1), done)
        fut2 = queue.put(retval(2), done)
        assert queue.pending_tasks
        await queue.flush()
        assert completed == {1, 2}
        assert fut1.result().result() == 1
        assert fut2.result().result() == 2

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

    async def test_cancel_pending(self):
        queue = TaskQueue(1)
        completed = set()

        def done(complete: CompletedTask):
            assert not complete.exc_info
            completed.add(complete.task.result())

        queue.run(retval(1), done)
        queue.put(retval(2), done)
        queue.put(retval(3), done)
        queue.cancel_pending()
        await queue.flush()
        assert completed == {1}

    async def test_cancel_all(self):
        queue = TaskQueue(1)
        completed = set()

        def done(complete: CompletedTask):
            assert not complete.exc_info
            completed.add(complete.task.result())

        queue.run(retval(1), done)
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
        fut = queue.put(co)
        assert fut.cancelled()

    async def test_cancel_long(self):
        queue = TaskQueue()
        task = queue.run(asyncio.sleep(5))
        queue.cancel()
        await queue

        # cancellation may take a second
        # assert task.cancelled()

        with self.assertRaises(asyncio.CancelledError):
            await task

    async def test_complete_with_timeout(self):
        queue = TaskQueue()
        task = queue.run(asyncio.sleep(5))
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
        queue.completed_task(task, done)
        assert completed == [1, 1]
