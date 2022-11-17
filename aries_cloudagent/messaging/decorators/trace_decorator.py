"""
A message decorator for trace events.

A trace decorator identifies a responsibility on the processor
to record information on message processing events.
"""

from typing import Sequence

from marshmallow import EXCLUDE, fields

from ..models.base import BaseModel, BaseModelSchema
from ..valid import UUIDFour


TRACE_MESSAGE_TARGET = "message"
TRACE_LOG_TARGET = "log"


class TraceReport(BaseModel):
    """Class representing a Trace Report."""

    class Meta:
        """TraceReport metadata."""

        schema_class = "TraceReport"

    def __init__(
        self,
        *,
        msg_id: str = None,
        thread_id: str = None,
        traced_type: str = None,
        timestamp: str = None,
        str_time: str = None,
        handler: str = None,
        ellapsed_milli: int = None,
        outcome: str = None,
    ):
        """
        Initialize a TraceReport instance.

        Args:
            msg_id: ...
            thread_id: ...
            traced_type: ...
            timestamp: ...
            str_time: ...
            handler: ...
            ellapsed_milli: ...
            outcome: ...
        """
        super().__init__()
        self._msg_id = msg_id
        self._thread_id = thread_id
        self._traced_type = traced_type
        self._timestamp = timestamp
        self._str_time = str_time
        self._handler = handler
        self._ellapsed_milli = ellapsed_milli
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
    def str_time(self):
        """
        Accessor for str_time.

        Returns:
            Formatted representation of the sender timestamp

        """
        return self._str_time

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


class TraceReportSchema(BaseModelSchema):
    """Trace report schema."""

    class Meta:
        """TraceReportSchema metadata."""

        model_class = TraceReport
        unknown = EXCLUDE

    msg_id = fields.Str(
        required=True,
        allow_none=False,
        description="Message Id",
        example=UUIDFour.EXAMPLE,  # typically a UUID4 but not necessarily
    )
    thread_id = fields.Str(
        required=True,
        allow_none=False,
        description="Message Id",
        example=UUIDFour.EXAMPLE,  # typically a UUID4 but not necessarily
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
        example="123456789.123456",
    )
    str_time = fields.Str(
        required=True,
        allow_none=False,
        description="Formatted timestamp of traced event",
        example="2018-03-27 18:23:45.123Z",
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
        strict=True,
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
        unknown = EXCLUDE

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
        description=("The set of reports collected so far for this message or thread"),
    )
