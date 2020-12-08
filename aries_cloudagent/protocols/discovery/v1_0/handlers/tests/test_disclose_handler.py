import pytest

from ......core.protocol_registry import ProtocolRegistry
from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder

from .....didcomm_prefix import DIDCommPrefix

from ...handlers.disclose_handler import DiscloseHandler
from ...messages.disclose import Disclose

TEST_MESSAGE_FAMILY = "TEST_FAMILY"
TEST_MESSAGE_TYPE = TEST_MESSAGE_FAMILY + "/MESSAGE"


@pytest.fixture()
def request_context() -> RequestContext:
    ctx = RequestContext.test_context()
    yield ctx


class TestDiscloseHandler:
    @pytest.mark.asyncio
    async def test_disclose(self, request_context):
        registry = ProtocolRegistry()
        registry.register_message_types({TEST_MESSAGE_TYPE: object()})
        request_context.injector.bind_instance(ProtocolRegistry, registry)
        request_context.message = Disclose(
            protocols=[
                {
                    "pid": DIDCommPrefix.qualify_current(
                        "test_proto/v1.0/test_message"
                    ),
                    "roles": [],
                }
            ]
        )

        handler = DiscloseHandler()
        mock_responder = MockResponder()
        await handler.handle(request_context, mock_responder)
        assert not mock_responder.messages
