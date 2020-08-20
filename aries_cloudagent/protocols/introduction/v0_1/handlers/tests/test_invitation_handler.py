from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.messaging.base_handler import HandlerException
from aries_cloudagent.messaging.request_context import RequestContext
from aries_cloudagent.messaging.responder import MockResponder
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.storage.basic import BasicStorage
from aries_cloudagent.protocols.connections.v1_0.messages.connection_invitation import (
    ConnectionInvitation,
)

from ...messages.invitation import Invitation
from ...messages.invitation_request import InvitationRequest

from .. import invitation_handler as test_module

TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_ROUTE_VERKEY = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"
TEST_LABEL = "Label"
TEST_ENDPOINT = "http://localhost"
TEST_IMAGE_URL = "http://aries.ca/images/sample.png"


class TestInvitationHandler(AsyncTestCase):
    async def setUp(self):
        self.storage = BasicStorage()

        self.context = RequestContext(
            base_context=InjectionContext(enforce_typing=False)
        )
        self.context.injector.bind_instance(BaseStorage, self.storage)

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
        self.context.connection_record = async_mock.MagicMock(connection_id="dummy")

    async def test_handle(self):
        handler = test_module.InvitationHandler()

        mock_conn_rec = async_mock.MagicMock(connection_id="dummy")

        responder = MockResponder()
        with async_mock.patch.object(
            self.context, "inject", async_mock.CoroutineMock()
        ) as mock_ctx_inject:
            mock_ctx_inject.return_value = async_mock.MagicMock(
                return_invitation=async_mock.CoroutineMock()
            )

            await handler.handle(self.context, responder)

            assert mock_ctx_inject.return_value.return_invitation.called_once_with(
                self.context.connection_record.connection_id,
                self.context.message,
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
