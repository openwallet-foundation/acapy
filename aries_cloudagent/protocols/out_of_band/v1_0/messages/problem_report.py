"""Represents an OOB connection reuse problem report message."""

from enum import Enum
from marshmallow import EXCLUDE, fields, validate, pre_dump, ValidationError

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import PROBLEM_REPORT, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers"
    ".problem_report_handler.OOBProblemReportMessageHandler"
)


class ProblemReportReason(str, Enum):
    """Supported reason codes."""

    EXISTING_CONNECTION_DOES_NOT_EXISTS = "existing_connection_does_not_exists"
    EXISTING_CONNECTION_NOT_ACTIVE = "existing_connection_not_active"


class ProblemReport(AgentMessage):
    """Base class representing an OOB connection reuse problem report message."""

    class Meta:
        """OOB connection reuse problem report metadata."""

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
        super().__init__(**kwargs)
        self.explain = explain
        self.problem_code = problem_code


class ProblemReportSchema(AgentMessageSchema):
    """Schema for ProblemReport base class."""

    class Meta:
        """Metadata for problem report schema."""

        model_class = ProblemReport
        unknown = EXCLUDE

    explain = fields.Str(
        required=False,
        description="Localized error explanation",
        example=ProblemReportReason.EXISTING_CONNECTION_DOES_NOT_EXISTS.value,
    )
    problem_code = fields.Str(
        data_key="problem-code",
        required=False,
        description="Standard error identifier",
        validate=validate.OneOf(
            choices=[prr.value for prr in ProblemReportReason],
            error="Value {input} must be one of {choices}.",
        ),
        example=ProblemReportReason.EXISTING_CONNECTION_DOES_NOT_EXISTS.value,
    )

    @pre_dump
    def check_thread_deco(self, obj, **kwargs):
        """Thread decorator, and its thid and pthid, are mandatory."""
        if not obj._decorators.to_dict().get("~thread", {}).keys() >= {"thid", "pthid"}:
            raise ValidationError("Missing required field(s) in thread decorator")
        return obj
