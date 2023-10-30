"""Assertion proof purpose class."""

from datetime import datetime, timedelta

from .controller_proof_purpose import ControllerProofPurpose


class AssertionProofPurpose(ControllerProofPurpose):
    """Assertion proof purpose class."""

    term = "assertionMethod"

    def __init__(self, *, date: datetime = None, max_timestamp_delta: timedelta = None):
        """Initialize new instance of AssertionProofPurpose."""
        super().__init__(
            term=AssertionProofPurpose.term,
            date=date,
            max_timestamp_delta=max_timestamp_delta,
        )
