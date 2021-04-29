"""A problem report message."""

from marshmallow import EXCLUDE

from ....problem_report.v1_0.message import ProblemReport, ProblemReportSchema

from ..message_types import CREDENTIAL_PROBLEM_REPORT, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.credential_problem_report_handler."
    "CredentialProblemReportHandler"
)


class CredentialProblemReport(ProblemReport):
    """Class representing a problem report message."""

    class Meta:
        """Problem report metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "CredentialProblemReportSchema"
        message_type = CREDENTIAL_PROBLEM_REPORT

    def __init__(self, **kwargs):
        """Initialize problem report object."""
        super().__init__(**kwargs)


class CredentialProblemReportSchema(ProblemReportSchema):
    """Problem report schema."""

    class Meta:
        """Schema metadata."""

        model_class = CredentialProblemReport
        unknown = EXCLUDE
