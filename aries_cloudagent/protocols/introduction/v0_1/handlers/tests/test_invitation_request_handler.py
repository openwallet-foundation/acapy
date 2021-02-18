from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......protocols.connections.v1_0.messages.connection_invitation import (
    ConnectionInvitation,
)

from ...messages.invitation import Invitation
from ...messages.invitation_request import InvitationRequest

from .. import invitation_request_handler as test_module

TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_ROUTE_VERKEY = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"
TEST_LABEL = "Label"
TEST_ENDPOINT = "http://localhost"
TEST_IMAGE_URL = "http://aries.ca/images/sample.png"


class TestInvitationRequestHandler(AsyncTestCase):
    async def setUp(self):
        self.context = RequestContext.test_context()
        self.context.connection_ready = True
        self.context.message = InvitationRequest(
            responder="test-agent",
            message="Hello World",
        )
        self.context.update_settings({"accept_requests": False})

    async def test_handle(self):
        handler = test_module.InvitationRequestHandler()

        responder = MockResponder()
        inv_req = InvitationRequest(responder=responder, message="Hello")

        with async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as mock_mgr:
            await handler.handle(self.context, responder)

    async def test_handle_auto_accept(self):
        handler = test_module.InvitationRequestHandler()
        self.context.update_settings({"accept_requests": True})

        conn_invitation = ConnectionInvitation(
            label=TEST_LABEL,
            did=TEST_DID,
            recipient_keys=[TEST_VERKEY],
            endpoint=TEST_ENDPOINT,
            routing_keys=[TEST_ROUTE_VERKEY],
            image_url=TEST_IMAGE_URL,
        )
        mock_conn_rec = async_mock.MagicMock(connection_id="dummy")

        responder = MockResponder()
        with async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as mock_mgr:
            mock_mgr.return_value.create_invitation = async_mock.CoroutineMock(
                return_value=(mock_conn_rec, conn_invitation)
            )

            await handler.handle(self.context, responder)
            assert mock_mgr.return_value.create_invitation.called_once_with()

            messages = responder.messages
            assert len(messages) == 1
            (result, _) = messages[0]
            assert type(result) == Invitation
            assert result._thread._thid == self.context.message._message_id

    async def test_handle_not_ready(self):
        handler = test_module.InvitationRequestHandler()
        self.context.connection_ready = False

        with self.assertRaises(HandlerException):
            await handler.handle(self.context, None)
