"""Test routes.py"""

import pytest
import pytest_asyncio

from .....config.settings import Settings
from .....core.event_bus import Event, MockEventBus
from .....core.profile import Profile
from .....messaging.responder import BaseResponder, MockResponder
from .....protocols.revocation_notification.v1_0.models.rev_notification_record import (
    RevNotificationRecord,
)
from .....revocation.util import (
    REVOCATION_CLEAR_PENDING_EVENT,
    REVOCATION_EVENT_PREFIX,
    REVOCATION_PUBLISHED_EVENT,
)
from .....storage.error import StorageError, StorageNotFoundError
from .....tests import mock
from .....utils.testing import create_test_profile
from .. import routes as test_module


@pytest.fixture
def responder():
    yield MockResponder()


@pytest_asyncio.fixture
async def profile(responder):
    profile = await create_test_profile()
    profile.context.injector.bind_instance(BaseResponder, responder)
    yield profile


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
    mock_rec.query_by_rev_reg_id = mock.CoroutineMock(return_value=[mock_rec])

    topic = f"{REVOCATION_EVENT_PREFIX}{REVOCATION_PUBLISHED_EVENT}::mock"
    event = Event(topic, {"rev_reg_id": "mock", "crids": ["mock"]})

    assert isinstance(profile.settings, Settings)

    profile.settings.set_value("revocation.notify", True)

    with mock.patch.object(test_module, "RevNotificationRecord", mock_rec):
        await test_module.on_revocation_published(profile, event)

    mock_rec.query_by_rev_reg_id.assert_called_once()
    mock_rec.delete_record.assert_called_once()
    assert responder.messages

    # Test with integer crids
    mock_rec.cred_rev_id = "1"
    mock_rec.query_by_rev_reg_id = mock.CoroutineMock(return_value=[mock_rec])
    event = Event(topic, {"rev_reg_id": "mock", "crids": [1]})

    with mock.patch.object(test_module, "RevNotificationRecord", mock_rec):
        await test_module.on_revocation_published(profile, event)

    mock_rec.query_by_rev_reg_id.assert_called_once()
    assert mock_rec.delete_record.call_count == 2

    # Test with empty crids
    mock_rec.cred_rev_id = "1"
    mock_rec.query_by_rev_reg_id = mock.CoroutineMock(return_value=[mock_rec])
    event = Event(topic, {"rev_reg_id": "mock", "crids": []})

    with mock.patch.object(test_module, "RevNotificationRecord", mock_rec):
        await test_module.on_revocation_published(profile, event)

    mock_rec.query_by_rev_reg_id.assert_called_once()
    assert mock_rec.delete_record.call_count == 2


@pytest.mark.asyncio
async def test_on_revocation_published_x_not_found(
    profile: Profile, responder: MockResponder
):
    """Test revocation published event handler."""
    mock_rec = mock.MagicMock()
    mock_rec.query_by_rev_reg_id = mock.CoroutineMock(side_effect=StorageNotFoundError)

    topic = f"{REVOCATION_EVENT_PREFIX}{REVOCATION_PUBLISHED_EVENT}::mock"
    event = Event(topic, {"rev_reg_id": "mock", "crids": ["mock"]})

    with mock.patch.object(test_module, "RevNotificationRecord", mock_rec):
        await test_module.on_revocation_published(profile, event)

    mock_rec.query_by_rev_reg_id.assert_called_once()
    assert not responder.messages


@pytest.mark.asyncio
async def test_on_revocation_published_x_storage_error(
    profile: Profile, responder: MockResponder
):
    """Test revocation published event handler."""
    mock_rec = mock.MagicMock()
    mock_rec.query_by_rev_reg_id = mock.CoroutineMock(side_effect=StorageError)

    topic = f"{REVOCATION_EVENT_PREFIX}{REVOCATION_PUBLISHED_EVENT}::mock"
    event = Event(topic, {"rev_reg_id": "mock", "crids": ["mock"]})

    with mock.patch.object(test_module, "RevNotificationRecord", mock_rec):
        await test_module.on_revocation_published(profile, event)

    mock_rec.query_by_rev_reg_id.assert_called_once()
    assert not responder.messages


@pytest.mark.asyncio
async def test_on_pending_cleared(profile: Profile):
    """Test pending revocation cleared event."""
    mock_rec = mock.MagicMock(RevNotificationRecord, autospec=True)
    mock_rec.delete_record = mock.CoroutineMock()
    mock_rec.query_by_rev_reg_id = mock.CoroutineMock(return_value=[mock_rec])

    topic = f"{REVOCATION_EVENT_PREFIX}{REVOCATION_CLEAR_PENDING_EVENT}::mock"
    event = Event(topic, {"rev_reg_id": "mock"})

    with mock.patch.object(test_module, "RevNotificationRecord", mock_rec):
        await test_module.on_pending_cleared(profile, event)

    mock_rec.delete_record.assert_called_once()
