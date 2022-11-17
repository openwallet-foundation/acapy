"""Test handler for keylist-update-response message."""

from functools import partial
from typing import AsyncGenerator
import pytest
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock


from ......connections.models.conn_record import ConnRecord
from ......core.event_bus import EventBus, MockEventBus
from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ...messages.inner.keylist_update_rule import KeylistUpdateRule
from ...messages.inner.keylist_updated import KeylistUpdated
from ...messages.keylist_update_response import KeylistUpdateResponse
from ...manager import MediationManager
from ...route_manager import RouteManager
from ...tests.test_route_manager import MockRouteManager
from ..keylist_update_response_handler import KeylistUpdateResponseHandler

TEST_CONN_ID = "conn-id"
TEST_THREAD_ID = "thread-id"
TEST_VERKEY = "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
TEST_ROUTE_VERKEY = "did:key:z6MknxTj6Zj1VrDWc1ofaZtmCVv2zNXpD58Xup4ijDGoQhya"


class TestKeylistUpdateResponseHandler(AsyncTestCase):
    """Test handler for keylist-update-response message."""

    async def setUp(self):
        """Setup test dependencies."""
        self.context = RequestContext.test_context()
        self.updated = [
            KeylistUpdated(
                recipient_key=TEST_VERKEY,
                action=KeylistUpdateRule.RULE_ADD,
                result=KeylistUpdated.RESULT_SUCCESS,
            )
        ]
        self.context.message = KeylistUpdateResponse(updated=self.updated)
        self.context.connection_ready = True
        self.context.connection_record = ConnRecord(connection_id=TEST_CONN_ID)
        self.mock_event_bus = MockEventBus()
        self.context.profile.context.injector.bind_instance(
            EventBus, self.mock_event_bus
        )
        self.route_manager = MockRouteManager()
        self.context.profile.context.injector.bind_instance(
            RouteManager, self.route_manager
        )

    async def test_handler_no_active_connection(self):
        handler, responder = KeylistUpdateResponseHandler(), MockResponder()
        self.context.connection_ready = False
        with pytest.raises(HandlerException) as exc:
            await handler.handle(self.context, responder)
            assert "no active connection" in str(exc.value)

    async def test_handler(self):
        handler, responder = KeylistUpdateResponseHandler(), MockResponder()
        with async_mock.patch.object(
            MediationManager, "store_update_results"
        ) as mock_store, async_mock.patch.object(
            handler, "notify_keylist_updated"
        ) as mock_notify:
            await handler.handle(self.context, responder)
            mock_store.assert_called_once_with(TEST_CONN_ID, self.updated)
            mock_notify.assert_called_once_with(
                self.context.profile, TEST_CONN_ID, self.context.message
            )

    async def test_notify_keylist_updated(self):
        """test notify_keylist_updated."""
        handler = KeylistUpdateResponseHandler()

        async def _result_generator():
            yield ConnRecord(connection_id="conn_id_1")
            yield ConnRecord(connection_id="conn_id_2")

        async def _retrieve_by_invitation_key(
            generator: AsyncGenerator, *args, **kwargs
        ):
            return await generator.__anext__()

        with async_mock.patch.object(
            self.route_manager,
            "connection_from_recipient_key",
            partial(_retrieve_by_invitation_key, _result_generator()),
        ):
            response = KeylistUpdateResponse(
                updated=[
                    KeylistUpdated(
                        recipient_key=TEST_ROUTE_VERKEY,
                        action=KeylistUpdateRule.RULE_ADD,
                        result=KeylistUpdated.RESULT_SUCCESS,
                    ),
                    KeylistUpdated(
                        recipient_key=TEST_VERKEY,
                        action=KeylistUpdateRule.RULE_REMOVE,
                        result=KeylistUpdated.RESULT_SUCCESS,
                    ),
                ],
            )

            response.assign_thread_id(TEST_THREAD_ID)
            await handler.notify_keylist_updated(
                self.context.profile, TEST_CONN_ID, response
            )
        assert self.mock_event_bus.events
        assert (
            self.mock_event_bus.events[0][1].topic
            == MediationManager.KEYLIST_UPDATED_EVENT
        )
        assert self.mock_event_bus.events[0][1].payload == {
            "connection_id": TEST_CONN_ID,
            "thread_id": TEST_THREAD_ID,
            "updated": [result.serialize() for result in response.updated],
            "mediated_connections": {
                TEST_ROUTE_VERKEY: "conn_id_1",
                TEST_VERKEY: "conn_id_2",
            },
        }

    async def test_notify_keylist_updated_x_unknown_recip_key(self):
        """test notify_keylist_updated."""
        handler = KeylistUpdateResponseHandler()
        response = KeylistUpdateResponse(
            updated=[
                KeylistUpdated(
                    recipient_key=TEST_ROUTE_VERKEY,
                    action=KeylistUpdateRule.RULE_ADD,
                    result=KeylistUpdated.RESULT_SUCCESS,
                ),
                KeylistUpdated(
                    recipient_key=TEST_VERKEY,
                    action=KeylistUpdateRule.RULE_REMOVE,
                    result=KeylistUpdated.RESULT_SUCCESS,
                ),
            ],
        )

        response.assign_thread_id(TEST_THREAD_ID)
        with pytest.raises(HandlerException):
            await handler.notify_keylist_updated(
                self.context.profile, TEST_CONN_ID, response
            )
