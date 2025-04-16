"""Test RevokeHandler."""

from typing import Generator

import pytest
import pytest_asyncio

from ......core.event_bus import EventBus, MockEventBus
from ......core.profile import Profile
from ......messaging.request_context import RequestContext
from ......messaging.responder import BaseResponder, MockResponder
from ......utils.testing import create_test_profile
from ...messages.revoke import Revoke
from ..revoke_handler import RevokeHandler


@pytest.fixture
def event_bus():
    yield MockEventBus()


@pytest.fixture
def responder():
    yield MockResponder()


@pytest_asyncio.fixture
async def profile(event_bus):
    profile = await create_test_profile()
    profile.context.injector.bind_instance(EventBus, event_bus)
    yield profile


@pytest.fixture
def message():
    yield Revoke(
        revocation_format="indy-anoncreds",
        credential_id="mock_cred_revocation_id",
        comment="mock_comment",
    )


@pytest.fixture
def context(profile: Profile, message: Revoke) -> Generator[RequestContext, None, None]:
    request_context = RequestContext(profile)
    request_context.message = message
    yield request_context


@pytest.mark.asyncio
async def test_handle(
    context: RequestContext, responder: BaseResponder, event_bus: MockEventBus
):
    context.connection_ready = True
    await RevokeHandler().handle(context, responder)
    assert event_bus.events
    [(_, received)] = event_bus.events
    assert received.topic == RevokeHandler.RECEIVED_TOPIC
    assert "revocation_format" in received.payload
    assert "credential_id" in received.payload
    assert "comment" in received.payload


@pytest.mark.asyncio
async def test_handle_monitor(
    context: RequestContext, responder: BaseResponder, event_bus: MockEventBus
):
    context.settings["revocation.monitor_notification"] = True
    context.connection_ready = True
    await RevokeHandler().handle(context, responder)
    [(_, webhook), (_, received)] = event_bus.events

    assert webhook.topic == RevokeHandler.WEBHOOK_TOPIC
    assert "revocation_format" in received.payload
    assert "credential_id" in received.payload
    assert "comment" in webhook.payload

    assert received.topic == RevokeHandler.RECEIVED_TOPIC
    assert "revocation_format" in received.payload
    assert "credential_id" in received.payload
    assert "comment" in received.payload
