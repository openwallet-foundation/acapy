from asynctest import TestCase as AsyncTestCase
from marshmallow import fields
import json

from ..agent_message import AgentMessage, AgentMessageSchema
from ..decorators.signature_decorator import SignatureDecorator
from ..decorators.trace_decorator import TraceReport, TRACE_MESSAGE_TARGET
from ...wallet.basic import BasicWallet


class SignedAgentMessage(AgentMessage):
    """Signed agent message tests"""

    class Meta:
        """Meta data"""

        handler_class = None
        schema_class = "SignedAgentMessageSchema"
        message_type = "signed-agent-message"

    def __init__(self, value: str = None, **kwargs):
        super(SignedAgentMessage, self).__init__(**kwargs)
        self.value = value


class SignedAgentMessageSchema(AgentMessageSchema):
    """Utility schema"""

    class Meta:
        model_class = SignedAgentMessage
        signed_fields = ("value",)

    value = fields.Str(required=True)


class BasicAgentMessage(AgentMessage):
    """Simple agent message implementation"""

    class Meta:
        """Meta data"""

        schema_class = "AgentMessageSchema"
        message_type = "basic-message"


class TestAgentMessage(AsyncTestCase):
    """Tests agent message."""

    class BadImplementationClass(AgentMessage):
        """Test utility class."""

        pass

    def test_init(self):
        """Tests init class"""
        SignedAgentMessage()

        with self.assertRaises(TypeError) as context:
            self.BadImplementationClass()  # pylint: disable=E0110

        assert "Can't instantiate abstract" in str(context.exception)

    async def test_field_signature(self):
        wallet = BasicWallet()
        key_info = await wallet.create_signing_key()

        msg = SignedAgentMessage()
        msg.value = "Test value"
        await msg.sign_field("value", key_info.verkey, wallet)
        sig = msg.get_signature("value")
        assert isinstance(sig, SignatureDecorator)

        assert await sig.verify(wallet)
        assert await msg.verify_signed_field("value", wallet) == key_info.verkey
        assert await msg.verify_signatures(wallet)

        serial = msg.serialize()
        assert "value~sig" in serial and "value" not in serial

        loaded = SignedAgentMessage.deserialize(serial)
        assert isinstance(loaded, SignedAgentMessage)
        assert await loaded.verify_signed_field("value", wallet) == key_info.verkey

    async def test_assign_thread(self):
        msg = BasicAgentMessage()
        assert msg._thread_id == msg._id
        reply = BasicAgentMessage()
        reply.assign_thread_from(msg)
        assert reply._thread_id == msg._thread_id
        assert reply._thread_id != reply._id

    async def test_add_tracing(self):
        msg = BasicAgentMessage()
        msg.add_trace_decorator()
        tracer = msg._trace
        assert tracer.target == TRACE_MESSAGE_TARGET
        assert tracer.full_thread == True

        trace_report = TraceReport(
            msg_id=msg._id,
            thread_id=msg._thread_id,
            traced_type=msg._type,
            timestamp="123456789.123456",
            str_time="2019-01-01 12:34:56.7",
            handler="function.START",
            ellapsed_milli=27,
            outcome="OK! ...",
        )
        msg.add_trace_report(trace_report)
        tracer = msg._trace
        trace_reports = tracer.trace_reports
        assert len(trace_reports) == 1
        msg_trace_report = trace_reports[0]
        assert msg_trace_report.msg_id == msg._id
        assert msg_trace_report.thread_id == msg._thread_id
        assert msg_trace_report.handler == trace_report.handler
        assert msg_trace_report.ellapsed_milli == trace_report.ellapsed_milli
        assert msg_trace_report.traced_type == msg._type
        assert msg_trace_report.outcome == trace_report.outcome

        msg2 = BasicAgentMessage()
        msg2.assign_thread_from(msg)
        msg2.assign_trace_from(msg)
        tracer = msg2._trace
        trace_reports = tracer.trace_reports
        assert len(trace_reports) == 1

        trace_report2 = TraceReport(
            msg_id=msg2._id,
            thread_id=msg2._thread_id,
            traced_type=msg2._type,
            timestamp="123456789.123456",
            str_time="2019-01-01 12:34:56.7",
            handler="function.END",
            ellapsed_milli=72,
            outcome="A OK! ...",
        )
        msg2.add_trace_report(trace_report2)
        tracer = msg2._trace
        trace_reports = tracer.trace_reports
        assert len(trace_reports) == 2
        msg_trace_report = trace_reports[1]
        assert msg_trace_report.msg_id == msg2._id
        assert msg_trace_report.thread_id == msg2._thread_id
        assert msg_trace_report.handler == trace_report2.handler
        assert msg_trace_report.ellapsed_milli == trace_report2.ellapsed_milli
        assert msg_trace_report.traced_type == msg2._type
        assert msg_trace_report.outcome == trace_report2.outcome

        print("tracer:", tracer.serialize())
