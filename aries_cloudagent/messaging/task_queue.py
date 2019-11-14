import asyncio
import logging
from typing import Callable, Coroutine

LOGGER = logging.getLogger(__name__)


class TaskQueue:
    def __init__(self, max_active: int = 0):
        self.loop = asyncio.get_event_loop()
        self.active_tasks = []
        self.pending_tasks = []
        self._cancelled = False
        self._max_active = max_active
        self._lock = asyncio.Lock()
        self._poll_task: asyncio.Task = None
        self._updated_evt = asyncio.Event()

    @staticmethod
    def exc_info(task: asyncio.Task):
        try:
            exc_val = task.exception()
        except asyncio.CancelledError:
            exc_val = asyncio.CancelledError("Task was cancelled")
        if exc_val:
            return type(exc_val), exc_val, task.get_stack()

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    @property
    def lock(self) -> asyncio.Lock:
        return self._lock

    @property
    def max_active(self) -> int:
        return self._max_active

    @property
    def ready(self) -> bool:
        return (
            not self._cancelled and not self.max_active or self.size < self.max_active
        )

    @property
    def active(self) -> int:
        return len(self.active_tasks)

    @property
    def pending(self) -> int:
        return len(self.pending_tasks)

    @property
    def size(self) -> int:
        return len(self.active_tasks) + len(self.pending_tasks)

    def __len__(self) -> int:
        return self.size

    def _start(self):
        if not self._poll_task and self.pending_tasks:
            self._poll_task = self.loop.create_task(self._poll())
            self._poll_task.add_done_callback(lambda task: self._poll_done())

    def _poll_done(self):
        self._poll_task = None

    async def _poll(self):
        while self.pending_tasks:
            self._updated_evt.clear()
            while self.pending_tasks and (
                not self.max_active or len(self.active_tasks) < self.max_active
            ):
                coro, task_complete, fut = self.pending_tasks.pop(0)
                task = self.run(coro, task_complete)
                if fut:
                    fut.set_result(task)
            await self._updated_evt.wait()

    def add_pending(
        self,
        coro: Coroutine,
        task_complete: Callable = None,
        fut: asyncio.Future = None,
    ):
        if not asyncio.iscoroutine(coro):
            raise ValueError(f"Expected coroutine, got {coro}")
        self.pending_tasks.append((coro, task_complete, fut))
        self._start()

    def add_active(
        self, task: asyncio.Task, task_complete: Callable = None
    ) -> asyncio.Task:
        self.active_tasks.append(task)
        task.add_done_callback(lambda fut: self.completed_task(task, task_complete))
        return task

    def run(self, coro: Coroutine, task_complete: Callable = None) -> asyncio.Task:
        if self._cancelled:
            raise RuntimeError("Task queue has been cancelled")
        if not asyncio.iscoroutine(coro):
            raise ValueError(f"Expected coroutine, got {coro}")
        task = self.loop.create_task(coro)
        return self.add_active(task, task_complete)

    def put(self, coro: Coroutine, task_complete: Callable = None) -> asyncio.Future:
        """Block until ready, then start a new task."""
        fut = self.loop.create_future()
        if self._cancelled:
            fut.cancel()
            return
        if self.ready:
            task = self.run(coro, task_complete)
            fut.set_result(task)
        else:
            self.add_pending(coro, task_complete, fut)
        return fut

    def completed_task(self, task: asyncio.Task, task_complete: Callable):
        """Wait for the dispatch to complete and perform final actions."""
        exc_info = self.exc_info(task)
        if exc_info and not task_complete:
            LOGGER.exception("Error running task", exc_info=exc_info)
        try:
            self.active_tasks.remove(task)
        except ValueError:
            pass
        if task_complete:
            try:
                task_complete(task, exc_info)
            except Exception:
                LOGGER.exception("Error finalizing task")
        self._updated_evt.set()

    def cancel_pending(self):
        if self._poll_task:
            self._poll_task.cancel()
        for coro, task_complete, fut in self.pending_tasks:
            coro.close()
            fut.cancel()
        self.pending_tasks = []

    def cancel(self):
        self._cancelled = True
        self.cancel_pending()
        for task in self.active_tasks:
            if not task.done():
                task.cancel()

    async def complete(self, timeout: float = None, cleanup: bool = True):
        self._cancelled = True
        self.cancel_pending()
        if timeout or timeout is None:
            try:
                await self.wait_for(timeout)
            except TimeoutError:
                pass
        for task in self.active_tasks:
            if not task.done():
                task.cancel()
        if cleanup:
            while self.active_tasks:
                await self._updated_evt.wait()

    async def flush(self):
        if self.pending_tasks and not self._poll_task:
            self._start()
        while self.active_tasks or self._poll_task:
            if self._poll_task:
                await self._poll_task
            if self.active_tasks:
                await asyncio.gather(*self.active_tasks)

    def __await__(self):
        yield from self.flush().__await__()

    async def wait_for(self, timeout: float):
        return await asyncio.wait_for(self.flush(), timeout)


async def pr(v):
    print(v)


async def test1():
    q = TaskQueue()
    await q.put(pr(1))
    q.run(pr(2))
    await q.put(pr(3))
    await q.flush()


async def test2():
    q = TaskQueue()
    f = asyncio.get_event_loop().create_future()
    q.add_pending(pr(1), None, f)
    await q


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(test2())
