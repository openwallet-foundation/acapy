"""
A message decorator for trace events.

A trace decorator identifies a responsibility on the processor
to record information on message processing events.
"""

from typing import Sequence

from marshmallow import fields

from ..models.base import BaseModel, BaseModelSchema
from ..valid import UUIDFour


TRACE_MESSAGE_TARGET = "message"


class MessageIdElement(BaseModel):
    """Class representing a message or trace id within a report."""

    class Meta:
        """MessageIdElement metadata."""

        schema_class = "MessageIdElement"

    def __init__(
        self,
        *,
        id: str = None,
        sender_order: int,
    ):
        """
        Initialize a MessageIdElement instance.

        Args:
            id: ...
            sender_order: ...
        """
        super(MessageIdElement, self).__init__()
        self._id = id
        self._sender_order = sender_order

    @property
    def id(self):
        """
        Accessor for id.

        Returns:
            The id

        """
        return self._id

    @property
    def sender_order(self):
        """
        Accessor for sender_order.

        Returns:
            The sender orger

        """
        return self._sender_order


class TraceReport(BaseModel):
    """Class representing a Trace Report."""

    class Meta:
        """TraceReport metadata."""

        schema_class = "TraceReport"

    def __init__(
        self,
        *,
        msg_id: MessageIdElement = None,
        thread_id: MessageIdElement = None,
        handler: str = None,
        ellapsed_milli: int = None,
        traced_type: str = None,
        timestamp: str = None,
        outcome: str = None,
    ):
        """
        Initialize a TraceReport instance.

        Args:
            msg_id: ...
            thread_id: ...
            handler: ...
            ellapsed_milli: ...
            traced_type: ...
            timestamp: ...
            outcome: ...
        """
        super(TraceReport, self).__init__()
        self._msg_id = msg_id
        self._thread_id = thread_id
        self._handler = handler
        self._ellapsed_milli = ellapsed_milli
        self._traced_type = traced_type
        self._timestamp = timestamp
        self._outcome = outcome

    @property
    def msg_id(self):
        """
        Accessor for msg_id.

        Returns:
            The msg_id

        """
        return self._msg_id

    @property
    def thread_id(self):
        """
        Accessor for thread_id.

        Returns:
            The thread_id

        """
        return self._thread_id

    @property
    def handler(self):
        """
        Accessor for handler.

        Returns:
            The sender handler

        """
        return self._handler

    @property
    def ellapsed_milli(self):
        """
        Accessor for ellapsed_milli.

        Returns:
            The sender ellapsed_milli

        """
        return self._ellapsed_milli

    @property
    def traced_type(self):
        """
        Accessor for traced_type.

        Returns:
            The sender traced_type

        """
        return self._traced_type

    @property
    def timestamp(self):
        """
        Accessor for timestamp.

        Returns:
            The sender timestamp

        """
        return self._timestamp

    @property
    def outcome(self):
        """
        Accessor for outcome.

        Returns:
            The sender outcome

        """
        return self._outcome


