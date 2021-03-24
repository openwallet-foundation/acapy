import json
import requests

from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ...protocols.out_of_band.v1_0.messages.invitation import InvitationMessage
from ...protocols.issue_credential.v1_0.models.credential_exchange import (
    V10CredentialExchange,
)
from ...transport.inbound.message import InboundMessage
from ...transport.outbound.message import OutboundMessage
from ...messaging.agent_message import AgentMessage

from ...messaging.decorators.trace_decorator import TraceDecorator, TRACE_MESSAGE_TARGET
from ...protocols.trustping.v1_0.messages.ping import Ping

from .. import tracing as test_module


class TestTracing(AsyncTestCase):
    test_did = "55GkHamhTU1ZbTbV2ab9DE"

    def test_get_timer(self):
        assert test_module.get_timer() > 0.0

    def test_tracing_enabled(self):
        invi = InvitationMessage(
            comment="no comment", label="cable guy", services=[TestTracing.test_did]
        )
        assert not test_module.tracing_enabled({}, invi)
        invi._trace = TraceDecorator(target="message")
        assert test_module.tracing_enabled({}, invi)

        cred_ex_rec = V10CredentialExchange()
        assert not test_module.tracing_enabled({}, cred_ex_rec)
        cred_ex_rec = V10CredentialExchange(trace=True)
        assert test_module.tracing_enabled({}, cred_ex_rec)

        dict_message = {"no": "trace"}
        assert not test_module.tracing_enabled({}, dict_message)
        dict_message["trace"] = True
        assert test_module.tracing_enabled({}, dict_message)
        dict_message["~trace"] = dict_message.pop("trace")
        assert test_module.tracing_enabled({}, dict_message)

        str_message = json.dumps({"item": "I can't draw but I can trace"})
        assert not test_module.tracing_enabled({}, str_message)
        str_message = json.dumps(
            "Finding a ~trace as a false positive represents an outlier"
        )
        assert test_module.tracing_enabled({}, str_message)
        str_message = json.dumps({"trace": False, "content": "sample"})
        assert not test_module.tracing_enabled({}, str_message)
        str_message = json.dumps({"trace": True, "content": "sample"})
        assert test_module.tracing_enabled({}, str_message)

        invi._trace = None
        outbound_message = OutboundMessage(payload=invi)
        assert not test_module.tracing_enabled({}, outbound_message)
        invi._trace = TraceDecorator(target="message")
        assert test_module.tracing_enabled({}, outbound_message)
        dict_message = {"no": "trace"}
        outbound_message = OutboundMessage(payload=dict_message)
        assert not test_module.tracing_enabled({}, outbound_message)
        dict_message["trace"] = True
        assert test_module.tracing_enabled({}, outbound_message)
        dict_message["~trace"] = dict_message.pop("trace")
        assert test_module.tracing_enabled({}, outbound_message)
        outbound_message = OutboundMessage(payload="This text does not have the T word")
        assert not test_module.tracing_enabled({}, outbound_message)
        outbound_message = OutboundMessage(payload=json.dumps({"trace": True}))
        assert test_module.tracing_enabled({}, outbound_message)

    def test_decode_inbound_message(self):
        invi = InvitationMessage(
            comment="no comment", label="cable guy", services=[TestTracing.test_did]
        )
        message = OutboundMessage(payload=invi)
        assert invi == test_module.decode_inbound_message(message)

        dict_message = {"a": 1, "b": 2}
        message = OutboundMessage(payload=dict_message)
        assert dict_message == test_module.decode_inbound_message(message)
        assert dict_message == test_module.decode_inbound_message(dict_message)

        str_message = json.dumps(dict_message)
        message = OutboundMessage(payload=str_message)
        assert dict_message == test_module.decode_inbound_message(message)
        assert dict_message == test_module.decode_inbound_message(str_message)

        x_message = "'bad json'"
        message = OutboundMessage(payload=x_message)
        assert message == test_module.decode_inbound_message(message)
        assert x_message == test_module.decode_inbound_message(x_message)

    def test_log_event(self):
        ping = Ping()
        ping._thread = {"thid": "dummy_thread_id_12345"}
        context = {
            "trace.enabled": True,
            "trace.target": "log",
            "trace.tag": "acapy.trace",
        }
        ret = test_module.trace_event(
            context,
            ping,
            handler="message_handler",
            perf_counter=None,
            outcome="processed Start",
        )
        test_module.trace_event(
            context,
            ping,
            perf_counter=ret,
            outcome="processed OK",
        )
        context["trace.label"] = "trace-label"
        test_module.trace_event(context, ping)
        ping = Ping()
        test_module.trace_event(context, ping)
        test_module.trace_event(
            context,
            InboundMessage(session_id="1234", payload="Hello world", receipt=None),
        )
        test_module.trace_event(
            context, OutboundMessage(reply_thread_id="5678", payload="Hello world")
        )
        test_module.trace_event(
            context, {"@type": "sample-type", "~thread": {"thid": "abcd"}}
        )
        test_module.trace_event(context, {"~thread": {"thid": "1234"}})
        test_module.trace_event(context, {"thread_id": "1234"})
        test_module.trace_event(context, {"@id": "12345"})
        test_module.trace_event(context, V10CredentialExchange())
        test_module.trace_event(context, [])

    async def test_post_event(self):
        message = Ping()
        message._thread = {"thid": "dummy_thread_id_12345"}
        context = {
            "trace.enabled": True,
            "trace.target": "http://fluentd:8080/",
            "trace.tag": "acapy.trace",
        }
        test_module.trace_event(
            context,
            message,
            handler="message_handler",
            perf_counter=None,
            outcome="processed OK",
        )

    async def test_post_event_with_error(self):
        message = Ping()
        message._thread = {"thid": "dummy_thread_id_12345"}
        context = {
            "trace.enabled": True,
            "trace.target": "http://fluentd-dummy:8080/",
            "trace.tag": "acapy.trace",
        }
        try:
            test_module.trace_event(
                context,
                message,
                handler="message_handler",
                perf_counter=None,
                outcome="processed OK",
                raise_errors=True,
            )
            assert False
        except requests.exceptions.ConnectionError as e:
            pass

    def test_post_msg_decorator_event(self):
        message = Ping()
        message._thread = {"thid": "dummy_thread_id_12345"}
        assert message._trace is None
        context = {
            "trace.enabled": True,
            "trace.target": TRACE_MESSAGE_TARGET,
            "trace.tag": "acapy.trace",
        }
        test_module.trace_event(
            context,
            message,
            handler="message_handler",
            perf_counter=None,
            outcome="processed OK",
        )
        trace = message._trace
        assert trace is not None
        assert trace.target == TRACE_MESSAGE_TARGET
        assert trace.full_thread == True
        trace_reports = trace.trace_reports
        assert len(trace_reports) == 1
        trace_report = trace_reports[0]
        assert trace_report.thread_id == message._thread.thid
