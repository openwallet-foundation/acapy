"""Test routes.py"""
from asynctest import mock
import pytest

from .. import routes as test_module
from .....config.settings import Settings
from .....core.event_bus import Event, MockEventBus
from .....core.in_memory import InMemoryProfile
from .....core.profile import Profile
from .....messaging.responder import BaseResponder, MockResponder
from .....revocation.util import (
    REVOCATION_CLEAR_PENDING_EVENT,
    REVOCATION_EVENT_PREFIX,
    REVOCATION_PUBLISHED_EVENT,
)
from .....storage.error import StorageError, StorageNotFoundError


@pytest.fixture
def responder():
    yield MockResponder()


@pytest.fixture
def profile(responder):
    yield InMemoryProfile.test_profile(bind={BaseResponder: responder})


def test_register_events():
    """Test handlers are added on register.

    This test need not be particularly in depth to keep it from getting brittle.
    """
    event_bus = MockEventBus()
    test_module.register_events(event_bus)
    assert event_bus.topic_patterns_to_subscribers


@pytest.mark.asyncio
async def test_on_revocation_published(profile: Profile, responder: MockResponder):
    """Test revocation published event handler."""
    mock_rec = mock.MagicMock()
    mock_rec.cred_rev_id = "mock"
    mock_rec.delete_record = mock.CoroutineMock()

    MockRec = mock.MagicMock()
    MockRec.query_by_rev_reg_id = mock.CoroutineMock(return_value=[mock_rec])

    topic = f"{REVOCATION_EVENT_PREFIX}{REVOCATION_PUBLISHED_EVENT}::mock"
    event = Event(topic, {"rev_reg_id": "mock", "crids": ["mock"]})

    assert isinstance(profile.settings, Settings)
    profile.settings["revocation.notify"] = True

    with mock.patch.object(test_module, "RevNotificationRecord", MockRec):
        await test_module.on_revocation_published(profile, event)

    MockRec.query_by_rev_reg_id.assert_called_once()
    mock_rec.delete_record.assert_called_once()
    assert responder.messages


@pytest.mark.asyncio
async def test_on_revocation_published_no_notify(
    profile: Profile, responder: MockResponder
):
    """Test revocation published event handler."""
    mock_rec = mock.MagicMock()
    mock_rec.cred_rev_id = "mock"
    mock_rec.delete_record = mock.CoroutineMock()

    MockRec = mock.MagicMock()
    MockRec.query_by_rev_reg_id = mock.CoroutineMock(return_value=[mock_rec])

    topic = f"{REVOCATION_EVENT_PREFIX}{REVOCATION_PUBLISHED_EVENT}::mock"
    event = Event(topic, {"rev_reg_id": "mock", "crids": ["mock"]})

    assert isinstance(profile.settings, Settings)
    profile.settings["revocation.notify"] = False

    with mock.patch.object(test_module, "RevNotificationRecord", MockRec):
        await test_module.on_revocation_published(profile, event)

    MockRec.query_by_rev_reg_id.assert_called_once()
    mock_rec.delete_record.assert_called_once()
    assert not responder.messages


@pytest.mark.asyncio
async def test_on_revocation_published_x_not_found(
    profile: Profile, responder: MockResponder
):
    """Test revocation published event handler."""
    MockRec = mock.MagicMock()
    MockRec.query_by_rev_reg_id = mock.CoroutineMock(side_effect=StorageNotFoundError)

    topic = f"{REVOCATION_EVENT_PREFIX}{REVOCATION_PUBLISHED_EVENT}::mock"
    event = Event(topic, {"rev_reg_id": "mock", "crids": ["mock"]})

    with mock.patch.object(test_module, "RevNotificationRecord", MockRec):
        await test_module.on_revocation_published(profile, event)

    MockRec.query_by_rev_reg_id.assert_called_once()
    assert not responder.messages


@pytest.mark.asyncio
async def test_on_revocation_published_x_storage_error(
    profile: Profile, responder: MockResponder
):
    """Test revocation published event handler."""
    MockRec = mock.MagicMock()
    MockRec.query_by_rev_reg_id = mock.CoroutineMock(side_effect=StorageError)

    topic = f"{REVOCATION_EVENT_PREFIX}{REVOCATION_PUBLISHED_EVENT}::mock"
    event = Event(topic, {"rev_reg_id": "mock", "crids": ["mock"]})

    with mock.patch.object(test_module, "RevNotificationRecord", MockRec):
        await test_module.on_revocation_published(profile, event)

    MockRec.query_by_rev_reg_id.assert_called_once()
    assert not responder.messages


@pytest.mark.asyncio
async def test_on_pending_cleared(profile: Profile):
    """Test pending revocation cleared event."""
    mock_rec = mock.MagicMock()
    mock_rec.delete_record = mock.CoroutineMock()

    MockRec = mock.MagicMock()
    MockRec.query_by_rev_reg_id = mock.CoroutineMock(return_value=[mock_rec])

    topic = f"{REVOCATION_EVENT_PREFIX}{REVOCATION_CLEAR_PENDING_EVENT}::mock"
    event = Event(topic, {"rev_reg_id": "mock"})

    with mock.patch.object(test_module, "RevNotificationRecord", MockRec):
        await test_module.on_pending_cleared(profile, event)

    mock_rec.delete_record.assert_called_once()
