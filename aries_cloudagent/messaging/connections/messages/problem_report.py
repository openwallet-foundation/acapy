"""Represents a connection problem report message."""

from enum import Enum
from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import PROBLEM_REPORT

HANDLER_CLASS = "aries_cloudagent.messaging.problem_report.handler.ProblemReportHandler"


class ProblemReportReason(Enum):
    """Supported reason codes."""

    REQUEST_NOT_ACCEPTED = "request_not_accepted"
    RESPONSE_FOR_UNKNOWN_REQUEST = "response_for_unknown_request"


class ProblemReport(AgentMessage):
    """Base class representing a connection problem report message."""

    class Meta:
        """Connection problem report metadata."""

        handler_class = HANDLER_CLASS
        message_type = PROBLEM_REPORT
        schema_class = "ProblemReportSchema"

    def __init__(self, *, problem_code: str = None, explain: str = None, **kwargs):
        """
        Initialize a ProblemReport message instance.

        Args:
            explain: The localized error explanation
            problem_code: The standard error identifier
        """
        super(ProblemReport, self).__init__(**kwargs)
        self.explain = explain
        self.problem_code = problem_code


class ProblemReportSchema(AgentMessageSchema):
    """Schema for ProblemReport base class."""

    class Meta:
        """Metadata for problem report schema."""

        model_class = ProblemReport

    explain = fields.Str(required=False)
    problem_code = fields.Str(data_key="problem-code", required=False)
