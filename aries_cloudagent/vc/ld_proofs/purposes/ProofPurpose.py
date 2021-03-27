"""Base Proof Purpose class."""

from datetime import datetime, timedelta

from ....messaging.util import str_to_datetime
from ..validation_result import PurposeResult
from ..document_loader import DocumentLoader
from ..suites import LinkedDataProof


class ProofPurpose:
    """Base proof purpose class."""

    def __init__(
        self, *, term: str, date: datetime = None, max_timestamp_delta: timedelta = None
    ):
        """Initialize new proof purpose instance."""
        self.term = term
        self.date = date or datetime.now()
        self.max_timestamp_delta = max_timestamp_delta

    def validate(
        self,
        *,
        proof: dict,
        document: dict,
        suite: LinkedDataProof,
        verification_method: dict,
        document_loader: DocumentLoader,
    ) -> PurposeResult:
        """Validate whether created date of proof is out of max_timestamp_delta range."""
        try:
            if self.max_timestamp_delta is not None:
                expected = self.date.time()

                created = str_to_datetime(proof.get("created"))

                if not (
                    created >= (expected - self.max_timestamp_delta)
                    and created <= (expected + self.max_timestamp_delta)
                ):
                    raise Exception("The proof's created timestamp is out of range.")

            return PurposeResult(valid=True)
        except Exception as err:
            return PurposeResult(valid=False, error=err)

    def update(self, proof: dict) -> dict:
        """Update proof purpose on proof."""
        proof["proofPurpose"] = self.term
        return proof

    def match(self, proof: dict) -> bool:
        """Check whether the passed proof matches with the term of this proof purpose."""
        return proof.get("proofPurpose") == self.term
