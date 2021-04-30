"""DID Exchange problem report reasons."""

from enum import Enum


class ProblemReportReason(str, Enum):
    """Supported reason codes."""

    REQUEST_NOT_ACCEPTED = "request_not_accepted"
    REQUEST_PROCESSING_ERROR = "request_processing_error"
    INVITATION_NOT_ACCEPTED = "invitation_not_accepted"
    RESPONSE_NOT_ACCEPTED = "response_not_accepted"
    RESPONSE_PROCESSING_ERROR = "response_processing_error"
    COMPLETE_NOT_ACCEPTED = "complete_not_accepted"
