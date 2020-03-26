from asynctest import mock, TestCase

import requests

from ...transport.inbound.message import InboundMessage
from ...transport.outbound.message import OutboundMessage
from ...messaging.agent_message import AgentMessage
from ...protocols.trustping.messages.ping import Ping

from .. import tracing as test_module


class TestTracing(TestCase):
    def test_log_event(self):
        message = Ping()
        message._thread = {"thid": "dummy_thread_id_12345"}
        context = {
            "trace.enabled": True,
            "trace.target": "log",
            "trace.tag": "acapy.trace"
        }
        test_module.trace_event(
            context, 
            message, 
            handler="message_handler",
            ellapsed_milli=27,
            outcome="processed OK"
        )

    async def test_post_event(self):
        message = Ping()
        message._thread = {"thid": "dummy_thread_id_12345"}
        context = {
            "trace.enabled": True,
            "trace.target": "http://fluentd:8080/",
            "trace.tag": "acapy.trace"
        }
        test_module.trace_event(
            context, 
            message, 
            handler="message_handler",
            ellapsed_milli=27,
            outcome="processed OK",
        )

        try:
            test_module.trace_event(
                context, 
                message, 
                handler="message_handler",
                ellapsed_milli=27,
                outcome="processed OK",
                raise_errors=True,
            )
            assert False
        except requests.exceptions.ConnectionError as e:
            pass
