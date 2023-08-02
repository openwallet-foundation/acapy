"""DID Exchange problem report and reasons."""

from enum import Enum
from typing import Optional
from marshmallow import EXCLUDE, fields, validate

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import PROBLEM_REPORT


# TODO this should be handled by a didx specific handler to mark the connection
# as abandoned.
HANDLER_CLASS = (
    "aries_cloudagent.protocols.problem_report.v1_0.handler.ProblemReportHandler"
)


class ProblemReportReason(Enum):
    """Supported reason codes."""

    INVITATION_NOT_ACCEPTED = "invitation_not_accepted"
    REQUEST_NOT_ACCEPTED = "request_not_accepted"
    REQUEST_PROCESSING_ERROR = "request_processing_error"
    RESPONSE_NOT_ACCEPTED = "response_not_accepted"
    RESPONSE_PROCESSING_ERROR = "response_processing_error"
    COMPLETE_NOT_ACCEPTED = "complete_not_accepted"
    ABANDONED = "abandoned"


class DIDXProblemReport(AgentMessage):
    """Base class representing a connection problem report message."""

    class Meta:
        """DID Exchange problem report metadata."""

        handler_class = HANDLER_CLASS
        message_type = PROBLEM_REPORT
        schema_class = "DIDXProblemReportSchema"

    def __init__(
        self,
        *,
        problem_code: Optional[str] = None,
        explain: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize a ProblemReport message instance.

        Args:
            explain: The localized error explanation
            problem_code: The standard error identifier
        """
        super().__init__(**kwargs)
        self.explain = explain
        self.problem_code = problem_code


class DIDXProblemReportSchema(AgentMessageSchema):
    """Schema for DIDXProblemReport model class."""

    class Meta:
        """Metadata for connection problem report schema."""

        model_class = DIDXProblemReport
        unknown = EXCLUDE

    explain = fields.Str(
        required=False,
        description="Localized error explanation",
        example="Invitation not accepted",
    )
    problem_code = fields.Str(
        data_key="problem-code",
        required=False,
        description="Standard error identifier",
        validate=validate.OneOf(
            choices=[prr.value for prr in ProblemReportReason],
            error="Value {input} must be one of {choices}.",
        ),
        example=ProblemReportReason.INVITATION_NOT_ACCEPTED.value,
    )
