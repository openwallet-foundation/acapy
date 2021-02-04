"""A simple event bus."""

from itertools import chain
import logging
from typing import Any, Callable, Dict, Pattern, Sequence
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
        return "<Event topic={}, payload={}>".format(self._topic, self._payload)


class EventBus:
    """A simple event bus implementation."""

    def __init__(self):
        self.topic_patterns_to_subscribers: Dict[Pattern, Sequence[Callable]] = {}

    async def notify(self, profile: Profile, event: Event):
        """Notify subscribers of event.

        Args:
            profile (Profile): profile of the event
            event (Event): event to emit

        """
        # TODO don't block notifier until subscribers have all been called?
        # TODO trigger each processor but don't await?
        # TODO log errors but otherwise ignore?

        LOGGER.debug("Notifying subscribers: %s", event)
        matched = [
            processor
            for pattern, processor in self.topic_patterns_to_subscribers.items()
            if pattern.match(event.topic)
        ]

        for processor in chain(*matched):
            try:
                await processor(profile, event)
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
