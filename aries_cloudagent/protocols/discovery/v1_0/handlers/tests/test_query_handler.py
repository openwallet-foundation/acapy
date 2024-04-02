import pytest

from aries_cloudagent.tests import mock

from ......core.protocol_registry import ProtocolRegistry
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder

from ...handlers.query_handler import QueryHandler
from ...messages.disclose import Disclose
from ...messages.query import Query

TEST_MESSAGE_FAMILY = "doc/proto/1.0"
TEST_MESSAGE_TYPE = TEST_MESSAGE_FAMILY + "/message"


@pytest.fixture()
def request_context():
    ctx = RequestContext.test_context()
    registry = ProtocolRegistry()
    registry.register_message_types({TEST_MESSAGE_TYPE: object()})
    profile = ctx.profile
    profile.context.injector.bind_instance(ProtocolRegistry, registry)
    yield ctx


class TestQueryHandler:
    @pytest.mark.asyncio
    async def test_query_all(self, request_context):
        query_msg = Query(query="*")
        query_msg.assign_thread_id("test123")
        request_context.message = query_msg
        handler = QueryHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert isinstance(result, Disclose) and result.protocols
        assert result.protocols[0]["pid"] == TEST_MESSAGE_FAMILY
        assert not target

    @pytest.mark.asyncio
    async def test_query_all_disclose_list_settings(self, request_context):
        profile = request_context.profile
        registry = profile.inject(ProtocolRegistry)
        registry.register_message_types({"doc/proto-b/1.0/message": object()})
        profile.context.injector.bind_instance(ProtocolRegistry, registry)
        profile.settings["disclose_protocol_list"] = [TEST_MESSAGE_FAMILY]
        query_msg = Query(query="*")
        query_msg.assign_thread_id("test123")
        request_context.message = query_msg
        handler = QueryHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert isinstance(result, Disclose) and result.protocols
        assert result.protocols[0]["pid"] == TEST_MESSAGE_FAMILY
        assert not target

    @pytest.mark.asyncio
    async def test_receive_query_process_disclosed(self, request_context):
        query_msg = Query(query="*")
        query_msg.assign_thread_id("test123")
        request_context.message = query_msg
        handler = QueryHandler()
        responder = MockResponder()
        with mock.patch.object(
            ProtocolRegistry, "protocols_matching_query", mock.MagicMock()
        ) as mock_query_match, mock.patch.object(
            ProtocolRegistry, "prepare_disclosed", mock.CoroutineMock()
        ) as mock_prepare_disclosed:
            mock_prepare_disclosed.return_value = [
                {"test": "test"},
                {
                    "pid": "https://didcomm.org/action-menu/1.0",
                    "roles": ["provider"],
                },
            ]
            await handler.handle(request_context, responder)
            messages = responder.messages
            assert len(messages) == 1
            result, target = messages[0]
            assert isinstance(result, Disclose) and result.protocols
            assert len(result.protocols) == 1
            assert result.protocols[0]["pid"] == "https://didcomm.org/action-menu/1.0"
            assert result.protocols[0]["roles"] == ["provider"]
            assert not target
