"""DID Exchange problem report and reasons."""

from enum import Enum
import logging

from marshmallow import EXCLUDE, ValidationError, validates_schema

from ....problem_report.v1_0.message import ProblemReport, ProblemReportSchema
from ..message_types import PROBLEM_REPORT


HANDLER_CLASS = (
    "aries_cloudagent.protocols.didexchange.v1_0.handlers."
    "problem_report_handler.ProblemReportHandler"
)

LOGGER = logging.getLogger(__name__)


class ProblemReportReason(Enum):
    """Supported reason codes."""

    INVITATION_NOT_ACCEPTED = "invitation_not_accepted"
    REQUEST_NOT_ACCEPTED = "request_not_accepted"
    REQUEST_PROCESSING_ERROR = "request_processing_error"
    RESPONSE_NOT_ACCEPTED = "response_not_accepted"
    RESPONSE_PROCESSING_ERROR = "response_processing_error"
    COMPLETE_NOT_ACCEPTED = "complete_not_accepted"


class DIDXProblemReport(ProblemReport):
    """Base class representing a connection problem report message."""

    class Meta:
        """DID Exchange problem report metadata."""

        handler_class = HANDLER_CLASS
        message_type = PROBLEM_REPORT
        schema_class = "DIDXProblemReportSchema"


class DIDXProblemReportSchema(ProblemReportSchema):
    """Schema for DIDXProblemReport model class."""

    class Meta:
        """Metadata for connection problem report schema."""

        model_class = DIDXProblemReport
        unknown = EXCLUDE

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Validate schema fields."""

        if not data.get("description", {}).get("code", ""):
            raise ValidationError("Value for description.code must be present")
        elif data.get("description", {}).get("code", "") not in [
            prr.value for prr in ProblemReportReason
        ]:
            locales = list(data.get("description").keys())
            locales.remove("code")
            LOGGER.warning(
                "Unexpected error code received.\n"
                f"Code: {data.get('description').get('code')}, "
                f"Description: {data.get('description').get(locales[0])}"
            )
