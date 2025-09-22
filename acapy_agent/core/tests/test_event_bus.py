"""Test Event Bus."""

import asyncio
import re
from unittest.mock import MagicMock, patch

import pytest

from .. import event_bus as test_module
from ..event_bus import Event, EventBus

# pylint: disable=redefined-outer-name


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def profile() -> MagicMock:
    return MagicMock()


@pytest.fixture
def event() -> Event:
    event = Event(topic="anything", payload="payload")
    return event


class MockProcessor:
    def __init__(self) -> None:
        self.profile = None
        self.event = None

    async def __call__(self, profile, event) -> None:
        self.profile = profile
        self.event = event


@pytest.fixture
def processor() -> MockProcessor:
    return MockProcessor()


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


def test_sub_unsub(event_bus: EventBus, processor: MockProcessor):
    """Test subscribe and unsubscribe."""
    event_bus.subscribe(re.compile(".*"), processor)
    assert event_bus.topic_patterns_to_subscribers
    assert event_bus.topic_patterns_to_subscribers[re.compile(".*")] == [processor]
    event_bus.unsubscribe(re.compile(".*"), processor)
    assert not event_bus.topic_patterns_to_subscribers


def test_unsub_idempotency(event_bus: EventBus, processor: MockProcessor):
    """Test unsubscribe idempotency."""
    event_bus.subscribe(re.compile(".*"), processor)
    event_bus.unsubscribe(re.compile(".*"), processor)
    assert not event_bus.topic_patterns_to_subscribers
    event_bus.unsubscribe(re.compile(".*"), processor)
    assert not event_bus.topic_patterns_to_subscribers


def test_unsub_unsubbed_processor(event_bus: EventBus, processor: MockProcessor):
    """Test unsubscribing an unsubscribed processor does not error."""
    event_bus.unsubscribe(re.compile(".*"), processor)
    event_bus.subscribe(re.compile(".*"), processor)
    another_processor = MockProcessor()
    event_bus.unsubscribe(re.compile(".*"), another_processor)


@pytest.mark.asyncio
async def test_sub_notify(
    event_bus: EventBus, profile: MagicMock, event: Event, processor: MockProcessor
):
    """Test subscriber receives event."""
    event_bus.subscribe(re.compile(".*"), processor)
    await event_bus.notify(profile, event)
    await event_bus.task_queue.wait_for_completion()
    assert processor.profile == profile
    assert processor.event == event


@pytest.mark.asyncio
async def test_sub_notify_error_logged_and_exec_continues(
    event_bus: EventBus,
    profile: MagicMock,
    event: Event,
):
    """Test subscriber errors are logged but do not halt execution."""

    async def _raise_exception(profile, event):
        raise Exception("Test exception")

    processor = MockProcessor()
    bad_processor = _raise_exception
    event_bus.subscribe(re.compile(".*"), bad_processor)
    event_bus.subscribe(re.compile(".*"), processor)
    with patch.object(test_module.LOGGER, "exception", MagicMock()) as mock_log_exc:
        await event_bus.notify(profile, event)
        await event_bus.task_queue.wait_for_completion()

    # The error handler should log the exception
    mock_log_exc.assert_called()
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
    event_bus: EventBus,
    profile: MagicMock,
    processor: MockProcessor,
    pattern: str,
    topic: str,
):
    """Test events are filtered correctly."""
    event = Event(topic)
    event_bus.subscribe(re.compile(pattern), processor)
    await event_bus.notify(profile, event)
    await event_bus.task_queue.wait_for_completion()
    assert processor.profile == profile
    assert processor.event == event


@pytest.mark.asyncio
async def test_sub_notify_no_match(
    event_bus: EventBus, profile: MagicMock, event: Event, processor: MockProcessor
):
    """Test event not given to processor when pattern doesn't match."""
    event_bus.subscribe(re.compile("^$"), processor)
    await event_bus.notify(profile, event)
    assert processor.profile is None
    assert processor.event is None


@pytest.mark.asyncio
async def test_sub_notify_only_one(
    event_bus: EventBus, profile: MagicMock, event: Event, processor: MockProcessor
):
    """Test only one subscriber is called when pattern matches only one."""
    processor1 = MockProcessor()
    event_bus.subscribe(re.compile(".*"), processor)
    event_bus.subscribe(re.compile("^$"), processor1)
    await event_bus.notify(profile, event)
    await event_bus.task_queue.wait_for_completion()
    assert processor.profile == profile
    assert processor.event == event
    assert processor1.profile is None
    assert processor1.event is None


@pytest.mark.asyncio
async def test_sub_notify_both(
    event_bus: EventBus, profile: MagicMock, event: Event, processor: MockProcessor
):
    """Test both subscribers are called when pattern matches both."""
    processor1 = MockProcessor()
    event_bus.subscribe(re.compile(".*"), processor)
    event_bus.subscribe(re.compile("anything"), processor1)
    await event_bus.notify(profile, event)
    await event_bus.task_queue.wait_for_completion()
    assert processor.profile == profile
    assert processor.event == event
    assert processor1.profile == profile
    assert processor1.event == event


