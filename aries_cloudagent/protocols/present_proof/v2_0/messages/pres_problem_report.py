"""A problem report message."""

from enum import Enum

from marshmallow import EXCLUDE, ValidationError, validates_schema

from ....problem_report.v1_0.message import ProblemReport, ProblemReportSchema

from ..message_types import PRES_20_PROBLEM_REPORT, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.pres_problem_report_handler."
    "V20PresProblemReportHandler"
)


class ProblemReportReason(Enum):
    """Supported reason codes."""

    ABANDONED = "abandoned"


class V20PresProblemReport(ProblemReport):
    """Class representing a problem report message."""

    class Meta:
        """Problem report metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "V20PresProblemReportSchema"
        message_type = PRES_20_PROBLEM_REPORT

    def __init__(self, *args, **kwargs):
        """Initialize problem report object."""
        super().__init__(*args, **kwargs)


class V20PresProblemReportSchema(ProblemReportSchema):
    """Problem report schema."""

    class Meta:
        """Schema metadata."""

        model_class = V20PresProblemReport
        unknown = EXCLUDE

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """
        Validate schema fields.

        Args:
            data: The data to validate

        """
        if not data.get("description", {}).get("code", ""):
            raise ValidationError("Value for description.code must be present")
