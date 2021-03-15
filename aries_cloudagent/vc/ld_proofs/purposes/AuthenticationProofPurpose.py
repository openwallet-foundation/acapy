from datetime import datetime, timedelta
from typing import Awaitable

from ..document_loader import DocumentLoader
from ..suites import LinkedDataProof
from .ControllerProofPurpose import ControllerProofPurpose


class AuthenticationProofPurpose(ControllerProofPurpose):
    def __init__(
        self,
        challenge: str,
        domain: str = None,
        date: datetime = None,
        max_timestamp_delta: timedelta = None,
    ):
        super().__init__(
            term="authentication", date=date, max_timestamp_delta=max_timestamp_delta
        )

        self.challenge = challenge
        self.domain = domain

    def validate(
        self,
        proof: dict,
        document: dict,
        suite: LinkedDataProof,
        verification_method: dict,
        document_loader: DocumentLoader,
    ) -> dict:
        try:
            if proof.get("challenge") != self.challenge:
                raise Exception(
                    f'The challenge is not expected; challenge={proof.get("challenge")}, expected={self.challenge}'
                )

            if self.domain and (proof.get("domain") != self.domain):
                raise Exception(
                    f'The domain is not as expected; domain={proof.get("domain")}, expected={self.domain}'
                )

            return super().validate(
                proof=proof,
                document=document,
                suite=suite,
                verification_method=verification_method,
                document_loader=document_loader,
            )
        except Exception as e:
            return {"valid": False, "error": e}

    async def update(self, proof: dict) -> Awaitable[dict]:
        proof = super().update(proof)
        proof["challenge"] = self.challenge

        if self.domain:
            proof["domain"] = self.domain

        return proof
