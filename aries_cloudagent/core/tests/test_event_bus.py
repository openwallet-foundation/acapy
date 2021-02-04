"""Test Event Bus."""

import pytest
import re
from asynctest import mock as async_mock
from ..event_bus import EventBus, Event

# pylint: disable=redefined-outer-name


@pytest.fixture
def event_bus():
    yield EventBus()


@pytest.fixture
def profile():
    yield async_mock.MagicMock()


@pytest.fixture
def event():
    event = Event(topic="anything", payload="payload")
    yield event


class TestProcessor:
    def __init__(self):
        self.profile = None
        self.event = None

    async def __call__(self, profile, event):
        self.profile = profile
        self.event = event


@pytest.fixture
def processor():
    yield TestProcessor()


def test_event(event):
    assert event.topic == "anything"
    assert event.payload == "payload"
    other = Event("anything", "payload")
    another = Event("nothing", "payload")
    and_another = Event("anything")
    assert event == other
    assert event != another
    assert event != and_another
    assert event != "random string"
    assert repr(event)


def test_sub_unsub(event_bus: EventBus, processor):
    """Test subscribe and unsubscribe."""
    event_bus.subscribe(re.compile(".*"), processor)
    assert event_bus.topic_patterns_to_subscribers
    assert event_bus.topic_patterns_to_subscribers[re.compile(".*")] == [processor]
    event_bus.unsubscribe(re.compile(".*"), processor)
    assert not event_bus.topic_patterns_to_subscribers


def test_unsub_idempotency(event_bus: EventBus, processor):
    """Test unsubscribe idempotency."""
    event_bus.subscribe(re.compile(".*"), processor)
    event_bus.unsubscribe(re.compile(".*"), processor)
    assert not event_bus.topic_patterns_to_subscribers
    event_bus.unsubscribe(re.compile(".*"), processor)
    assert not event_bus.topic_patterns_to_subscribers


@pytest.mark.asyncio
async def test_sub_notify(event_bus: EventBus, profile, event, processor):
    """Test subscriber receives event."""
    event_bus.subscribe(re.compile(".*"), processor)
    await event_bus.notify(profile, event)
    assert processor.profile == profile
    assert processor.event == event


@pytest.mark.parametrize(
    "pattern, topic",
    [
        ("test", "test"),
        (".*", "test"),
        ("topic::with::namespace", "topic::with::namespace::like::pieces"),
    ],
)
@pytest.mark.asyncio
async def test_sub_notify_regex_filtering(
    event_bus: EventBus, profile, processor, pattern, topic
):
    """Test events are filtered correctly."""
    event = Event(topic)
    event_bus.subscribe(re.compile(pattern), processor)
    await event_bus.notify(profile, event)
    assert processor.profile == profile
    assert processor.event == event


@pytest.mark.asyncio
async def test_sub_notify_no_match(event_bus: EventBus, profile, event, processor):
    """Test event not given to processor when pattern doesn't match."""
    event_bus.subscribe(re.compile("^$"), processor)
    await event_bus.notify(profile, event)
    assert processor.profile is None
    assert processor.event is None


@pytest.mark.asyncio
async def test_sub_notify_only_one(event_bus: EventBus, profile, event, processor):
    """Test only one subscriber is called when pattern matches only one."""
    processor1 = TestProcessor()
    event_bus.subscribe(re.compile(".*"), processor)
    event_bus.subscribe(re.compile("^$"), processor1)
    await event_bus.notify(profile, event)
    assert processor.profile == profile
    assert processor.event == event
    assert processor1.profile is None
    assert processor1.event is None


@pytest.mark.asyncio
async def test_sub_notify_both(event_bus: EventBus, profile, event, processor):
    """Test both subscribers are called when pattern matches both."""
    processor1 = TestProcessor()
    event_bus.subscribe(re.compile(".*"), processor)
    event_bus.subscribe(re.compile("anything"), processor1)
    await event_bus.notify(profile, event)
    assert processor.profile == profile
    assert processor.event == event
    assert processor1.profile == profile
    assert processor1.event == event
