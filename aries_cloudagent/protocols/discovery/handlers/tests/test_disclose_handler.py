import pytest

from .....core.protocol_registry import ProtocolRegistry
from .....messaging.base_handler import HandlerException
from .....messaging.request_context import RequestContext
from .....messaging.responder import MockResponder

from ...handlers.disclose_handler import DiscloseHandler
from ...messages.disclose import Disclose


TEST_MESSAGE_FAMILY = "TEST_FAMILY"
TEST_MESSAGE_TYPE = TEST_MESSAGE_FAMILY + "/MESSAGE"


class TestQueryHandler:
    @pytest.mark.asyncio
    async def test_disclose(self):
        ctx = RequestContext()
        registry = ProtocolRegistry()
        registry.register_message_types({TEST_MESSAGE_TYPE: object()})
        ctx.injector.bind_instance(ProtocolRegistry, registry)
        ctx.message = Disclose(
            protocols=[
                {
                    "pid": "did:sov:BzCbsNYhMrjHiqZDTUASHg;test_proto/test_message",
                    "roles": [],
                }
            ]
        )

        handler = DiscloseHandler()
        mock_responder = MockResponder()
        await handler.handle(ctx, mock_responder)
        assert not mock_responder.messages