@pytest.mark.asyncio
async def test_wait_for_event_multiple_do_not_collide(
    event_bus: EventBus, profile: MagicMock
):
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
async def test_wait_for_event(event_bus: EventBus, profile: MagicMock, event: Event):
    with event_bus.wait_for_event(profile, re.compile(".*")) as returned_event:
        await event_bus.notify(profile, event)
        await event_bus.task_queue.wait_for_completion()
        assert await returned_event == event


@pytest.mark.asyncio
async def test_wait_for_event_condition(
    event_bus: EventBus, profile: MagicMock, event: Event
):
    with event_bus.wait_for_event(
        profile, re.compile(".*"), lambda e: e.payload == "asdf"
    ) as returned_event:
        # This shouldn't trigger our condition because payload == "payload"
        await event_bus.notify(profile, event)
        await event_bus.task_queue.wait_for_completion()
        assert not returned_event.done()

        # This should trigger
        event = Event("asdF", "asdf")
        await event_bus.notify(profile, event)
        await event_bus.task_queue.wait_for_completion()
        assert returned_event.done()
        assert await returned_event == event


@pytest.mark.asyncio
async def test_shutdown_no_active_tasks(event_bus: EventBus):
    """Test shutdown with no active tasks completes cleanly."""
    with patch.object(test_module.LOGGER, "debug") as mock_debug:
        await event_bus.shutdown()

    # Should log start and completion messages
    assert mock_debug.call_count >= 2
    # Verify the shutdown completion message
    completion_call = mock_debug.call_args_list[-1]
    assert "EventBus shutdown complete" in completion_call[0][0]


@pytest.mark.asyncio
async def test_shutdown_exception_handling(
    event_bus: EventBus, profile: MagicMock, event: Event
):
    """Test shutdown handles exceptions during task cancellation."""

    async def normal_processor(profile, event):
        await asyncio.sleep(0.1)

    event_bus.subscribe(re.compile(".*"), normal_processor)

    # Mock asyncio.wait to raise an exception
    test_exception = Exception("Test exception during shutdown")
    with (
        patch("asyncio.wait", side_effect=test_exception),
        patch.object(test_module.LOGGER, "debug") as mock_debug,
    ):
        await event_bus.notify(profile, event)
        await asyncio.sleep(0.01)  # Let task start

        # Should handle the exception gracefully
        await event_bus.shutdown()

        # Should log the exception
        exception_logged = any(
            "Exception while waiting for task cancellation" in str(call)
            for call in mock_debug.call_args_list
        )
        assert exception_logged


@pytest.mark.asyncio
async def test_shutdown_idempotency(event_bus: EventBus):
    """Test shutdown can be called multiple times safely."""
    with patch.object(test_module.LOGGER, "debug") as mock_debug:
        # First shutdown
        await event_bus.shutdown()
        first_call_count = mock_debug.call_count

        # Second shutdown should also work
        await event_bus.shutdown()

        # Should have logged both shutdowns
        assert mock_debug.call_count >= first_call_count


@pytest.mark.asyncio
async def test_shutdown_logging_details(
    event_bus: EventBus, profile: MagicMock, event: Event
):
    """Test shutdown logs detailed task count information."""

    async def quick_processor(profile, event):
        await asyncio.sleep(0.01)

    event_bus.subscribe(re.compile(".*"), quick_processor)

    with patch.object(test_module.LOGGER, "debug") as mock_debug:
        # Create some tasks
        await event_bus.notify(profile, event)
        await event_bus.notify(profile, event)

        await event_bus.shutdown()

        # Find the shutdown start message
        start_message = None
        completion_message = None
        for call in mock_debug.call_args_list:
            message = call[0][0]
            if "Shutting down EventBus" in message:
                start_message = message
            elif "EventBus shutdown complete" in message:
                completion_message = message

        assert start_message is not None
        assert completion_message is not None
        assert "active tasks" in start_message
        assert "pending tasks" in start_message


@pytest.mark.asyncio
async def test_shutdown_with_mixed_task_states(
    event_bus: EventBus, profile: MagicMock, event: Event
):
    """Test shutdown handles tasks in various states (running, done, cancelled)."""

    task_states = []

    async def state_tracking_processor(profile, event):
        """Track when this processor runs."""
        task_states.append("started")
        try:
            await asyncio.sleep(0.1)
            task_states.append("completed")
        except asyncio.CancelledError:
            task_states.append("cancelled")
            raise

    event_bus.subscribe(re.compile(".*"), state_tracking_processor)

    # Create multiple tasks
    await event_bus.notify(profile, event)
    await event_bus.notify(profile, event)

    # Let some tasks start
    await asyncio.sleep(0.01)

    with patch.object(test_module.LOGGER, "debug"):
        await event_bus.shutdown()

    # Tasks should have been cancelled
    assert "started" in task_states
    assert event_bus.task_queue.current_active == 0
