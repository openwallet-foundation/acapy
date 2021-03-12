from datetime import datetime, timedelta
from pyld.jsonld import JsonLdProcessor

from ..suites import LinkedDataProof
from ..document_loader import DocumentLoader
from ..constants import CREDENTIALS_ISSUER_URL
from .AssertionProofPurpose import AssertionProofPurpose


class CredentialIssuancePurpose(AssertionProofPurpose):
    def __init__(self, date: datetime = None, max_timestamp_delta: timedelta = None):
        super().__init__(date=date, max_timestamp_delta=max_timestamp_delta)

    def validate(
        self,
        proof: dict,
        *,
        document: dict,
        suite: LinkedDataProof,
        verification_method: str,
        document_loader: DocumentLoader,
    ):
        try:
            result = super().validate(
                proof=proof,
                document=document,
                suite=suite,
                verification_method=verification_method,
                document_loader=document_loader,
            )

            if not result.get("valid"):
                raise result.get("error")

            issuer: list = JsonLdProcessor.get_values(document, CREDENTIALS_ISSUER_URL)

            if not issuer or len(issuer) == 0:
                raise Exception("Credential issuer is required.")

            if result.get("controller", {}).get("id") != issuer[0].get("id"):
                raise Exception(
                    "Credential issuer must match the verification method controller."
                )

            return {"valid": True}

        except Exception as e:
            return {"valid": False, "error": e}
