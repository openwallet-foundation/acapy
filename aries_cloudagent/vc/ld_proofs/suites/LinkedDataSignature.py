import traceback
from pyld import jsonld
from datetime import datetime
from hashlib import sha256
from typing import Union
from abc import abstractmethod, ABCMeta

from ..document_loader import DocumentLoader
from ..purposes import ProofPurpose
from ..constants import SECURITY_V2_URL
from ..util import frame_without_compact_to_relative
from .LinkedDataProof import LinkedDataProof


class LinkedDataSignature(LinkedDataProof, metaclass=ABCMeta):
    def __init__(
        self,
        signature_type: str,
        verification_method: str,
        proof: dict = None,
        date: Union[datetime, str, None] = None,
    ):
        super().__init__(signature_type=signature_type)
        self.verification_method = verification_method
        self.proof = proof
        self.date = date

        if isinstance(date, str):
            # cast date to datetime if str
            self.date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")

    # ABSTRACT METHODS

    @abstractmethod
    async def sign(self, verify_data: bytes, proof: dict):
        pass

    @abstractmethod
    async def verify_signature(
        self,
        verify_data: bytes,
        verification_method: dict,
        document: dict,
        proof: dict,
        document_loader: DocumentLoader,
    ):
        pass

    # PUBLIC METHODS

    async def create_proof(
        self, document: dict, purpose: ProofPurpose, document_loader: DocumentLoader
    ) -> dict:
        proof = None
        if self.proof:
            # TODO remove hardcoded security context
            # TODO verify if the other optional params shown in jsonld-signatures are
            # required
            proof = jsonld.compact(
                self.proof, SECURITY_V2_URL, {"documentLoader": document_loader}
            )
        else:
            proof = {"@context": SECURITY_V2_URL}

        proof["type"] = self.signature_type
        proof["verificationMethod"] = self.verification_method

        if not self.date:
            self.date = datetime.now()

        if not proof.get("created"):
            proof["created"] = self.date.isoformat()

        proof = self.update_proof(proof=proof)
        proof = purpose.update(proof)

        verify_data = self._create_verify_data(
            proof=proof, document=document, document_loader=document_loader
        )

        proof = await self.sign(verify_data=verify_data, proof=proof)
        return proof

    def update_proof(self, proof: dict):
        """
        Extending classes may do more
        """
        return proof

    async def verify_proof(
        self,
        proof: dict,
        document: dict,
        purpose: ProofPurpose,
        document_loader: DocumentLoader,
    ) -> dict:
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
                raise Exception("Invalid signature")

            purpose_result = purpose.validate(
                proof=proof,
                document=document,
                suite=self,
                verification_method=verification_method,
                document_loader=document_loader,
            )

            if not purpose_result["valid"]:
                raise purpose_result["error"]

            return {"verified": True, "purpose_result": purpose_result}
        except Exception as err:
            return {
                "verified": False,
                "error": err,
                # TODO: leave trace in error?
                "trace": traceback.format_exc(),
            }

    def _get_verification_method(self, proof: dict, document_loader: DocumentLoader):
        verification_method = proof.get("verificationMethod")

        if not verification_method:
            raise Exception('No "verificationMethod" found in proof')

        if isinstance(verification_method, dict):
            verification_method: str = verification_method.get("id")

        framed = frame_without_compact_to_relative(
            input=verification_method,
            frame={
                "@context": SECURITY_V2_URL,
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
        self, proof: dict, document: dict, document_loader: DocumentLoader
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

    def _canonize(self, input, document_loader: DocumentLoader = None) -> str:
        # application/n-quads format always returns str
        return jsonld.normalize(
            input,
            {
                "algorithm": "URDNA2015",
                "format": "application/n-quads",
                "documentLoader": document_loader,
            },
        )

    def _canonize_proof(self, proof: dict, document_loader: DocumentLoader = None):
        proof = proof.copy()

        proof.pop("jws", None)
        proof.pop("signatureValue", None)
        proof.pop("proofValue", None)

        return self._canonize(input=proof, document_loader=document_loader)
