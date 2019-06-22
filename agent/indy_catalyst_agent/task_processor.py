"""Classes for managing a limited set of concurrent tasks."""

import asyncio
import logging
from typing import Coroutine

LOGGER = logging.getLogger(__name__)


class PendingTask:
    """Class for tracking pending tasks."""

    def __init__(
        self, args, ident, future: asyncio.Future, retries: int, retry_wait: float
    ):
        """Initialize the pending task instance."""
        self.args = args
        self.ident = ident
        self.future = future
        self.retries = retries
        self.retry_wait = retry_wait


class TaskProcessor:
    """Class for managing a limited set of concurrent tasks."""

    def __init__(
        self,
        perform: Coroutine,
        *,
        default_retries: int = 0,
        default_retry_wait: float = 10.0,
        max_pending: int = 10,
    ):
        """Instantiate the dispatcher."""
        self.default_retries = default_retries
        self.default_retry_wait = default_retry_wait
        self._perform = perform
        self.max_pending = max_pending
        self.pending = set()
        self.pending_lock = asyncio.Lock()
        self.ready_event = asyncio.Event()
        self.ready_event.set()

    def ready(self):
        """Check if the dispatcher is ready."""
        return self.ready_event.is_set()

    async def wait(self):
        """Wait for the dispatcher to be ready for more messages."""
        await self.ready_event.wait()

    async def _perform_task(self, args, delay: float = None):
        """Perform the task."""
        if delay:
            await asyncio.sleep(delay)
        await self._perform(*args)

    async def _finish_task(self, task: PendingTask):
        """Complete a task."""
        async with self.pending_lock:
            if task in self.pending:
                if task.future.exception():
                    if task.retries > 0:
                        task.retries -= 1
                        task.future = asyncio.ensure_future(
                            self._perform_task(task.args, task.retry_wait)
                        )
                        task.future.add_done_callback(
                            lambda fut: asyncio.ensure_future(self._finish_task(task))
                        )
                    else:
                        # TODO: add failure callback
                        LOGGER.warning("Task processing failed: %s", task.ident)
                else:
                    self.pending.remove(task)
                    if len(self.pending) < self.max_pending:
                        self.ready_event.set()
            else:
                LOGGER.warning("Task not found in pending list: %s", task)

    async def run(
        self,
        *args,
        ident=None,
        retries: int = None,
        retry_wait: float = None,
        when_ready: bool = True,
    ):
        """Process a task and track the result."""
        if when_ready:
            await self.wait()
        future = asyncio.ensure_future(self._perform_task(args))
        if retries is None:
            retries = self.default_retries
        if retry_wait is None:
            retry_wait = self.default_retry_wait
        task = PendingTask(args, ident, future, retries, retry_wait)
        async with self.pending_lock:
            self.pending.add(task)
            if len(self.pending) >= self.max_pending:
                self.ready_event.clear()
        future.add_done_callback(
            lambda fut: asyncio.ensure_future(self._finish_task(task))
        )
