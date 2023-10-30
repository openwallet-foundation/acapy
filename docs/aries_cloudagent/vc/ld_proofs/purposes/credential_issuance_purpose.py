"""Credential Issuance proof purpose class."""

from typing import List, TYPE_CHECKING

from pyld.jsonld import JsonLdProcessor
from pyld import jsonld

from ..constants import CREDENTIALS_ISSUER_URL
from ..document_loader import DocumentLoaderMethod
from ..error import LinkedDataProofException
from ..validation_result import PurposeResult

from .assertion_proof_purpose import AssertionProofPurpose

# Avoid circular dependency
if TYPE_CHECKING:
    from ..suites import LinkedDataProof


class CredentialIssuancePurpose(AssertionProofPurpose):
    """Credential Issuance proof purpose."""

    def validate(
        self,
        *,
        proof: dict,
        document: dict,
        suite: "LinkedDataProof",
        verification_method: dict,
        document_loader: DocumentLoaderMethod,
    ) -> PurposeResult:
        """Validate if the issuer matches the controller of the verification method."""
        try:
            result = super().validate(
                proof=proof,
                document=document,
                suite=suite,
                verification_method=verification_method,
                document_loader=document_loader,
            )

            # Return early if super check was invalid
            if not result.valid:
                return result

            # FIXME: Other implementations don't expand, but
            # if we don't expand we can't get the property using
            # the full CREDENTIALS_ISSUER_URL.
            [expanded] = jsonld.expand(
                document,
                {
                    "documentLoader": document_loader,
                },
            )

            issuer: List[dict] = JsonLdProcessor.get_values(
                expanded, CREDENTIALS_ISSUER_URL
            )

            if len(issuer) == 0:
                raise LinkedDataProofException("Credential issuer is required.")

            controller_id = result.controller.get("id")
            issuer_id = issuer[0].get("@id")

            if controller_id != issuer_id:
                raise LinkedDataProofException(
                    "Credential issuer must match the verification method controller."
                )

            return result
        except Exception as e:
            return PurposeResult(valid=False, error=e)
