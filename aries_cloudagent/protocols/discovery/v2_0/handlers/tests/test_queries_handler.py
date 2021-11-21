import pytest

from asynctest import mock as async_mock

from ......core.protocol_registry import ProtocolRegistry
from ......core.goal_code_registry import GoalCodeRegistry
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......protocols.issue_credential.v1_0.controller import (
    ISSUE_VC,
    PARTICIPATE_VC_INTERACTION,
)
from ......protocols.issue_credential.v1_0.message_types import (
    CONTROLLERS as issue_cred_v1_controller,
)
from ......protocols.present_proof.v1_0.message_types import (
    CONTROLLERS as pres_proof_v1_controller,
)

from ...handlers.queries_handler import QueriesHandler
from ...manager import V20DiscoveryMgr
from ...messages.disclosures import Disclosures
from ...messages.queries import Queries, QueryItem

TEST_MESSAGE_FAMILY = "TEST_FAMILY"
TEST_MESSAGE_TYPE = TEST_MESSAGE_FAMILY + "/MESSAGE"


@pytest.fixture()
def request_context() -> RequestContext:
    ctx = RequestContext.test_context()
    protocol_registry = ProtocolRegistry()
    goal_code_registry = GoalCodeRegistry()
    protocol_registry.register_message_types({TEST_MESSAGE_TYPE: object()})
    goal_code_registry.register_controllers(issue_cred_v1_controller)
    profile = ctx.profile
    profile.context.injector.bind_instance(ProtocolRegistry, protocol_registry)
    profile.context.injector.bind_instance(GoalCodeRegistry, goal_code_registry)
    yield ctx


class TestQueriesHandler:
    @pytest.mark.asyncio
    async def test_queries_all(self, request_context):
        test_queries = [
            QueryItem(feature_type="protocol", match="*"),
        ]
        queries = Queries(queries=test_queries)
        queries.assign_thread_id("test123")
        request_context.message = queries
        handler = QueriesHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert isinstance(result, Disclosures)
        assert result.disclosures[0].get("id") == TEST_MESSAGE_FAMILY
        assert not target

    @pytest.mark.asyncio
    async def test_queries_protocol_goal_code_all(self, request_context):
        test_queries = [
            QueryItem(feature_type="protocol", match="*"),
            QueryItem(feature_type="goal-code", match="*"),
        ]
        queries = Queries(queries=test_queries)
        queries.assign_thread_id("test123")
        request_context.message = queries
        handler = QueriesHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert isinstance(result, Disclosures)
        assert result.disclosures[0].get("id") == TEST_MESSAGE_FAMILY
        assert result.disclosures[0].get("feature-type") == "protocol"
        assert result.disclosures[1].get("id") == PARTICIPATE_VC_INTERACTION
        assert result.disclosures[1].get("feature-type") == "goal-code"
        assert result.disclosures[2].get("id") == ISSUE_VC
        assert result.disclosures[2].get("feature-type") == "goal-code"
        assert not target

    @pytest.mark.asyncio
    async def test_queries_protocol_goal_code_all_disclose_list_settings(
        self, request_context
    ):
        profile = request_context.profile
        protocol_registry = profile.inject(ProtocolRegistry)
        protocol_registry.register_message_types({"TEST_FAMILY_B/MESSAGE": object()})
        profile.context.injector.bind_instance(ProtocolRegistry, protocol_registry)
        goal_code_registry = profile.inject(GoalCodeRegistry)
        goal_code_registry.register_controllers(pres_proof_v1_controller)
        profile.context.injector.bind_instance(GoalCodeRegistry, goal_code_registry)
        profile.settings["disclose_protocol_list"] = [TEST_MESSAGE_FAMILY]
        profile.settings["disclose_goal_code_list"] = [
            PARTICIPATE_VC_INTERACTION,
            ISSUE_VC,
        ]
        test_queries = [
            QueryItem(feature_type="protocol", match="*"),
            QueryItem(feature_type="goal-code", match="*"),
        ]
        queries = Queries(queries=test_queries)
        queries.assign_thread_id("test123")
        request_context.message = queries
        handler = QueriesHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert isinstance(result, Disclosures)
        assert result.disclosures[0].get("id") == TEST_MESSAGE_FAMILY
        assert result.disclosures[0].get("feature-type") == "protocol"
        assert result.disclosures[1].get("id") == PARTICIPATE_VC_INTERACTION
        assert result.disclosures[1].get("feature-type") == "goal-code"
        assert result.disclosures[2].get("id") == ISSUE_VC
        assert result.disclosures[2].get("feature-type") == "goal-code"
        assert not target

    @pytest.mark.asyncio
    async def test_receive_query_process_disclosed(self, request_context):
        test_queries = [
            QueryItem(feature_type="protocol", match="*"),
            QueryItem(feature_type="goal-code", match="*"),
        ]
        queries_msg = Queries(queries=test_queries)
        queries_msg.assign_thread_id("test123")
        request_context.message = queries_msg
        handler = QueriesHandler()
        responder = MockResponder()
        with async_mock.patch.object(
            V20DiscoveryMgr, "execute_protocol_query", async_mock.CoroutineMock()
        ) as mock_exec_protocol_query, async_mock.patch.object(
            V20DiscoveryMgr, "execute_goal_code_query", async_mock.CoroutineMock()
        ) as mock_goal_code_protocol_query:
            mock_exec_protocol_query.return_value = [
                {"test": "test"},
                {
                    "pid": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/action-menu/1.0",
                    "roles": ["provider"],
                },
            ]
            mock_goal_code_protocol_query.return_value = ["aries.vc", "aries.vc.test"]
            await handler.handle(request_context, responder)
            messages = responder.messages
            assert len(messages) == 1
            result, target = messages[0]
            assert isinstance(result, Disclosures)
            assert (
                result.disclosures[0].get("id")
                == "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/action-menu/1.0"
            )
            assert result.disclosures[0].get("feature-type") == "protocol"
            assert result.disclosures[1].get("id") == "aries.vc"
            assert result.disclosures[1].get("feature-type") == "goal-code"
            assert result.disclosures[2].get("id") == "aries.vc.test"
            assert result.disclosures[2].get("feature-type") == "goal-code"
            assert not target
