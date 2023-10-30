"""Authentication proof purpose class."""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from ..document_loader import DocumentLoaderMethod
from ..error import LinkedDataProofException
from ..validation_result import PurposeResult

from .controller_proof_purpose import ControllerProofPurpose

# Avoid circular dependency
if TYPE_CHECKING:
    from ..suites import LinkedDataProof


class AuthenticationProofPurpose(ControllerProofPurpose):
    """Authentication proof purpose."""

    term = "authentication"

    def __init__(
        self,
        *,
        challenge: str,
        domain: str = None,
        date: datetime = None,
        max_timestamp_delta: timedelta = None,
    ):
        """Initialize new AuthenticationProofPurpose instance."""
        super().__init__(
            term=AuthenticationProofPurpose.term,
            date=date,
            max_timestamp_delta=max_timestamp_delta,
        )

        self.challenge = challenge
        self.domain = domain

    def validate(
        self,
        *,
        proof: dict,
        document: dict,
        suite: "LinkedDataProof",
        verification_method: dict,
        document_loader: DocumentLoaderMethod,
    ) -> PurposeResult:
        """Validate whether challenge and domain are valid."""
        try:
            if proof.get("challenge") != self.challenge:
                raise LinkedDataProofException(
                    f"The challenge is not as expected; challenge="
                    f'{proof.get("challenge")}, expected={self.challenge}'
                )

            if self.domain and (proof.get("domain") != self.domain):
                raise LinkedDataProofException(
                    f"The domain is not as expected; "
                    f'domain={proof.get("domain")}, expected={self.domain}'
                )

            return super().validate(
                proof=proof,
                document=document,
                suite=suite,
                verification_method=verification_method,
                document_loader=document_loader,
            )
        except Exception as e:
            return PurposeResult(valid=False, error=e)

    def update(self, proof: dict) -> dict:
        """Update poof purpose, challenge and domain on proof."""
        proof = super().update(proof)
        proof["challenge"] = self.challenge

        if self.domain:
            proof["domain"] = self.domain

        return proof

    def __eq__(self, o: object) -> bool:
        """Check if object is same as ProofPurpose."""
        if isinstance(o, AuthenticationProofPurpose):
            return (
                super().__eq__(o)
                and self.challenge == o.challenge
                and self.domain == o.domain
            )

        return False
