"""A problem report message."""

from marshmallow import EXCLUDE

from ....problem_report.v1_0.message import ProblemReport, ProblemReportSchema

from ..message_types import PRES_20_PROBLEM_REPORT, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.pres_problem_report_handler."
    "V20PresProblemReportHandler"
)


class V20PresProblemReport(ProblemReport):
    """Class representing a problem report message."""

    class Meta:
        """Problem report metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "V20PresProblemReportSchema"
        message_type = PRES_20_PROBLEM_REPORT

    def __init__(self, **kwargs):
        """Initialize problem report object."""
        super().__init__(**kwargs)


class V20PresProblemReportSchema(ProblemReportSchema):
    """Problem report schema."""

    class Meta:
        """Schema metadata."""

        model_class = V20PresProblemReport
        unknown = EXCLUDE
