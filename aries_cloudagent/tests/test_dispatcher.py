import asyncio
import json

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from .. import dispatcher as test_module
from ..config.injection_context import InjectionContext
from ..connections.models.connection_record import ConnectionRecord
from ..messaging.agent_message import AgentMessage, AgentMessageSchema
from ..messaging.error import MessageParseError
from ..messaging.message_delivery import MessageDelivery
from ..messaging.outbound_message import OutboundMessage
from ..protocols.problem_report.message import ProblemReport
from ..messaging.protocol_registry import ProtocolRegistry
from ..messaging.serializer import MessageSerializer


def make_context() -> InjectionContext:
    context = InjectionContext()
    context.injector.bind_instance(ProtocolRegistry, ProtocolRegistry())
    context.injector.bind_instance(MessageSerializer, MessageSerializer())
    return context


def make_delivery() -> MessageDelivery:
    return MessageDelivery()


def make_connection_record() -> ConnectionRecord:
    return ConnectionRecord()


class Receiver:
    def __init__(self):
        self.messages = []

    async def send(self, message: OutboundMessage):
        self.messages.append(message)


class StubAgentMessage(AgentMessage):
    class Meta:
        handler_class = "StubAgentMessageHandler"
        schema_class = "StubAgentMessageSchema"
        message_type = "stub-message"


class StubAgentMessageSchema(AgentMessageSchema):
    class Meta:
        model_class = StubAgentMessage


class StubAgentMessageHandler:
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
        rcv = Receiver()
        message = {"@type": StubAgentMessage.Meta.message_type}

        with async_mock.patch.object(
            StubAgentMessageHandler, "handle", autospec=True
        ) as handler_mock:
            await dispatcher.dispatch(
                message, make_delivery(), make_connection_record(), rcv.send
            )
            await asyncio.sleep(0.1)
            handler_mock.assert_awaited_once()
            assert isinstance(handler_mock.call_args[0][1].message, StubAgentMessage)
            assert isinstance(
                handler_mock.call_args[0][2], test_module.DispatcherResponder
            )

    async def test_bad_message_dispatch(self):
        dispatcher = test_module.Dispatcher(make_context())
        rcv = Receiver()
        bad_message = {"bad": "message"}
        await dispatcher.dispatch(
            bad_message, make_delivery(), make_connection_record(), rcv.send
        )
        await asyncio.sleep(0.1)
        assert rcv.messages and isinstance(rcv.messages[0], OutboundMessage)
        payload = json.loads(rcv.messages[0].payload)
        assert payload["@type"] == ProblemReport.Meta.message_type
