"""BbsBlsSignature2020 class."""

from datetime import datetime, timezone
from pytz import utc
from typing import List, Union

from ....wallet.util import b64_to_bytes, bytes_to_b64

from ..crypto import _KeyPair as KeyPair
from ..document_loader import DocumentLoaderMethod
from ..error import LinkedDataProofException
from ..purposes import _ProofPurpose as ProofPurpose
from ..validation_result import ProofResult

from .bbs_bls_signature_2020_base import BbsBlsSignature2020Base


class BbsBlsSignature2020(BbsBlsSignature2020Base):
    """BbsBlsSignature2020 class."""

    signature_type = "BbsBlsSignature2020"

    def __init__(
        self,
        *,
        key_pair: KeyPair,
        proof: dict = None,
        verification_method: str = None,
        date: Union[datetime, None] = None,
    ):
        """Create new BbsBlsSignature2020 instance.

        Args:
            key_pair (KeyPair): Key pair to use. Must provide BBS signatures
            proof (dict, optional): A JSON-LD document with options to use for the
                `proof` node (e.g. any other custom fields can be provided here
                using a context different from security-v2).
            verification_method (str, optional): A key id URL to the paired public key.
            date (datetime, optional): Signing date to use. Defaults to now

        """
        super().__init__(signature_type=BbsBlsSignature2020.signature_type, proof=proof)
        self.key_pair = key_pair
        self.verification_method = verification_method
        self.date = date

    async def create_proof(
        self,
        *,
        document: dict,
        purpose: ProofPurpose,
        document_loader: DocumentLoaderMethod,
    ) -> dict:
        """Create proof for document, return proof."""
        proof = self.proof.copy() if self.proof else {}

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

        # Create statements to sign
        verify_data = self._create_verify_data(
            proof=proof, document=document, document_loader=document_loader
        )

        # Encode statements as bytes
        verify_data = list(map(lambda item: item.encode("utf-8"), verify_data))

        # Sign statements
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
            # Create statements to verify
            verify_data = self._create_verify_data(
                proof=proof, document=document, document_loader=document_loader
            )

            # Encode statements as bytes
            verify_data = list(map(lambda item: item.encode("utf-8"), verify_data))

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
    ) -> List[str]:
        """Create verification data.

        Returns a list of canonized statements

        """
        proof_statements = self._create_verify_proof_data(
            proof=proof, document=document, document_loader=document_loader
        )
        document_statements = self._create_verify_document_data(
            document=document, document_loader=document_loader
        )

        return [*proof_statements, *document_statements]

    def _canonize_proof(
        self, *, proof: dict, document: dict, document_loader: DocumentLoaderMethod
    ):
        """Canonize proof dictionary. Removes value that are not part of signature."""
        # Use default security context url if document has no context
        proof = {**proof, "@context": document.get("@context") or self._default_proof}

        proof.pop("proofValue", None)

        return self._canonize(input=proof, document_loader=document_loader)

    async def sign(self, *, verify_data: List[bytes], proof: dict) -> dict:
        """Sign the data and add it to the proof.

        Args:
            verify_data (List[bytes]): The data to sign.
            proof (dict): The proof to add the signature to

        Returns:
            dict: The proof object with the added signature

        """
        signature = await self.key_pair.sign(verify_data)

        proof["proofValue"] = bytes_to_b64(
            signature, urlsafe=False, pad=True, encoding="utf-8"
        )

        return proof

    async def verify_signature(
        self,
        *,
        verify_data: List[bytes],
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

        if not (isinstance(proof.get("proofValue"), str)):
            raise LinkedDataProofException(
                'The proof does not contain a valid "proofValue" property.'
            )

        signature = b64_to_bytes(proof["proofValue"])

        # If the key pair has no public key yet, create a new key pair
        # from the verification method. We don't want to overwrite data
        # on the original key pair
        key_pair = self.key_pair
        if not key_pair.has_public_key:
            key_pair = key_pair.from_verification_method(verification_method)

        return await key_pair.verify(verify_data, signature)
