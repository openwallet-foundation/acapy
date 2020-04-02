import asyncio
import json

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ...config.injection_context import InjectionContext
from ...connections.models.connection_record import ConnectionRecord
from ...core.protocol_registry import ProtocolRegistry
from ...messaging.agent_message import AgentMessage, AgentMessageSchema
from ...messaging.error import MessageParseError

# FIXME: We shouldn't rely on a hardcoded message version here.
from ...protocols.problem_report.v1_0.message import ProblemReport

from ...transport.inbound.message import InboundMessage
from ...transport.inbound.receipt import MessageReceipt
from ...transport.outbound.message import OutboundMessage

from .. import dispatcher as test_module


def make_context() -> InjectionContext:
    context = InjectionContext()
    context.injector.bind_instance(ProtocolRegistry, ProtocolRegistry())
    return context


def make_inbound(payload) -> InboundMessage:
    return InboundMessage(payload, MessageReceipt())


# def make_connection_record() -> ConnectionRecord:
#   return ConnectionRecord()


class Receiver:
    def __init__(self):
        self.messages = []

    async def send(
        self,
        context: InjectionContext,
        message: OutboundMessage,
        inbound: InboundMessage = None,
    ):
        self.messages.append((context, message, inbound))


class StubAgentMessage(AgentMessage):
    class Meta:
        handler_class = "StubAgentMessageHandler"
        schema_class = "StubAgentMessageSchema"
        message_type = "proto-name/1.1/message-type"


class StubAgentMessageSchema(AgentMessageSchema):
    class Meta:
        model_class = StubAgentMessage


class StubAgentMessageHandler:
    async def handle(self, context, responder):
        pass


class StubV1_2AgentMessage(AgentMessage):
    class Meta:
        handler_class = "StubV1_2AgentMessageHandler"
        schema_class = "StubV1_2AgentMessageSchema"
        message_type = "proto-name/1.2/message-type"

class StubV1_2AgentMessageSchema(AgentMessageSchema):
    class Meta:
        model_class = StubV1_2AgentMessage


class StubV1_2AgentMessageHandler:
    async def handle(self, context, responder):
        pass


class TestDispatcher(AsyncTestCase):
    async def test_dispatch(self):
        context = make_context()
        context.enforce_typing = False
        registry = await context.inject(ProtocolRegistry)
        registry.register_message_types(
            {StubAgentMessage.Meta.message_type: StubAgentMessage}
        )
        dispatcher = test_module.Dispatcher(context)
        await dispatcher.setup()
        rcv = Receiver()
        message = {"@type": StubAgentMessage.Meta.message_type}

        with async_mock.patch.object(
            StubAgentMessageHandler, "handle", autospec=True
        ) as handler_mock:
            await dispatcher.queue_message(make_inbound(message), rcv.send)
            await dispatcher.task_queue
            handler_mock.assert_awaited_once()
            assert isinstance(handler_mock.call_args[0][1].message, StubAgentMessage)
            assert isinstance(
                handler_mock.call_args[0][2], test_module.DispatcherResponder
            )

    async def test_dispatch_versioned_message(self):
        context = make_context()
        context.enforce_typing = False
        registry = await context.inject(ProtocolRegistry)
        registry.register_message_types(
            {StubAgentMessage.Meta.message_type: StubAgentMessage},
            version_definition={
                "major_version": 1,
                "minimum_minor_version": 0,
                "current_minor_version": 1,
                "path": "v1_1",
            },
        )
        dispatcher = test_module.Dispatcher(context)
        await dispatcher.setup()
        rcv = Receiver()
        message = {"@type": StubAgentMessage.Meta.message_type}

        with async_mock.patch.object(
            StubAgentMessageHandler, "handle", autospec=True
        ) as handler_mock:
            await dispatcher.queue_message(make_inbound(message), rcv.send)
            await dispatcher.task_queue
            handler_mock.assert_awaited_once()
            assert isinstance(handler_mock.call_args[0][1].message, StubAgentMessage)
            assert isinstance(
                handler_mock.call_args[0][2], test_module.DispatcherResponder
            )

    async def test_dispatch_versioned_message_handle_greater_succeeds(self):
        context = make_context()
        context.enforce_typing = False
        registry = await context.inject(ProtocolRegistry)
        registry.register_message_types(
            {StubAgentMessage.Meta.message_type: StubAgentMessage},
            version_definition={
                "major_version": 1,
                "minimum_minor_version": 0,
                "current_minor_version": 1,
                "path": "v1_1",
            },
        )
        dispatcher = test_module.Dispatcher(context)
        await dispatcher.setup()
        rcv = Receiver()
        message = {"@type": StubV1_2AgentMessage.Meta.message_type}

        with async_mock.patch.object(
            StubAgentMessageHandler, "handle", autospec=True
        ) as handler_mock:
            await dispatcher.queue_message(make_inbound(message), rcv.send)
            await dispatcher.task_queue
            handler_mock.assert_awaited_once()
            assert isinstance(handler_mock.call_args[0][1].message, StubAgentMessage)
            assert isinstance(
                handler_mock.call_args[0][2], test_module.DispatcherResponder
            )

    async def test_dispatch_versioned_message_fail(self):
        context = make_context()
        context.enforce_typing = False
        registry = await context.inject(ProtocolRegistry)
        registry.register_message_types(
            {StubV1_2AgentMessage.Meta.message_type: StubV1_2AgentMessage},
            version_definition={
                "major_version": 1,
                "minimum_minor_version": 2,
                "current_minor_version": 2,
                "path": "v1_2",
            },
        )
        dispatcher = test_module.Dispatcher(context)
        await dispatcher.setup()
        rcv = Receiver()
        message = {"@type": StubAgentMessage.Meta.message_type}

        with async_mock.patch.object(
            StubAgentMessageHandler, "handle", autospec=True
        ) as handler_mock:
            await dispatcher.queue_message(make_inbound(message), rcv.send)
            await dispatcher.task_queue
            assert rcv.messages and isinstance(rcv.messages[0][1], OutboundMessage)
            payload = json.loads(rcv.messages[0][1].payload)
            assert payload["@type"] == ProblemReport.Meta.message_type


    async def test_bad_message_dispatch(self):
        dispatcher = test_module.Dispatcher(make_context())
        await dispatcher.setup()
        rcv = Receiver()
        bad_message = {"bad": "message"}
        await dispatcher.queue_message(make_inbound(bad_message), rcv.send)
        await dispatcher.task_queue
        assert rcv.messages and isinstance(rcv.messages[0][1], OutboundMessage)
        payload = json.loads(rcv.messages[0][1].payload)
        assert payload["@type"] == ProblemReport.Meta.message_type
