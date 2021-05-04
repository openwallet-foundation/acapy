"""Problem report reasons."""

from enum import Enum


class ProblemReportReason(str, Enum):
    """Supported reason codes."""

    MEDIATION_NOT_GRANTED = "mediation-not-granted"
    MEDIATION_ALREADY_EXISTS = "mediation-already-exists"
