from ..trace_decorator import TraceDecorator, TraceReport, TRACE_MESSAGE_TARGET

from unittest import TestCase


class TestTraceDecorator(TestCase):
    target_api = "http://example.com/api/trace/"
    full_thread_api = False
    target_msg = TRACE_MESSAGE_TARGET
    full_thread_msg = True

    msg_id = "msg-001"
    thread_id = "thid-001"
    traced_type = "msg-001/my_type"
    timestamp = "123456789.123456"
    str_time = "2018-03-27 18:23:45.123Z"
    handler = "agent name"
    ellapsed_milli = 27
    outcome = "OK ..."

    def test_init_api(self):
        decorator = TraceDecorator(
            target=self.target_api,
            full_thread=self.full_thread_api,
        )
        assert decorator.target == self.target_api
        assert decorator.full_thread == self.full_thread_api

    def test_init_message(self):
        x_msg_id = self.msg_id
        x_thread_id = self.thread_id
        x_trace_report = TraceReport(
            msg_id=x_msg_id,
            thread_id=x_thread_id,
            traced_type=self.traced_type,
            timestamp=self.timestamp,
            str_time=self.str_time,
            handler=self.handler,
            ellapsed_milli=self.ellapsed_milli,
            outcome=self.outcome,
        )

        decorator = TraceDecorator(
            target=self.target_msg,
            full_thread=self.full_thread_msg,
            trace_reports=[
                x_trace_report,
            ],
        )
        assert decorator.target == self.target_msg
        assert decorator.full_thread == self.full_thread_msg
        assert len(decorator.trace_reports) == 1
        trace_report = decorator.trace_reports[0]
        assert trace_report.msg_id == self.msg_id
        assert trace_report.thread_id == self.thread_id
        assert trace_report.traced_type == self.traced_type
        assert trace_report.timestamp == self.timestamp
        assert trace_report.str_time == self.str_time
        assert trace_report.handler == self.handler
        assert trace_report.ellapsed_milli == self.ellapsed_milli
        assert trace_report.outcome == self.outcome

    def test_serialize_load(self):
        x_msg_id = self.msg_id
        x_thread_id = self.thread_id
        x_trace_report = TraceReport(
            msg_id=x_msg_id,
            thread_id=x_thread_id,
            traced_type=self.traced_type,
            timestamp=self.timestamp,
            str_time=self.str_time,
            handler=self.handler,
            ellapsed_milli=self.ellapsed_milli,
            outcome=self.outcome,
        )

        decorator = TraceDecorator(
            target=self.target_msg,
            full_thread=self.full_thread_msg,
            trace_reports=[
                x_trace_report,
                x_trace_report,
            ],
        )

        dumped = decorator.serialize()
        loaded = TraceDecorator.deserialize(dumped)

        assert loaded.target == decorator.target
        assert loaded.full_thread == decorator.full_thread
        assert len(loaded.trace_reports) == 2
        trace_report = loaded.trace_reports[0]
        assert trace_report.msg_id == x_trace_report.msg_id
        assert trace_report.thread_id == x_trace_report.thread_id
        assert trace_report.traced_type == x_trace_report.traced_type
        assert trace_report.timestamp == x_trace_report.timestamp
        assert trace_report.str_time == x_trace_report.str_time
        assert trace_report.handler == x_trace_report.handler
        assert trace_report.ellapsed_milli == x_trace_report.ellapsed_milli
        assert trace_report.outcome == x_trace_report.outcome

    def test_trace_reports(self):
        decorator = TraceDecorator(
            target=self.target_msg,
            full_thread=self.full_thread_msg,
        )
        assert len(decorator.trace_reports) == 0

        x_msg_id = self.msg_id
        x_thread_id = self.thread_id
        x_trace_report = TraceReport(
            msg_id=x_msg_id,
            thread_id=x_thread_id,
            traced_type=self.traced_type,
            timestamp=self.timestamp,
            str_time=self.str_time,
            handler=self.handler,
            ellapsed_milli=self.ellapsed_milli,
            outcome=self.outcome,
        )
        decorator.append_trace_report(x_trace_report)
        assert len(decorator.trace_reports) == 1

        y_msg_id = self.msg_id
        y_thread_id = self.thread_id
        y_trace_report = TraceReport(
            msg_id=y_msg_id,
            thread_id=y_thread_id,
            traced_type=self.traced_type,
            timestamp=self.timestamp,
            str_time=self.str_time,
            handler=self.handler,
            ellapsed_milli=self.ellapsed_milli,
            outcome=self.outcome,
        )
        decorator.append_trace_report(y_trace_report)
        assert len(decorator.trace_reports) == 2
        trace_report = decorator.trace_reports[1]
        assert trace_report.msg_id == x_trace_report.msg_id
        assert trace_report.thread_id == x_trace_report.thread_id

        z_msg_id = self.msg_id + "-z"
        z_thread_id = self.thread_id + "-z"
        z_trace_report = TraceReport(
            msg_id=z_msg_id,
            thread_id=z_thread_id,
            traced_type=self.traced_type,
            timestamp=self.timestamp,
            str_time=self.str_time,
            handler=self.handler,
            ellapsed_milli=self.ellapsed_milli,
            outcome=self.outcome,
        )
        decorator.append_trace_report(z_trace_report)
        assert len(decorator.trace_reports) == 3
        trace_report = decorator.trace_reports[2]
        assert trace_report.msg_id == self.msg_id + "-z"
        assert trace_report.thread_id == self.thread_id + "-z"
