"""Represents a connection problem report message."""

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import PROBLEM_REPORT

HANDLER_CLASS = (
    "indy_catalyst_agent.messaging.problem_report.handler.ProblemReportHandler"
)


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

    explain = fields.Str(required=False)
    problem_code = fields.Str(data_key="problem-code", required=False)
