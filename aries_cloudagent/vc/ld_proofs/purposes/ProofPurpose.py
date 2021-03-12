from datetime import datetime, timedelta

from ..document_loader import DocumentLoader
from ..suites import LinkedDataProof


class ProofPurpose:
    def __init__(
        self, term: str, *, date: datetime = None, max_timestamp_delta: timedelta = None
    ):
        self.term = term
        self.date = date or datetime.now()
        self.max_timestamp_delta = max_timestamp_delta

    def validate(
        self,
        proof: dict,
        *,
        document: dict,
        suite: LinkedDataProof,
        verification_method: dict,
        document_loader: DocumentLoader
    ) -> dict:
        try:
            if self.max_timestamp_delta is not None:
                expected = self.date.time()
                created = datetime.strptime(proof.get("created"), "%Y-%m-%dT%H:%M:%SZ")

                if not (
                    created >= (expected - self.max_timestamp_delta)
                    and created <= (expected + self.max_timestamp_delta)
                ):
                    raise Exception("The proof's created timestamp is out of range.")

                return {"valid": True}
        except Exception as err:
            return {"valid": False, "error": err}

    def update(self, proof: dict) -> dict:
        proof["proofPurpose"] = self.term
        return proof

    def match(self, proof: dict) -> bool:
        return proof.get("proofPurpose") == self.term
