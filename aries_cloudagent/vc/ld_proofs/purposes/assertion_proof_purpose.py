"""Assertion proof purpose class."""

from datetime import datetime, timedelta
from typing import Optional

from .controller_proof_purpose import ControllerProofPurpose


class AssertionProofPurpose(ControllerProofPurpose):
    """Assertion proof purpose class."""

    term = "assertionMethod"

    def __init__(
        self,
        *,
        date: Optional[datetime] = None,
        max_timestamp_delta: Optional[timedelta] = None,
    ):
        """Initialize new instance of AssertionProofPurpose."""
        super().__init__(
            term=AssertionProofPurpose.term,
            date=date,
            max_timestamp_delta=max_timestamp_delta,
        )
