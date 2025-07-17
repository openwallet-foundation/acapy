from unittest import IsolatedAsyncioTestCase

from ......connections.models.conn_record import ConnRecord
from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......tests import mock
from ......utils.testing import create_test_profile
from .....out_of_band.v1_0.messages.invitation import InvitationMessage, Service
from ...messages.forward_invitation import ForwardInvitation
from .. import forward_invitation_handler as test_module

TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_ROUTE_VERKEY = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"
TEST_LABEL = "Label"
TEST_ENDPOINT = "http://localhost"
TEST_IMAGE_URL = "http://aries.ca/images/sample.png"


class TestForwardInvitationHandler(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.context = RequestContext.test_context(await create_test_profile())

        self.context.connection_ready = True
        service = Service(
            did=TEST_DID,
            recipient_keys=[TEST_VERKEY],
            service_endpoint=TEST_ENDPOINT,
            routing_keys=[TEST_ROUTE_VERKEY],
        )
        self.context.message = ForwardInvitation(
            invitation=InvitationMessage(
                label=TEST_LABEL,
                image_url=TEST_IMAGE_URL,
                services=[service],
            ),
            message="Hello World",
        )

    async def test_handle(self):
        handler = test_module.ForwardInvitationHandler()

        responder = MockResponder()
        with mock.patch.object(
            test_module, "OutOfBandManager", autospec=True
        ) as mock_mgr:
            mock_mgr.return_value.receive_invitation = mock.CoroutineMock(
                return_value=ConnRecord(connection_id="dummy")
            )

            await handler.handle(self.context, responder)
            assert not (responder.messages)

    async def test_handle_x(self):
        handler = test_module.ForwardInvitationHandler()

        responder = MockResponder()
        with mock.patch.object(
            test_module, "OutOfBandManager", autospec=True
        ) as mock_mgr:
            mock_mgr.return_value.receive_invitation = mock.CoroutineMock(
                side_effect=test_module.OutOfBandManagerError("oops")
            )

            await handler.handle(self.context, responder)
            messages = responder.messages
            assert len(messages) == 1
            (result, _) = messages[0]
            assert type(result) is test_module.ProblemReport

    async def test_handle_not_ready(self):
        handler = test_module.ForwardInvitationHandler()
        self.context.connection_ready = False

        with self.assertRaises(HandlerException):
            await handler.handle(self.context, None)
