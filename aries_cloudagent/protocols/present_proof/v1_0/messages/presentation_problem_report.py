"""A problem report message."""

from marshmallow import EXCLUDE

from ....problem_report.v1_0.message import ProblemReport, ProblemReportSchema

from ..message_types import PRESENTATION_PROBLEM_REPORT, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.presentation_problem_report_handler."
    "PresentationProblemReportHandler"
)


class PresentationProblemReport(ProblemReport):
    """Class representing a problem report message."""

    class Meta:
        """Problem report metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "PresentationProblemReportSchema"
        message_type = PRESENTATION_PROBLEM_REPORT

    def __init__(self, **kwargs):
        """Initialize problem report object."""
        super().__init__(**kwargs)


class PresentationProblemReportSchema(ProblemReportSchema):
    """Problem report schema."""

    class Meta:
        """Schema metadata."""

        model_class = PresentationProblemReport
        unknown = EXCLUDE
