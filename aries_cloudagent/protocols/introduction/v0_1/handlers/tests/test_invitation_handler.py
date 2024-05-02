from unittest import IsolatedAsyncioTestCase
from aries_cloudagent.tests import mock

from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......protocols.connections.v1_0.messages.connection_invitation import (
    ConnectionInvitation,
)

from ...messages.invitation import Invitation

from .. import invitation_handler as test_module

TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_ROUTE_VERKEY = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"
TEST_LABEL = "Label"
TEST_ENDPOINT = "http://localhost"
TEST_IMAGE_URL = "http://aries.ca/images/sample.png"


class TestInvitationHandler(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.context = RequestContext.test_context()
        self.context.connection_ready = True
        self.context.message = Invitation(
            invitation=ConnectionInvitation(
                label=TEST_LABEL,
                did=TEST_DID,
                recipient_keys=[TEST_VERKEY],
                endpoint=TEST_ENDPOINT,
                routing_keys=[TEST_ROUTE_VERKEY],
                image_url=TEST_IMAGE_URL,
            ),
            message="Hello World",
        )
        self.context.connection_record = mock.MagicMock(connection_id="dummy")

    async def test_handle(self):
        handler = test_module.InvitationHandler()

        mock_conn_rec = mock.MagicMock(connection_id="dummy")

        responder = MockResponder()
        with mock.patch.object(
            self.context, "inject_or", mock.MagicMock()
        ) as mock_ctx_inject:
            mock_ctx_inject.return_value = mock.MagicMock(
                return_invitation=mock.CoroutineMock()
            )

            await handler.handle(self.context, responder)

            mock_ctx_inject.return_value.return_invitation.assert_called_once_with(
                self.context.connection_record.connection_id,
                self.context.message,
                mock.ANY,
                responder.send,
            )

    async def test_handle_no_service(self):
        handler = test_module.InvitationHandler()

        with self.assertRaises(HandlerException):
            await handler.handle(self.context, None)

    async def test_handle_not_ready(self):
        handler = test_module.InvitationHandler()
        self.context.connection_ready = False

        with self.assertRaises(HandlerException):
            await handler.handle(self.context, None)
