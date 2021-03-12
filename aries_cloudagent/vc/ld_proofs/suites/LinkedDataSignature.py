from pyld import jsonld
from datetime import datetime
from hashlib import sha256
from typing import Union
from abc import abstractmethod, ABCMeta

from ..document_loader import DocumentLoader
from ..purposes import ProofPurpose
from ..constants import SECURITY_CONTEXT_V2_URL
from .LinkedDataProof import LinkedDataProof


class LinkedDataSignature(LinkedDataProof, metaclass=ABCMeta):
    def __init__(
        self,
        signature_type: str,
        verification_method: str,
        *,
        proof: dict = None,
        date: Union[datetime, str, None] = None,
    ):
        super().__init__(signature_type)
        self.verification_method = verification_method
        self.proof = proof
        self.date = date

        if isinstance(date, datetime):
            # cast date to datetime if str
            self.date = datetime.strptime(date)

    # ABSTRACT METHODS

    @abstractmethod
    def sign(self, verify_data: bytes, proof: dict):
        pass

    @abstractmethod
    def verify_signature(
        self, verify_data: bytes, verification_method: dict, proof: dict
    ):
        pass

    # PUBLIC METHODS

    async def create_proof(
        self, document: dict, *, purpose: ProofPurpose, document_loader: DocumentLoader
    ) -> dict:
        proof = None
        if self.proof:
            # TODO remove hardcoded security context
            # TODO verify if the other optional params shown in jsonld-signatures are
            # required
            proof = jsonld.compact(
                self.proof, SECURITY_CONTEXT_V2_URL, {"documentLoader": document_loader}
            )
        else:
            proof = {"@context": SECURITY_CONTEXT_V2_URL}

        proof["type"] = self.signature_type

        if not self.date:
            self.date = datetime.now()

        if not proof.get("created"):
            proof["created"] = self.date.isoformat()

        if self.verification_method:
            proof["verificationMethod"] = self.verification_method

        proof = await self.update_proof(proof)

        proof = purpose.update(proof)

        verify_data = await self.create_verify_data(document, proof, document_loader)

        proof = await self.sign(verify_data, proof)
        return proof

    async def update_proof(self, proof: dict):
        """
        Extending classes may do more
        """
        return proof

    async def verify_proof(
        self,
        proof: dict,
        *,
        document: dict,
        purpose: ProofPurpose,
        document_loader: DocumentLoader,
    ):
        try:
            verify_data = self._create_verify_data(
                document=document, proof=proof, document_loader=document_loader
            )
            verification_method = self._get_verification_method(
                proof, document_loader=document_loader
            )

            verified = await self.verify_signature(
                verify_data=verify_data,
                verification_method=verification_method,
                document=document,
                proof=proof,
                document_loader=document_loader,
            )

            if not verified:
                raise Exception("Invalid signature")

            purpose_result = await purpose.validate(
                proof,
                document=document,
                suite=self,
                verification_method=verification_method,
                document_loader=document_loader,
            )

            if not purpose_result["valid"]:
                raise purpose_result["error"]

            return {"verified": True, "purpose_result": purpose_result}
        except Exception as err:
            return {"verified": False, "error": err}

    def _get_verification_method(self, proof: dict, *, document_loader: DocumentLoader):
        verification_method = proof.get("verificationMethod")

        if not verification_method:
            raise Exception('No "verificationMethod" found in proof')

        framed = jsonld.frame(
            verification_method,
            {
                "@context": SECURITY_CONTEXT_V2_URL,
                "@embed": "@always",
                "id": verification_method,
            },
            options={"documentLoader": document_loader},
        )

        if not framed:
            raise Exception(f"Verification method {verification_method} not found")

        if framed.get("revoked"):
            raise Exception("The verification method has been revoked.")

        return framed

    def _create_verify_data(
        self, *, document: dict, proof: dict, document_loader: DocumentLoader
    ) -> str:
        c14n_proof_options = self._canonize_proof(
            proof, document_loader=document_loader
        )
        c14n_doc = self._canonize(document, document_loader=document_loader)
        hash = sha256(c14n_proof_options.encode())
        hash.update(c14n_doc.encode())

        return hash.digest()

    def _canonize(self, input, *, document_loader: DocumentLoader = None) -> str:
        # application/n-quads format always returns str
        return jsonld.normalize(
            input,
            {
                "algorithm": "URDNA2015",
                "format": "application/n-quads",
                "documentLoader": document_loader,
            },
        )

    def _canonize_proof(self, proof: dict, *, document_loader: DocumentLoader = None):
        proof = proof.copy()

        proof.pop("jws", None)
        proof.pop("signatureValue", None)
        proof.pop("proofValue", None)

        return self._canonize(proof, document_loader=document_loader)
