"""Classes for managing a set of asyncio tasks."""

import asyncio
import logging
from typing import Callable, Coroutine, Tuple

LOGGER = logging.getLogger(__name__)


def task_exc_info(task: asyncio.Task):
    """Extract exception info from an asyncio task."""
    if not task or not task.done():
        return
    try:
        exc_val = task.exception()
    except asyncio.CancelledError:
        exc_val = asyncio.CancelledError("Task was cancelled")
    if exc_val:
        return type(exc_val), exc_val, exc_val.__traceback__


class CompletedTask:
    """Represent the result of a queued task."""

    # Note: this would be a good place to return timing information

    def __init__(self, task: asyncio.Task, exc_info: Tuple):
        """Initialize the completed task."""
        self.exc_info = exc_info
        self.task = task


class TaskQueue:
    """A class for managing a set of asyncio tasks."""

    def __init__(self, max_active: int = 0):
        """
        Initialize the task queue.

        Args:
            max_active: The maximum number of tasks to automatically run
        """
        self.loop = asyncio.get_event_loop()
        self.active_tasks = []
        self.pending_tasks = []
        self.total_done = 0
        self.total_failed = 0
        self._cancelled = False
        self._drain_evt = asyncio.Event()
        self._drain_task: asyncio.Task = None
        self._max_active = max_active

    @property
    def cancelled(self) -> bool:
        """Accessor for the cancelled property of the queue."""
        return self._cancelled

    @property
    def max_active(self) -> int:
        """Accessor for the maximum number of active tasks in the queue."""
        return self._max_active

    @property
    def ready(self) -> bool:
        """Accessor for the ready property of the queue."""
        return (
            not self._cancelled
            and not self._max_active
            or self.current_size < self._max_active
        )

    @property
    def current_active(self) -> int:
        """Accessor for the current number of active tasks in the queue."""
        return len(self.active_tasks)

    @property
    def current_pending(self) -> int:
        """Accessor for the current number of pending tasks in the queue."""
        return len(self.pending_tasks)

    @property
    def current_size(self) -> int:
        """Accessor for the total number of tasks in the queue."""
        return len(self.active_tasks) + len(self.pending_tasks)

    def __len__(self) -> int:
        """Support for the len() builtin."""
        return self.current_size

    def drain(self) -> asyncio.Task:
        """Start the process to run queued tasks."""
        if self._drain_task and not self._drain_task.done():
            self._drain_evt.set()
        elif self.pending_tasks:
            self._drain_task = self.loop.create_task(self._drain_loop())
            self._drain_task.add_done_callback(lambda task: self._drain_done(task))
        return self._drain_task

    def _drain_done(self, task: asyncio.Task):
        """Handle completion of the drain process."""
        exc_info = task_exc_info(task)
        if exc_info:
            LOGGER.exception("Error draining task queue:", exc_info=exc_info)
        if self._drain_task and self._drain_task.done():
            self._drain_task = None

    async def _drain_loop(self):
        """Run pending tasks while there is room in the queue."""
        # Note: this method should not call async methods apart from
        # waiting for the updated event, to avoid yielding to other queue methods
        while True:
            self._drain_evt.clear()
            while self.pending_tasks and (
                not self._max_active or len(self.active_tasks) < self._max_active
            ):
                coro, task_complete, fut = self.pending_tasks.pop(0)
                task = self.run(coro, task_complete)
                if fut and not fut.done():
                    fut.set_result(task)
            if self.pending_tasks:
                await self._drain_evt.wait()
            else:
                break

    def add_pending(
        self,
        coro: Coroutine,
        task_complete: Callable = None,
        fut: asyncio.Future = None,
    ):
        """
        Add a task to the pending queue.

        Args:
            coro: The coroutine to run
            task_complete: An optional callback when the task has completed
            fut: A future that resolves to the task once it is queued
        """
        if not asyncio.iscoroutine(coro):
            raise ValueError(f"Expected coroutine, got {coro}")
        self.pending_tasks.append((coro, task_complete, fut))
        self.drain()

    def add_active(
        self, task: asyncio.Task, task_complete: Callable = None
    ) -> asyncio.Task:
        """
        Register an active async task with an optional completion callback.

        Args:
            task: The asyncio task instance
            task_complete: An optional callback to run on completion
        """
        self.active_tasks.append(task)
        task.add_done_callback(lambda fut: self.completed_task(task, task_complete))
        return task

    def run(self, coro: Coroutine, task_complete: Callable = None) -> asyncio.Task:
        """
        Start executing a coroutine as an async task, bypassing the pending queue.

        Args:
            coro: The coroutine to run
            task_complete: A callback to run on completion

        Returns: the new asyncio task instance

        """
        if self._cancelled:
            raise RuntimeError("Task queue has been cancelled")
        if not asyncio.iscoroutine(coro):
            raise ValueError(f"Expected coroutine, got {coro}")
        task = self.loop.create_task(coro)
        return self.add_active(task, task_complete)

    def put(self, coro: Coroutine, task_complete: Callable = None) -> asyncio.Future:
        """
        Add a new task to the queue, delaying execution if busy.

        Args:
            coro: The coroutine to run
            task_complete: A callback to run on completion

        Returns: a future resolving to the asyncio task instance once queued

        """
        fut = self.loop.create_future()
        if self._cancelled:
            coro.close()
            fut.cancel()
        elif self.ready:
            task = self.run(coro, task_complete)
            fut.set_result(task)
        else:
            self.add_pending(coro, task_complete, fut)
        return fut

    def completed_task(self, task: asyncio.Task, task_complete: Callable):
        """Clean up after a task has completed and run callbacks."""
        exc_info = task_exc_info(task)
        if exc_info:
            self.total_failed += 1
            if not task_complete:
                LOGGER.exception("Error running task", exc_info=exc_info)
        else:
            self.total_done += 1
        if task_complete:
            try:
                task_complete(CompletedTask(task, exc_info))
            except Exception:
                LOGGER.exception("Error finalizing task")
        try:
            self.active_tasks.remove(task)
        except ValueError:
            pass
        self.drain()

    def cancel_pending(self):
        """Cancel any pending tasks in the queue."""
        if self._drain_task:
            self._drain_task.cancel()
            self._drain_task = None
        for coro, task_complete, fut in self.pending_tasks:
            coro.close()
            fut.cancel()
        self.pending_tasks = []

    def cancel(self):
        """Cancel any pending or active tasks in the queue."""
        self._cancelled = True
        self.cancel_pending()
        for task in self.active_tasks:
            if not task.done():
                task.cancel()

    async def complete(self, timeout: float = None, cleanup: bool = True):
        """Cancel any pending tasks and wait for, or cancel active tasks."""
        self._cancelled = True
        self.cancel_pending()
        if timeout or timeout is None:
            try:
                await self.wait_for(timeout)
            except asyncio.TimeoutError:
                pass
        for task in self.active_tasks:
            if not task.done():
                task.cancel()
        if cleanup:
            while True:
                drain = self.drain()
                if not drain:
                    break
                await drain

    async def flush(self):
        """Wait for any active or pending tasks to be completed."""
        self.drain()
        while self.active_tasks or self._drain_task:
            if self._drain_task:
                await self._drain_task
            if self.active_tasks:
                await asyncio.wait(self.active_tasks)

    def __await__(self):
        """Handle the builtin await operator."""
        yield from self.flush().__await__()

    async def wait_for(self, timeout: float):
        """Wait for all queued tasks to complete with a timeout."""
        return await asyncio.wait_for(self.flush(), timeout)
