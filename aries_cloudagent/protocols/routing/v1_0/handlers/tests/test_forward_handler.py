from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
import json

from ......connections.models.connection_target import ConnectionTarget
from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...models.route_record import RouteRecord
from ...messages.forward import Forward

from .. import forward_handler as test_module

TEST_CONN_ID = "conn-id"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_ROUTE_VERKEY = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"


class TestForwardHandler(AsyncTestCase):
    async def setUp(self):
        self.context = RequestContext.test_context()
        self.context.connection_ready = True
        self.context.message = Forward(to="sample-did", msg={"msg": "sample-message"})

    async def test_handle(self):
        self.context.message_receipt = MessageReceipt(recipient_verkey=TEST_VERKEY)
        handler = test_module.ForwardHandler()

        responder = MockResponder()
        with async_mock.patch.object(
            test_module, "RoutingManager", autospec=True
        ) as mock_mgr, async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as mock_connection_mgr, async_mock.patch.object(
            self.context.profile, "notify", autospec=True
        ) as mock_notify:
            mock_mgr.return_value.get_recipient = async_mock.CoroutineMock(
                return_value=RouteRecord(connection_id="dummy")
            )
            mock_connection_mgr.return_value.get_connection_targets = (
                async_mock.CoroutineMock(
                    return_value=[
                        ConnectionTarget(
                            recipient_keys=["recip_key"],
                        )
                    ]
                )
            )

            await handler.handle(self.context, responder)

            mock_notify.assert_called_once_with(
                "acapy::forward::received",
                {
                    "connection_id": "dummy",
                    "status": "queued_for_delivery",
                    "recipient_key": "sample-did",
                },
            )

            messages = responder.messages
            assert len(messages) == 1
            (result, target) = messages[0]
            assert json.loads(result) == self.context.message.msg
            assert target["connection_id"] == "dummy"

    async def test_handle_receipt_no_recipient_verkey(self):
        self.context.message_receipt = MessageReceipt()
        handler = test_module.ForwardHandler()
        with self.assertRaises(HandlerException):
            await handler.handle(self.context, None)

    async def test_handle_cannot_resolve_recipient(self):
        self.context.message_receipt = MessageReceipt(recipient_verkey=TEST_VERKEY)
        handler = test_module.ForwardHandler()

        responder = MockResponder()
        with async_mock.patch.object(
            test_module, "RoutingManager", autospec=True
        ) as mock_mgr:
            mock_mgr.return_value.get_recipient = async_mock.CoroutineMock(
                side_effect=test_module.RoutingManagerError()
            )

            await handler.handle(self.context, responder)

            messages = responder.messages
            assert not messages
