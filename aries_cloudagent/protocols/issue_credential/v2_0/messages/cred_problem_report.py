"""A problem report message."""

from marshmallow import EXCLUDE

from ....problem_report.v2_0.message import ProblemReport, ProblemReportSchema

from ..message_types import CRED_20_PROBLEM_REPORT, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.problem_report_handler.ProblemReportHandler"
)


class IssueCredV20ProblemReport(ProblemReport):
    """Class representing a problem report message."""

    class Meta:
        """Problem report metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "IssueCredV20ProblemReportSchema"
        message_type = CRED_20_PROBLEM_REPORT

    def __init__(self, **kwargs):
        """Initialize problem report object."""
        super().__init__(**kwargs)


class IssueCredV20ProblemReportSchema(ProblemReportSchema):
    """Problem report schema."""

    class Meta:
        """Schema metadata."""

        model_class = IssueCredV20ProblemReport
        unknown = EXCLUDE
