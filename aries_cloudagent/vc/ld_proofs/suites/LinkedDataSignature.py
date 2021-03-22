"""Linked Data Signature class"""

from pyld import jsonld
from datetime import datetime
from hashlib import sha256
from typing import Union
from abc import abstractmethod, ABCMeta

from ..error import LinkedDataProofException
from ..validation_result import ProofResult
from ..document_loader import DocumentLoader
from ..purposes import ProofPurpose
from ..constants import SECURITY_V2_URL
from .LinkedDataProof import LinkedDataProof


class LinkedDataSignature(LinkedDataProof, metaclass=ABCMeta):
    """Linked Data Signature class"""

    def __init__(
        self,
        *,
        signature_type: str,
        proof: dict = None,
        verification_method: str = None,
        date: Union[str, None] = None,
    ):
        """Create new LinkedDataSignature instance"""
        super().__init__(signature_type=signature_type, proof=proof)
        self.verification_method = verification_method
        self.date = date

    @abstractmethod
    async def sign(self, *, verify_data: bytes, proof: dict) -> dict:
        """Sign the data and add it to the proof

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
        document_loader: DocumentLoader,
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
        self, *, document: dict, purpose: ProofPurpose, document_loader: DocumentLoader
    ) -> dict:
        """Create proof for document, return proof"""
        proof = None
        if self.proof:
            # TODO remove hardcoded security context
            # TODO verify if the other optional params shown in jsonld-signatures are
            # required
            # TODO: digitalbazaar changed this implementation after we wrote it. Should
            # double check to make sure we're doing it correctly
            # https://github.com/digitalbazaar/jsonld-signatures/commit/2c98a2fb626b85e31d16b16e7ea6a90fd83534c5
            proof = jsonld.compact(
                self.proof, SECURITY_V2_URL, {"documentLoader": document_loader}
            )
        else:
            proof = {"@context": SECURITY_V2_URL}

        # TODO: validate if verification_method is set?
        proof["type"] = self.signature_type
        proof["verificationMethod"] = self.verification_method

        if not self.date:
            self.date = datetime.now()

        if not proof.get("created"):
            proof["created"] = self.date.isoformat()

        proof = purpose.update(proof)

        verify_data = self._create_verify_data(
            proof=proof, document=document, document_loader=document_loader
        )

        proof = await self.sign(verify_data=verify_data, proof=proof)
        return proof

    async def verify_proof(
        self,
        *,
        proof: dict,
        document: dict,
        purpose: ProofPurpose,
        document_loader: DocumentLoader,
    ) -> ProofResult:
        """Verify proof against document and proof purpose."""
        try:
            verify_data = self._create_verify_data(
                proof=proof, document=document, document_loader=document_loader
            )
            verification_method = self._get_verification_method(
                proof=proof, document_loader=document_loader
            )

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

            purpose_result = purpose.validate(
                proof=proof,
                document=document,
                suite=self,
                verification_method=verification_method,
                document_loader=document_loader,
            )

            if not purpose_result.valid:
                raise purpose_result.error

            return ProofResult(verified=True, purpose_result=purpose_result)
        except Exception as err:
            return ProofResult(verified=False, error=err)

    def _get_verification_method(
        self, *, proof: dict, document_loader: DocumentLoader
    ) -> dict:
        verification_method = proof.get("verificationMethod")

        if not verification_method:
            raise Exception('No "verificationMethod" found in proof')

        if isinstance(verification_method, dict):
            verification_method: str = verification_method.get("id")

        framed = jsonld.frame(
            verification_method,
            frame={
                "@context": SECURITY_V2_URL,
                "@embed": "@always",
                "id": verification_method,
            },
            options={
                "documentLoader": document_loader,
                "expandContext": SECURITY_V2_URL,
                # if we don't set base explicitly it will remove the base in returned
                # document (e.g. use key:z... instead of did:key:z...)
                # same as compactToRelative in jsonld.js
                "base": None,
            },
        )

        if not framed:
            raise LinkedDataProofException(
                f"Verification method {verification_method} not found"
            )

        if framed.get("revoked"):
            raise LinkedDataProofException("The verification method has been revoked.")

        return framed

    def _create_verify_data(
        self, *, proof: dict, document: dict, document_loader: DocumentLoader
    ) -> bytes:
        c14n_proof_options = self._canonize_proof(
            proof=proof, document_loader=document_loader
        )
        c14n_doc = self._canonize(input=document, document_loader=document_loader)

        # TODO: detect any dropped properties using expand/contract step

        return (
            sha256(c14n_proof_options.encode("utf-8")).digest()
            + sha256(c14n_doc.encode("utf-8")).digest()
        )

    def _canonize(self, *, input, document_loader: DocumentLoader = None) -> str:
        """Canonize input document using URDNA2015 algorithm"""
        # application/n-quads format always returns str
        return jsonld.normalize(
            input,
            {
                "algorithm": "URDNA2015",
                "format": "application/n-quads",
                "documentLoader": document_loader,
            },
        )

    def _canonize_proof(self, *, proof: dict, document_loader: DocumentLoader = None):
        """Canonize proof dictionary. Removes jws, signature, etc..."""
        proof = proof.copy()

        proof.pop("jws", None)
        proof.pop("signatureValue", None)
        proof.pop("proofValue", None)

        return self._canonize(input=proof, document_loader=document_loader)
