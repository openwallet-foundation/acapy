from ..trace_decorator import TraceDecorator, TraceReport, MessageIdElement

from unittest import TestCase


class TestTraceDecorator(TestCase):

    target_api = "http://example.com/api/trace/"
    full_thread_api = False
    target_msg = "message"
    full_thread_msg = True

    msg_id = {"id": "msg-001", "sender_order":1}
    thread_id = {"id": "tid-001", "sender_order": 1}
    handler = "agent name"
    ellapsed_milli = 27
    traced_type = "msg-001/my_type"
    timestamp = "2018-03-27 18:23:45.123Z"
    outcome = "OK ..."


    def test_init_api(self):

        decorator = TraceDecorator(
            target=self.target_api,
            full_thread=self.full_thread_api,
        )
        assert decorator.target == self.target_api
        assert decorator.full_thread == self.full_thread_api

    def test_init_message(self):

        x_msg_id = MessageIdElement(
            id=self.msg_id["id"],
            sender_order=self.msg_id["sender_order"],
        )
        x_thread_id = MessageIdElement(
            id=self.thread_id["id"],
            sender_order=self.thread_id["sender_order"],
        )
        x_trace_report = TraceReport(
            msg_id=x_msg_id,
            thread_id=x_thread_id,
            handler=self.handler,
            ellapsed_milli=self.ellapsed_milli,
            traced_type=self.traced_type,
            timestamp=self.timestamp,
            outcome=self.outcome,
        )

        decorator = TraceDecorator(
            target=self.target_msg,
            full_thread=self.full_thread_msg,
            trace_reports=[x_trace_report,],
        )
        assert decorator.target == self.target_msg
        assert decorator.full_thread == self.full_thread_msg
        assert len(decorator.trace_reports) == 1
        trace_report = decorator.trace_reports[0]
        assert trace_report.msg_id.id == self.msg_id["id"]
        assert trace_report.msg_id.sender_order == self.msg_id["sender_order"]
        assert trace_report.thread_id.id == self.thread_id["id"]
        assert trace_report.thread_id.sender_order == self.thread_id["sender_order"]
        assert trace_report.handler == self.handler
        assert trace_report.ellapsed_milli == self.ellapsed_milli
        assert trace_report.traced_type == self.traced_type
        assert trace_report.timestamp == self.timestamp
        assert trace_report.outcome == self.outcome

    def test_serialize_load(self):

        x_msg_id = MessageIdElement(
            id=self.msg_id["id"],
            sender_order=self.msg_id["sender_order"],
        )
        x_thread_id = MessageIdElement(
            id=self.thread_id["id"],
            sender_order=self.thread_id["sender_order"],
        )
        x_trace_report = TraceReport(
            msg_id=x_msg_id,
            thread_id=x_thread_id,
            handler=self.handler,
            ellapsed_milli=self.ellapsed_milli,
            traced_type=self.traced_type,
            timestamp=self.timestamp,
            outcome=self.outcome,
        )

        decorator = TraceDecorator(
            target=self.target_msg,
            full_thread=self.full_thread_msg,
            trace_reports=[x_trace_report,],
        )

        dumped = decorator.serialize()
        print(dumped)
        loaded = TraceDecorator.deserialize(dumped)

        assert loaded.target == decorator.target
        assert loaded.full_thread == decorator.full_thread
        assert len(loaded.trace_reports) == 1
        trace_report = loaded.trace_reports[0]
        assert trace_report.msg_id.id == x_trace_report.msg_id.id
        assert trace_report.msg_id.sender_order == x_trace_report.msg_id.sender_order
        assert trace_report.thread_id.id == x_trace_report.thread_id.id
        assert trace_report.thread_id.sender_order == x_trace_report.thread_id.sender_order
        assert trace_report.handler == x_trace_report.handler
        assert trace_report.ellapsed_milli == x_trace_report.ellapsed_milli
        assert trace_report.traced_type == x_trace_report.traced_type
        assert trace_report.timestamp == x_trace_report.timestamp
        assert trace_report.outcome == x_trace_report.outcome
