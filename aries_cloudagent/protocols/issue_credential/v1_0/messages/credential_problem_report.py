"""A problem report message."""

from enum import Enum

from marshmallow import EXCLUDE, validates_schema, ValidationError

from ....problem_report.v1_0.message import ProblemReport, ProblemReportSchema

from ..message_types import CREDENTIAL_PROBLEM_REPORT, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.credential_problem_report_handler."
    "CredentialProblemReportHandler"
)


class ProblemReportReason(Enum):
    """Supported reason codes."""

    ISSUANCE_ABANDONED = "issuance-abandoned"


class CredentialProblemReport(ProblemReport):
    """Class representing a problem report message."""

    class Meta:
        """Problem report metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "CredentialProblemReportSchema"
        message_type = CREDENTIAL_PROBLEM_REPORT

    def __init__(self, *args, **kwargs):
        """Initialize problem report object."""
        super().__init__(*args, **kwargs)


class CredentialProblemReportSchema(ProblemReportSchema):
    """Problem report schema."""

    class Meta:
        """Schema metadata."""

        model_class = CredentialProblemReport
        unknown = EXCLUDE

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """
        Validate schema fields.

        Args:
            data: The data to validate

        """
        if (
            data.get("description", {}).get("code", "")
            != ProblemReportReason.ISSUANCE_ABANDONED.value
        ):
            raise ValidationError(
                "Value for description.code must be "
                f"{ProblemReportReason.ISSUANCE_ABANDONED.value}"
            )
