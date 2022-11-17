"""Test RevokeHandler."""

import pytest

from ......config.settings import Settings
from ......core.event_bus import EventBus, MockEventBus
from ......core.in_memory import InMemoryProfile
from ......core.profile import Profile
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder, BaseResponder
from ...messages.revoke import Revoke
from ..revoke_handler import RevokeHandler


@pytest.fixture
def event_bus():
    yield MockEventBus()


@pytest.fixture
def responder():
    yield MockResponder()


@pytest.fixture
def profile(event_bus):
    yield InMemoryProfile.test_profile(bind={EventBus: event_bus})


@pytest.fixture
def message():
    yield Revoke(
        revocation_format="indy-anoncreds",
        credential_id="mock_cred_revocation_id",
        comment="mock_comment",
    )


@pytest.fixture
def context(profile: Profile, message: Revoke):
    request_context = RequestContext(profile)
    request_context.message = message
    yield request_context


@pytest.mark.asyncio
async def test_handle(
    context: RequestContext, responder: BaseResponder, event_bus: MockEventBus
):
    await RevokeHandler().handle(context, responder)
    assert event_bus.events
    [(_, received)] = event_bus.events
    assert received.topic == RevokeHandler.RECIEVED_TOPIC
    assert "revocation_format" in received.payload
    assert "credential_id" in received.payload
    assert "comment" in received.payload


@pytest.mark.asyncio
async def test_handle_monitor(
    context: RequestContext, responder: BaseResponder, event_bus: MockEventBus
):
    context.settings["revocation.monitor_notification"] = True
    await RevokeHandler().handle(context, responder)
    [(_, webhook), (_, received)] = event_bus.events

    assert webhook.topic == RevokeHandler.WEBHOOK_TOPIC
    assert "revocation_format" in received.payload
    assert "credential_id" in received.payload
    assert "comment" in webhook.payload

    assert received.topic == RevokeHandler.RECIEVED_TOPIC
    assert "revocation_format" in received.payload
    assert "credential_id" in received.payload
    assert "comment" in received.payload
