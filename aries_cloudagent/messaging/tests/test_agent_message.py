from asynctest import TestCase as AsyncTestCase

from marshmallow import EXCLUDE, fields

from ...core.in_memory import InMemoryProfile
from ...protocols.didcomm_prefix import DIDCommPrefix
from ...wallet.key_type import ED25519

from ..agent_message import AgentMessage, AgentMessageSchema
from ..decorators.signature_decorator import SignatureDecorator
from ..decorators.trace_decorator import TraceReport, TRACE_LOG_TARGET
from ..models.base import BaseModelError


class SignedAgentMessage(AgentMessage):
    """Signed agent message tests"""

    class Meta:
        """Meta data"""

        handler_class = None
        schema_class = "SignedAgentMessageSchema"
        message_type = "signed-agent-message"

    def __init__(self, value: str = None, **kwargs):
        super().__init__(**kwargs)
        self.value = value


class SignedAgentMessageSchema(AgentMessageSchema):
    """Utility schema"""

    class Meta:
        model_class = SignedAgentMessage
        signed_fields = ("value",)
        unknown = EXCLUDE

    value = fields.Str(required=True)


class BasicAgentMessage(AgentMessage):
    """Simple agent message implementation"""

    class Meta:
        """Meta data"""

        schema_class = AgentMessageSchema
        message_type = "basic-message"


class TestAgentMessage(AsyncTestCase):
    """Tests agent message."""

    def test_init(self):
        """Tests init class"""

        class BadImplementationClass(AgentMessage):
            """Test utility class."""

        message = SignedAgentMessage()
        message._id = "12345"

        with self.assertRaises(TypeError) as context:
            BadImplementationClass()  # pylint: disable=E0110
        assert "Can't instantiate abstract" in str(context.exception)

        BadImplementationClass.Meta.schema_class = "AgentMessageSchema"
        with self.assertRaises(TypeError) as context:
            BadImplementationClass()  # pylint: disable=E0110
        assert "Can't instantiate abstract" in str(context.exception)

    async def test_field_signature(self):
        session = InMemoryProfile.test_session()
        wallet = session.wallet
        key_info = await wallet.create_signing_key(ED25519)

        msg = SignedAgentMessage()
        msg.value = None
        with self.assertRaises(BaseModelError) as context:
            await msg.sign_field("value", key_info.verkey, wallet)
        assert "field has no value for signature" in str(context.exception)

        msg.value = "Test value"
        with self.assertRaises(BaseModelError) as context:
            msg.serialize()
        assert "Missing signature for field" in str(context.exception)

        await msg.sign_field("value", key_info.verkey, wallet)
        sig = msg.get_signature("value")
        assert isinstance(sig, SignatureDecorator)

        assert await sig.verify(wallet)
        assert await msg.verify_signed_field("value", wallet) == key_info.verkey
        assert await msg.verify_signatures(wallet)

        with self.assertRaises(BaseModelError) as context:
            await msg.verify_signed_field("value", wallet, "bogus-verkey")
        assert "Signer verkey of signature does not match" in str(context.exception)

        serial = msg.serialize()
        assert "value~sig" in serial and "value" not in serial

        (_, timestamp) = msg._decorators.field("value")["sig"].decode()
        tamper_deco = await SignatureDecorator.create("tamper", key_info.verkey, wallet)
        msg._decorators.field("value")["sig"].sig_data = tamper_deco.sig_data
        with self.assertRaises(BaseModelError) as context:
            await msg.verify_signed_field("value", wallet)
        assert "Field signature verification failed" in str(context.exception)
        assert not await msg.verify_signatures(wallet)

        msg.value = "Test value"
        msg._decorators.field("value").pop("sig")
        with self.assertRaises(BaseModelError) as context:
            await msg.verify_signed_field("value", wallet)
        assert "Missing field signature" in str(context.exception)

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

        msg.assign_thread_id(None, None)
        assert not msg._thread

    async def test_add_tracing(self):
        msg = BasicAgentMessage()
        msg.add_trace_decorator()
        tracer = msg._trace
        assert tracer.target == TRACE_LOG_TARGET
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

        msg3 = BasicAgentMessage()
        msg.add_trace_decorator()
        assert msg._trace


class TestAgentMessageSchema(AsyncTestCase):
    """Tests agent message schema."""

    def test_init_x(self):
        """Tests init class"""

        class BadImplementationClass(AgentMessageSchema):
            """Test utility class."""

        with self.assertRaises(TypeError) as context:
            BadImplementationClass()
        assert "Can't instantiate abstract" in str(context.exception)

    def test_extract_decorators_x(self):
        for serial in [
            {
                "@type": "signed-agent-message",
                "@id": "030ac9e6-0d60-49d3-a8c6-e7ce0be8df5a",
                "value": "Test value",
            },
            {
                "@type": "signed-agent-message",
                "@id": "030ac9e6-0d60-49d3-a8c6-e7ce0be8df5a",
                "value": "Test value",
                "value~sig": {
                    "@type": DIDCommPrefix.qualify_current(
                        "signature/1.0/ed25519Sha512_single"
                    ),
                    "signature": (
                        "-OKdiRRQu-xbVGICg1J6KV_6nXLLzYRXr8BZSXzoXimytBl"
                        "O8ULY7Nl1lQPqahc-XQPHiBSVraLM8XN_sCzdCg=="
                    ),
                    "sig_data": "AAAAAF8bIV4iVGVzdCB2YWx1ZSI=",
                    "signer": "7VA3CaF9jaTuRN2SGmekANoja6Js4U51kfRSbpZAfdhy",
                },
            },
            {
                "@type": "signed-agent-message",
                "@id": "030ac9e6-0d60-49d3-a8c6-e7ce0be8df5a",
                "superfluous~sig": {
                    "@type": DIDCommPrefix.qualify_current(
                        "signature/1.0/ed25519Sha512_single"
                    ),
                    "signature": (
                        "-OKdiRRQu-xbVGICg1J6KV_6nXLLzYRXr8BZSXzoXimytBl"
                        "O8ULY7Nl1lQPqahc-XQPHiBSVraLM8XN_sCzdCg=="
                    ),
                    "sig_data": "AAAAAF8bIV4iVGVzdCB2YWx1ZSI=",
                    "signer": "7VA3CaF9jaTuRN2SGmekANoja6Js4U51kfRSbpZAfdhy",
                },
            },
        ]:
            with self.assertRaises(BaseModelError) as context:
                SignedAgentMessage.deserialize(serial)

    def test_serde(self):
        serial = {
            "@type": "signed-agent-message",
            "@id": "030ac9e6-0d60-49d3-a8c6-e7ce0be8df5a",
            "value~sig": {
                "@type": DIDCommPrefix.qualify_current(
                    "signature/1.0/ed25519Sha512_single"
                ),
                "signature": (
                    "-OKdiRRQu-xbVGICg1J6KV_6nXLLzYRXr8BZSXzoXimytBl"
                    "O8ULY7Nl1lQPqahc-XQPHiBSVraLM8XN_sCzdCg=="
                ),
                "sig_data": "AAAAAF8bIV4iVGVzdCB2YWx1ZSI=",
                "signer": "7VA3CaF9jaTuRN2SGmekANoja6Js4U51kfRSbpZAfdhy",
            },
        }
        result = SignedAgentMessage.deserialize(serial)
        result.serialize()
