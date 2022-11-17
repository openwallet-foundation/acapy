"""A problem report message."""

import logging

from enum import Enum

from marshmallow import EXCLUDE, ValidationError, validates_schema

from ....problem_report.v1_0.message import ProblemReport, ProblemReportSchema

from ..message_types import CRED_20_PROBLEM_REPORT, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.cred_problem_report_handler.CredProblemReportHandler"
)

LOGGER = logging.getLogger(__name__)


class ProblemReportReason(Enum):
    """Supported reason codes."""

    ISSUANCE_ABANDONED = "issuance-abandoned"


class V20CredProblemReport(ProblemReport):
    """Class representing a problem report message."""

    class Meta:
        """Problem report metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "V20CredProblemReportSchema"
        message_type = CRED_20_PROBLEM_REPORT

    def __init__(self, *args, **kwargs):
        """Initialize problem report object."""
        super().__init__(*args, **kwargs)


class V20CredProblemReportSchema(ProblemReportSchema):
    """Problem report schema."""

    class Meta:
        """Schema metadata."""

        model_class = V20CredProblemReport
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
        elif (
            data.get("description", {}).get("code", "")
            != ProblemReportReason.ISSUANCE_ABANDONED.value
        ):
            locales = list(data.get("description").keys())
            locales.remove("code")
            LOGGER.warning(
                "Unexpected error code received.\n"
                f"Code: {data.get('description').get('code')}, "
                f"Description: {data.get('description').get(locales[0])}"
            )
