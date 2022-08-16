"""A simple event bus."""

import asyncio
from contextlib import contextmanager
import logging
from typing import (
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
    TYPE_CHECKING,
    Tuple,
)
from functools import partial

if TYPE_CHECKING:  # To avoid circular import error
    from .profile import Profile

LOGGER = logging.getLogger(__name__)


class Event:
    """A simple event object."""

    def __init__(self, topic: str, payload: Any = None):
        """Create a new event."""
        self._topic = topic
        self._payload = payload

    @property
    def topic(self):
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

    async def notify(self, profile: "Profile", event: Event):
        """Notify subscribers of event.

        Args:
            profile (Profile): context of the event
            event (Event): event to emit

        """
        # TODO don't block notifier until subscribers have all been called?
        # TODO trigger each processor but don't await?
        # TODO log errors but otherwise ignore?

        LOGGER.debug("Notifying subscribers: %s", event)

        partials = []
        for pattern, subscribers in self.topic_patterns_to_subscribers.items():
            match = pattern.match(event.topic)

            if not match:
                continue

            for subscriber in subscribers:
                partials.append(
                    partial(
                        subscriber,
                        profile,
                        event.with_metadata(EventMetadata(pattern, match)),
                    )
                )

        for processor in partials:
            try:
                await processor()
            except Exception:
                LOGGER.exception("Error occurred while processing event")

    def subscribe(self, pattern: Pattern, processor: Callable):
        """Subscribe to an event.

        Args:
            pattern (Pattern): compiled regular expression for matching topics
            processor (Callable): async callable accepting profile and event

        """
        LOGGER.debug("Subscribed: topic %s, processor %s", pattern, processor)
        if pattern not in self.topic_patterns_to_subscribers:
            self.topic_patterns_to_subscribers[pattern] = []
        self.topic_patterns_to_subscribers[pattern].append(processor)

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


class MockEventBus(EventBus):
    """A mock EventBus for testing."""

    def __init__(self):
        """Initialize MockEventBus."""
        super().__init__()
        self.events: List[Tuple[Profile, Event]] = []

    async def notify(self, profile: "Profile", event: Event):
        """Append the event to MockEventBus.events."""
        self.events.append((profile, event))
