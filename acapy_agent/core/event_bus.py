"""A simple event bus."""

import asyncio
import logging
import os
import re
from contextlib import contextmanager
from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    Iterator,
    List,
    Match,
    NamedTuple,
    Optional,
    Pattern,
    Tuple,
)

from ..utils.task_queue import CompletedTask, TaskQueue

if TYPE_CHECKING:  # To avoid circular import error
    from .profile import Profile

LOGGER = logging.getLogger(__name__)

MAX_ACTIVE_EVENT_BUS_TASKS = int(os.getenv("MAX_ACTIVE_EVENT_BUS_TASKS", "50"))


class Event:
    """A simple event object."""

    def __init__(self, topic: str, payload: Optional[Any] = None):
        """Create a new event."""
        self._topic = topic
        self._payload = payload

    @property
    def topic(self) -> str:
        """Return this event's topic."""
        return self._topic

    @property
    def payload(self):
        """Return this event's payload."""
        return self._payload

    def __eq__(self, other):
        """Test equality."""
        if not isinstance(other, Event):
            return False
        return self._topic == other._topic and self._payload == other._payload

    def __repr__(self):
        """Return debug representation."""
        return "<Event topic={}, payload={}>".format(self._topic, self._payload)

    def with_metadata(self, metadata: "EventMetadata") -> "EventWithMetadata":
        """Annotate event with metadata and return EventWithMetadata object."""
        return EventWithMetadata(self.topic, self.payload, metadata)


class EventMetadata(NamedTuple):
    """Metadata passed alongside events to add context."""

    pattern: Pattern
    match: Match[str]


class EventWithMetadata(Event):
    """Event with metadata passed alongside events to add context."""

    def __init__(self, topic: str, payload: Any, metadata: EventMetadata):
        """Initialize event metadata."""
        super().__init__(topic, payload)
        self._metadata = metadata

    @property
    def metadata(self) -> EventMetadata:
        """Return metadata."""
        return self._metadata


