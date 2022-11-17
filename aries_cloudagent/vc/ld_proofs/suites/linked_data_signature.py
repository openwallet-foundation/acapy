"""Linked Data Signature class."""

from abc import abstractmethod, ABCMeta
from datetime import datetime, timezone
from hashlib import sha256
from pytz import utc
from typing import Union

from ..constants import SECURITY_CONTEXT_URL
from ..document_loader import DocumentLoaderMethod
from ..error import LinkedDataProofException
from ..purposes import _ProofPurpose as ProofPurpose
from ..validation_result import ProofResult

from .linked_data_proof import LinkedDataProof


class LinkedDataSignature(LinkedDataProof, metaclass=ABCMeta):
    """Linked Data Signature class."""

    def __init__(
        self,
        *,
        signature_type: str,
        proof: dict = None,
        verification_method: str = None,
        date: Union[datetime, None] = None,
    ):
        """Create new LinkedDataSignature instance.

        Must be subclassed, not initialized directly.

        Args:
            signature_type (str): Signature type to use for the proof
            proof (dict, optional): A JSON-LD document with options to use for the
                `proof` node (e.g. any other custom fields can be provided here
                using a context different from security-v2).
            verification_method (str, optional): A key id URL to the paired public key.
            date (datetime, optional): Signing date to use. Defaults to now

        """
        super().__init__(signature_type=signature_type, proof=proof)
        self.verification_method = verification_method
        self.date = date

    @abstractmethod
    async def sign(self, *, verify_data: bytes, proof: dict) -> dict:
        """Sign the data and add it to the proof.

        Args:
            verify_data (bytes): The data to sign.
            proof (dict): The proof to add the signature to

        Returns:
            dict: The proof object with the added signature

        """
        pass

    @abstractmethod
    async def verify_signature(
        self,
        *,
        verify_data: bytes,
        verification_method: dict,
        document: dict,
        proof: dict,
        document_loader: DocumentLoaderMethod,
    ) -> bool:
        """Verify the data against the proof.

        Args:
            verify_data (bytes): The data to check
            verification_method (dict): The verification method to use.
            document (dict): The document the verify data is derived for as extra context
            proof (dict): The proof to check
            document_loader (DocumentLoader): Document loader used for resolving

        Returns:
            bool: Whether the signature is valid for the data

        """

    async def create_proof(
        self,
        *,
        document: dict,
        purpose: ProofPurpose,
        document_loader: DocumentLoaderMethod,
    ) -> dict:
        """Create proof for document, return proof."""
        proof = self.proof.copy() if self.proof else {}

        # TODO: validate if verification_method is set?
        proof["type"] = self.signature_type
        proof["verificationMethod"] = self.verification_method

        # Set created if not already set
        if not proof.get("created"):
            # Use class date, or now
            date = self.date or datetime.now(timezone.utc)
            if not date.tzinfo:
                date = utc.localize(date)
            proof["created"] = date.isoformat()

        # Allow purpose to update the proof; the `proof` is in the
        # SECURITY_CONTEXT_URL `@context` -- therefore the `purpose` must
        # ensure any added fields are also represented in that same `@context`
        proof = purpose.update(proof)

        # Create data to sign
        verify_data = self._create_verify_data(
            proof=proof, document=document, document_loader=document_loader
        )

        # Sign data
        proof = await self.sign(verify_data=verify_data, proof=proof)

        return proof

    async def verify_proof(
        self,
        *,
        proof: dict,
        document: dict,
        purpose: ProofPurpose,
        document_loader: DocumentLoaderMethod,
    ) -> ProofResult:
        """Verify proof against document and proof purpose."""
        try:
            # Create data to verify
            verify_data = self._create_verify_data(
                proof=proof, document=document, document_loader=document_loader
            )

            # Fetch verification method
            verification_method = self._get_verification_method(
                proof=proof, document_loader=document_loader
            )

            # Verify signature on data
            verified = await self.verify_signature(
                verify_data=verify_data,
                verification_method=verification_method,
                document=document,
                proof=proof,
                document_loader=document_loader,
            )
            if not verified:
                raise LinkedDataProofException(
                    f"Invalid signature on document {document}"
                )

            # Ensure proof was performed for a valid purpose
            purpose_result = purpose.validate(
                proof=proof,
                document=document,
                suite=self,
                verification_method=verification_method,
                document_loader=document_loader,
            )

            if not purpose_result.valid:
                return ProofResult(
                    verified=False,
                    purpose_result=purpose_result,
                    error=purpose_result.error,
                )

            return ProofResult(verified=True, purpose_result=purpose_result)
        except Exception as err:
            return ProofResult(verified=False, error=err)

    def _create_verify_data(
        self, *, proof: dict, document: dict, document_loader: DocumentLoaderMethod
    ) -> bytes:
        """Create signing or verification data."""
        c14n_proof_options = self._canonize_proof(
            proof=proof, document=document, document_loader=document_loader
        )
        c14n_doc = self._canonize(input=document, document_loader=document_loader)

        # TODO: detect any dropped properties using expand/contract step

        return (
            sha256(c14n_proof_options.encode("utf-8")).digest()
            + sha256(c14n_doc.encode("utf-8")).digest()
        )

    def _canonize_proof(
        self, *, proof: dict, document: dict, document_loader: DocumentLoaderMethod
    ):
        """Canonize proof dictionary. Removes jws, signature, etc..."""
        # Use default security context url if document has no context
        proof = {
            **proof,
            "@context": document.get("@context") or SECURITY_CONTEXT_URL,
        }

        proof.pop("jws", None)
        proof.pop("signatureValue", None)
        proof.pop("proofValue", None)

        return self._canonize(input=proof, document_loader=document_loader)