class TraceDecorator(BaseModel):
    """Class representing trace decorator."""

    class Meta:
        """TraceDecorator metadata."""

        schema_class = "TraceDecoratorSchema"

    def __init__(
        self,
        *,
        target: str = None,
        full_thread: bool = True,
        trace_reports: Sequence = None,
    ):
        """
        Initialize a TraceDecorator instance.

        Args:
            target: The "target" can refer to a url (as above) or the term
                    "message", which is a request to append trace information
                    to the message itself.
            full_thread: An optional flag to indicate tracing should be included
                    on all subsequent messages in the thread (on by default).
            trace_reports: Trace reports contain information about a message
                    processing at a specific point in time, along with a timestamp.
                    Trace reports can be used to identify steps in the processing
                    of a message or thread, and support troubleshooting and
                    performance issues.
        """
        super(TraceDecorator, self).__init__()
        self._target = target
        self._full_thread = full_thread
        self._trace_reports = trace_reports and list(trace_reports) or None

    @property
    def target(self):
        """
        Accessor for trace target.

        Returns:
            The target for tracing messages

        """
        return self._target

    @property
    def full_thread(self):
        """
        Accessor for full_thread flag.

        Returns:
            The full_thread flag

        """
        return self._full_thread

    @property
    def trace_reports(self):
        """
        Set of trace reports for this message.

        Returns:
            The trace reports that have been logged on this message/thread
            so far.  (Only for target="message".)

        """
        if not self._trace_reports:
            return []
        return self._trace_reports

    def append_trace_report(self, trace_report: TraceReport):
        """Append a trace report to this decorator."""
        if not self._trace_reports:
            self._trace_reports = []
        self._trace_reports.append(trace_report)

    def next_msg_sender_order(self, msg_id: str):
        """Get next sender order for given message id."""
        sender_order = 1
        if self._trace_reports:
            for trace_report in self._trace_reports:
                if (trace_report.msg_id
                        and trace_report.msg_id.id == msg_id
                        and trace_report.msg_id.sender_order >= sender_order):
                    sender_order = trace_report.msg_id.sender_order + 1
        return sender_order

    def next_thread_sender_order(self, thread_id: str):
        """Get next sender order for given thread id."""
        sender_order = 1
        if self._trace_reports:
            for trace_report in self._trace_reports:
                if (trace_report.thread_id
                        and trace_report.thread_id.id == thread_id
                        and trace_report.thread_id.sender_order >= sender_order):
                    sender_order = trace_report.thread_id.sender_order + 1
        return sender_order


class MessageIdSchema(BaseModelSchema):
    """Message Id schema."""

    class Meta:
        """MessageIdSchema metadata."""

        model_class = MessageIdElement

    id = fields.Str(
        required=True,
        allow_none=False,
        description="Message Id",
        example=UUIDFour.EXAMPLE,  # typically a UUID4 but not necessarily
    )
    sender_order = fields.Int(
        required=False,
        allow_none=True,
        description="Message sender order",
        example=27,
    )


class TraceReportSchema(BaseModelSchema):
    """Trace report schema."""

    class Meta:
        """TraceReportSchema metadata."""

        model_class = TraceReport

    msg_id = fields.Nested(
        MessageIdSchema,
        required=True,
        allow_none=False,
        description="Message Id",
    )
    thread_id = fields.Nested(
        MessageIdSchema,
        required=False,
        allow_none=True,
        description="Thread Id",
    )
    handler = fields.Str(
        required=False,
        allow_none=True,
        description="Description of the message handler",
        example="TODO",
    )
    ellapsed_milli = fields.Int(
        required=False,
        allow_none=True,
        description="Elapsed milliseconds processing time",
        example=27,
    )
    traced_type = fields.Str(
        required=False,
        allow_none=True,
        description="Type of traced message",
        example="TODO",
    )
    timestamp = fields.Str(
        required=True,
        allow_none=False,
        description="Timestamp of traced event",
        example="2018-03-27 18:23:45.123Z",
    )
    outcome = fields.Str(
        required=False,
        allow_none=True,
        description="Outcome description",
        example="TODO",
    )


class TraceDecoratorSchema(BaseModelSchema):
    """Trace decorator schema used in serialization/deserialization."""

    class Meta:
        """TraceDecoratorSchema metadata."""

        model_class = TraceDecorator

    target = fields.Str(
        required=True,
        allow_none=False,
        description="Trace report target",
        example="'http://example.com/tracer', or 'message'",
    )
    full_thread = fields.Boolean(
        required=False,
        allow_none=True,
        description="Parent thread identifier",
        example="True",
    )
    trace_reports = fields.List(
        fields.Nested(TraceReportSchema),
        required=False,
        allow_none=True,
        description=(
            "The set of reports collected so far for this message or thread"
        ),
    )