class EventBus:
    """A simple event bus implementation."""

    def __init__(self):
        """Initialize Event Bus."""
        self.topic_patterns_to_subscribers: Dict[Pattern, List[Callable]] = {}

        # TaskQueue for non-blocking event processing
        self.task_queue = TaskQueue(max_active=MAX_ACTIVE_EVENT_BUS_TASKS)

    async def notify(self, profile: "Profile", event: Event):
        """Notify subscribers of event.

        Args:
            profile (Profile): context of the event
            event (Event): event to emit

        """
        # TODO: This method can now be made synchronous (would be breaking change)

        LOGGER.debug("Notifying subscribers for event: %s", event)
        # Define partial functions for each subscriber that matches the event topic
        partials = [
            partial(
                subscriber,
                profile,
                event.with_metadata(EventMetadata(pattern, match)),
            )
            for pattern, subscribers in self.topic_patterns_to_subscribers.items()
            if (match := pattern.match(event.topic))
            for subscriber in subscribers
        ]

        if not partials:
            LOGGER.debug("No subscribers for %s event", event.topic)
            return

        LOGGER.debug("Notifying %d subscribers for %s event", len(partials), event.topic)
        for processor in partials:
            LOGGER.debug("Putting %s event for processor %s", event.topic, processor)
            # Run each processor as a background task (fire and forget) with error handler
            self.task_queue.put(
                processor(),
                task_complete=self._make_error_handler(processor, event),
                ident=f"event_processor_{event.topic}",
            )

    def _make_error_handler(
        self, processor: partial[Any], event: Event
    ) -> Callable[[CompletedTask], None]:
        """Create an error handler that captures the processor and event context."""

        def error_handler(completed_task: CompletedTask):
            """Handle errors from event processor tasks."""
            if completed_task.exc_info:
                _, exc_val, _ = completed_task.exc_info
                # Don't log CancelledError as an error - it's normal task cancellation
                if not isinstance(exc_val, asyncio.CancelledError):
                    LOGGER.exception(
                        "Error occurred while processing %s for event: %s",
                        str(processor),
                        event,
                        exc_info=completed_task.exc_info,
                    )

        return error_handler

    def subscribe(self, pattern: Pattern | str, processor: Callable):
        """Subscribe to an event.

        Args:
            pattern (Pattern | str): compiled regular expression for matching topics,
                or the string to be compiled into a regular expression.
            processor (Callable): async callable accepting profile and event

        """
        if isinstance(pattern, str):
            pattern = re.compile(pattern)

        if pattern not in self.topic_patterns_to_subscribers:
            self.topic_patterns_to_subscribers[pattern] = []
        self.topic_patterns_to_subscribers[pattern].append(processor)
        LOGGER.debug("Subscribed: topic %s, processor %s", pattern, processor)

    def unsubscribe(self, pattern: Pattern, processor: Callable):
        """Unsubscribe from an event.

        This method is idempotent. Repeated calls to unsubscribe will not
        result in errors.

        Args:
            pattern (Pattern): regular expression used to subscribe the processor
            processor (Callable): processor to unsubscribe

        """
        if pattern in self.topic_patterns_to_subscribers:
            try:
                index = self.topic_patterns_to_subscribers[pattern].index(processor)
            except ValueError:
                return
            del self.topic_patterns_to_subscribers[pattern][index]
            if not self.topic_patterns_to_subscribers[pattern]:
                del self.topic_patterns_to_subscribers[pattern]
            LOGGER.debug("Unsubscribed: topic %s, processor %s", pattern, processor)

    @contextmanager
    def wait_for_event(
        self,
        waiting_profile: "Profile",
        pattern: Pattern,
        cond: Optional[Callable[[Event], bool]] = None,
    ) -> Iterator[Awaitable[Event]]:
        """Capture an event and retrieve its value."""
        future = asyncio.get_event_loop().create_future()

        async def _handle_single_event(profile, event):
            """Handle the single event."""
            LOGGER.debug(
                "wait_for_event event listener with event %s and profile %s",
                event,
                profile,
            )
            if cond is not None and not cond(event):
                return

            if waiting_profile == profile:
                future.set_result(event)
                self.unsubscribe(pattern, _handle_single_event)

        self.subscribe(pattern, _handle_single_event)

        yield future

        if not future.done():
            future.cancel()

    async def shutdown(self):
        """Shutdown the event bus and clean up background tasks."""
        active_before = self.task_queue.current_active
        pending_before = self.task_queue.current_pending
        LOGGER.debug(
            "Shutting down EventBus, cancelling %d active tasks and %d pending tasks",
            active_before,
            pending_before,
        )
        # Get references to active tasks before cancelling them
        tasks_to_cancel = [
            task for task in self.task_queue.active_tasks if not task.done()
        ]
        try:
            # Use TaskQueue's complete() to cancel tasks
            await self.task_queue.complete(timeout=2.0, cleanup=True)

            # Explicitly wait for the cancelled tasks to actually finish cancelling
            if tasks_to_cancel:
                # Wait for all the tasks we just cancelled to actually complete
                await asyncio.wait(tasks_to_cancel, timeout=2.0)
        except Exception as e:
            LOGGER.debug("Exception while waiting for task cancellation: %s", e)

        active_after = self.task_queue.current_active
        pending_after = self.task_queue.current_pending
        LOGGER.debug(
            "EventBus shutdown complete. Tasks: %d active (%d->%d), %d pending (%d->%d)",
            active_after,
            active_before,
            active_after,
            pending_after,
            pending_before,
            pending_after,
        )


class MockEventBus(EventBus):
    """A mock EventBus for testing."""

    def __init__(self):
        """Initialize MockEventBus."""
        super().__init__()
        self.events: List[Tuple[Profile, Event]] = []

    async def notify(self, profile: "Profile", event: Event):
        """Append the event to MockEventBus.events."""
        self.events.append((profile, event))
        await super().notify(profile, event)

    async def shutdown(self):
        """Mock shutdown method for testing."""
        # For MockEventBus, we still want to clean up the TaskQueue
        await super().shutdown()
