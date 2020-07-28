"""Classes for managing a set of asyncio tasks."""

import asyncio
import logging
import time
from typing import Callable, Coroutine, Tuple

LOGGER = logging.getLogger(__name__)


def coro_ident(coro: Coroutine):
    """Extract an identifier for a coroutine."""
    return coro and (hasattr(coro, "__qualname__") and coro.__qualname__ or repr(coro))


async def coro_timed(coro: Coroutine, timing: dict):
    """Capture timing for a coroutine."""
    timing["started"] = time.perf_counter()
    try:
        return await coro
    finally:
        timing["ended"] = time.perf_counter()


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

    def __init__(
        self,
        task: asyncio.Task,
        exc_info: Tuple,
        ident: str = None,
        timing: dict = None,
    ):
        """Initialize the completed task."""
        self.exc_info = exc_info
        self.ident = ident
        self.task = task
        self.timing = timing

    def __repr__(self) -> str:
        """Generate string representation for logging."""
        return f"<{self.__class__.__name__} ident={self.ident} timing={self.timing}>"


class PendingTask:
    """Represent a task in the queue."""

    def __init__(
        self,
        coro: Coroutine,
        complete_hook: Callable = None,
        ident: str = None,
        task_future: asyncio.Future = None,
        queued_time: float = None,
    ):
        """
        Initialize the pending task.

        Args:
            coro: The coroutine to be run
            complete_hook: A callback to run on completion
            ident: A string identifier for the task
            task_future: A future to be resolved to the asyncio Task
            queued_time: When the pending task was added to the queue
        """
        if not asyncio.iscoroutine(coro):
            raise ValueError(f"Expected coroutine, got {coro}")
        self._cancelled = False
        self.complete_hook = complete_hook
        self.coro = coro
        self.queued_time: float = queued_time
        self.unqueued_time: float = None
        self.ident = ident or coro_ident(coro)
        self.task_future = task_future or asyncio.get_event_loop().create_future()

    def cancel(self):
        """Cancel the pending task."""
        self.coro.close()
        if not self.task_future.done():
            self.task_future.cancel()
        self._cancelled = True

    @property
    def cancelled(self):
        """Accessor for the cancelled property."""
        return self._cancelled

    @property
    def task(self) -> asyncio.Task:
        """Accessor for the task."""
        return self.task_future.done() and self.task_future.result()

    @task.setter
    def task(self, task: asyncio.Task):
        """Setter for the task."""
        if self.task_future.cancelled():
            return
        elif self.task_future.done():
            raise ValueError("Cannot set pending task future, already done")
        self.task_future.set_result(task)

    def __await__(self):
        """Wait for the task to be queued."""
        return self.task_future.__await__()

    def __repr__(self) -> str:
        """Generate string representation for logging."""
        return f"<{self.__class__.__name__} ident={self.ident}>"


class TaskQueue:
    """A class for managing a set of asyncio tasks."""

    def __init__(
        self, max_active: int = 0, timed: bool = False, trace_fn: Callable = None
    ):
        """
        Initialize the task queue.

        Args:
            max_active: The maximum number of tasks to automatically run
            timed: A flag indicating that timing should be collected for tasks
            trace_fn: A callback for all completed tasks
        """
        self.loop = asyncio.get_event_loop()
        self.active_tasks = []
        self.pending_tasks = []
        self.timed = timed
        self.total_done = 0
        self.total_failed = 0
        self.total_started = 0
        self._trace_fn = trace_fn
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

    def __bool__(self) -> bool:
        """
        Support for the bool() builtin.

        Return:
            True - the task queue exists even if there are no tasks
        """
        return True

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
        # waiting for the drain event, to avoid yielding to other queue methods
        while True:
            self._drain_evt.clear()
            while self.pending_tasks and (
                not self._max_active or len(self.active_tasks) < self._max_active
            ):
                pending: PendingTask = self.pending_tasks.pop(0)
                if pending.queued_time:
                    pending.unqueued_time = time.perf_counter()
                    timing = {
                        "queued": pending.queued_time,
                        "unqueued": pending.unqueued_time,
                    }
                else:
                    timing = None
                task = self.run(
                    pending.coro, pending.complete_hook, pending.ident, timing
                )
                try:
                    pending.task = task
                except ValueError:
                    LOGGER.warning("Pending task future already fulfilled")
            if self.pending_tasks:
                await self._drain_evt.wait()
            else:
                break

    def add_pending(self, pending: PendingTask):
        """
        Add a task to the pending queue.

        Args:
            pending: The `PendingTask` to add to the task queue
        """
        if self.timed and not pending.queued_time:
            pending.queued_time = time.perf_counter()
        self.pending_tasks.append(pending)
        self.drain()

    def add_active(
        self,
        task: asyncio.Task,
        task_complete: Callable = None,
        ident: str = None,
        timing: dict = None,
    ) -> asyncio.Task:
        """
        Register an active async task with an optional completion callback.

        Args:
            task: The asyncio task instance
            task_complete: An optional callback to run on completion
            ident: A string identifer for the task
            timing: An optional dictionary of timing information
        """
        self.active_tasks.append(task)
        task.add_done_callback(
            lambda fut: self.completed_task(task, task_complete, ident, timing)
        )
        self.total_started += 1
        return task

    def run(
        self,
        coro: Coroutine,
        task_complete: Callable = None,
        ident: str = None,
        timing: dict = None,
    ) -> asyncio.Task:
        """
        Start executing a coroutine as an async task, bypassing the pending queue.

        Args:
            coro: The coroutine to run
            task_complete: An optional callback to run on completion
            ident: A string identifier for the task
            timing: An optional dictionary of timing information

        Returns: the new asyncio task instance

        """
        if self._cancelled:
            raise RuntimeError("Task queue has been cancelled")
        if not asyncio.iscoroutine(coro):
            raise ValueError(f"Expected coroutine, got {coro}")
        if not ident:
            ident = coro_ident(coro)
        if self.timed:
            if not timing:
                timing = dict()
            coro = coro_timed(coro, timing)
        task = self.loop.create_task(coro)
        return self.add_active(task, task_complete, ident, timing)

    def put(
        self, coro: Coroutine, task_complete: Callable = None, ident: str = None
    ) -> PendingTask:
        """
        Add a new task to the queue, delaying execution if busy.

        Args:
            coro: The coroutine to run
            task_complete: A callback to run on completion
            ident: A string identifier for the task

        Returns: a future resolving to the asyncio task instance once queued

        """
        pending = PendingTask(coro, task_complete, ident)
        if self._cancelled:
            pending.cancel()
        elif self.ready:
            pending.task = self.run(coro, task_complete, pending.ident)
        else:
            self.add_pending(pending)
        return pending

    def completed_task(
        self,
        task: asyncio.Task,
        task_complete: Callable,
        ident: str,
        timing: dict = None,
    ):
        """Clean up after a task has completed and run callbacks."""
        exc_info = task_exc_info(task)
        if exc_info:
            self.total_failed += 1
            if not task_complete and not self._trace_fn:
                LOGGER.exception(
                    "Error running task %s", ident or "", exc_info=exc_info
                )
        else:
            self.total_done += 1
        if task_complete or self._trace_fn:
            completed = CompletedTask(task, exc_info, ident, timing)
            try:
                if task_complete:
                    task_complete(completed)
                if self._trace_fn:
                    self._trace_fn(completed)
            except Exception:
                LOGGER.exception("Error finalizing task %s", completed)
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
        for pending in self.pending_tasks:
            pending.cancel()
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
