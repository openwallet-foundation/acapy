from asynctest import mock, TestCase

import requests

from ...transport.inbound.message import InboundMessage
from ...transport.outbound.message import OutboundMessage
from ...messaging.agent_message import AgentMessage

from ...messaging.decorators.trace_decorator import TRACE_MESSAGE_TARGET
from ...protocols.trustping.v1_0.messages.ping import Ping

from .. import tracing as test_module


class TestTracing(TestCase):
    def test_log_event(self):
        message = Ping()
        message._thread = {"thid": "dummy_thread_id_12345"}
        context = {
            "trace.enabled": True,
            "trace.target": "log",
            "trace.tag": "acapy.trace",
        }
        ret = test_module.trace_event(
            context,
            message,
            handler="message_handler",
            perf_counter=None,
            outcome="processed Start",
        )
        test_module.trace_event(
            context,
            message,
            handler="message_handler",
            perf_counter=ret,
            outcome="processed OK",
        )

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
