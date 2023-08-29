"""Test Event Bus."""

import pytest
import re

from asynctest import mock as async_mock

from .. import event_bus as test_module
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


class MockProcessor:
    def __init__(self):
        self.profile = None
        self.event = None

    async def __call__(self, profile, event):
        self.profile = profile
        self.event = event


@pytest.fixture
def processor():
    yield MockProcessor()


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


def test_unsub_unsubbed_processor(event_bus: EventBus, processor):
    """Test unsubscribing an unsubscribed processor does not error."""
    event_bus.unsubscribe(re.compile(".*"), processor)
    event_bus.subscribe(re.compile(".*"), processor)
    another_processor = MockProcessor()
    event_bus.unsubscribe(re.compile(".*"), another_processor)


@pytest.mark.asyncio
async def test_sub_notify(event_bus: EventBus, profile, event, processor):
    """Test subscriber receives event."""
    event_bus.subscribe(re.compile(".*"), processor)
    await event_bus.notify(profile, event)
    assert processor.profile == profile
    assert processor.event == event


@pytest.mark.asyncio
async def test_sub_notify_error_logged_and_exec_continues(
    event_bus: EventBus,
    profile,
    event,
):
    """Test subscriber errors are logged but do not halt execution."""

    def _raise_exception(profile, event):
        raise Exception()

    processor = MockProcessor()
    bad_processor = _raise_exception
    event_bus.subscribe(re.compile(".*"), bad_processor)
    event_bus.subscribe(re.compile(".*"), processor)
    with async_mock.patch.object(
        test_module.LOGGER, "exception", async_mock.MagicMock()
    ) as mock_log_exc:
        await event_bus.notify(profile, event)

    assert mock_log_exc.called_once_with("Error occurred while processing event")
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
    processor1 = MockProcessor()
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
    processor1 = MockProcessor()
    event_bus.subscribe(re.compile(".*"), processor)
    event_bus.subscribe(re.compile("anything"), processor1)
    await event_bus.notify(profile, event)
    assert processor.profile == profile
    assert processor.event == event
    assert processor1.profile == profile
    assert processor1.event == event


@pytest.mark.asyncio
async def test_wait_for_event_multiple_do_not_collide(event_bus: EventBus, profile):
    """Test multiple wait_for_event calls don't collide."""
    pattern = re.compile(".*")
    with event_bus.wait_for_event(profile, pattern) as event1:
        with event_bus.wait_for_event(profile, pattern) as event2:
            assert len(event_bus.topic_patterns_to_subscribers) == 1
            assert len(event_bus.topic_patterns_to_subscribers[pattern]) == 2
            event_bus.unsubscribe(
                pattern, event_bus.topic_patterns_to_subscribers[pattern][0]
            )
            assert len(event_bus.topic_patterns_to_subscribers[pattern]) == 1


@pytest.mark.asyncio
async def test_wait_for_event(event_bus: EventBus, profile, event):
    with event_bus.wait_for_event(profile, re.compile(".*")) as returned_event:
        await event_bus.notify(profile, event)
        assert await returned_event == event


@pytest.mark.asyncio
async def test_wait_for_event_condition(event_bus: EventBus, profile, event):
    with event_bus.wait_for_event(
        profile, re.compile(".*"), lambda e: e.payload == "asdf"
    ) as returned_event:
        # This shouldn't trigger our condition because payload == "payload"
        await event_bus.notify(profile, event)
        assert not returned_event.done()

        # This should trigger
        event = Event("asdF", "asdf")
        await event_bus.notify(profile, event)
        assert returned_event.done()
        assert await returned_event == event
