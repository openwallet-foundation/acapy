from abc import abstractmethod, ABCMeta
from .LinkedDataProof import LinkedDataProof
from ..purposes import ProofPurpose
from pyld import jsonld
from datetime import datetime
from hashlib import sha256
from typing import Union
from ..constants import SECURITY_CONTEXT_V2_URL


class LinkedDataSignature(LinkedDataProof, metaclass=ABCMeta):
    def __init__(
        self,
        signature_type: str,
        verification_method: str,
        *,
        proof: dict = None,
        date: Union[datetime, str],
    ):
        super().__init__(signature_type)
        self.verification_method = verification_method
        self.proof = proof
        self.date = date

    async def create_proof(
        self,
        document: dict,
        purpose: ProofPurpose,
        document_loader: callable,
        compact_proof: bool,
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

        # TODO validate existance and type of date more carefully
        # see: jsonld-signatures implementation
        if not self.date:
            self.date = datetime.now().isoformat()

        if not proof.get("created"):
            proof["created"] = str(self.date.isoformat())

        if self.verification_method:
            proof[
                "verificationMethod"
            ] = f"{self.verification_method}#{self.verification_method[8:]}"

        proof = await self.update_proof(proof)

        proof = purpose.update(proof)
        verify_data = await self.create_verify_data(document, proof, document_loader)

        proof = await self.sign(verify_data, proof)
        return proof

    async def create_verify_data(
        self, document: dict, proof: dict, document_loader: dict
    ) -> str:
        c14n_proof_options = await self.canonize_proof(
            proof, document_loader=document_loader
        )
        print(c14n_proof_options)
        c14n_doc = await self.canonize(document, document_loader=document_loader)
        hash = sha256(c14n_proof_options.encode())
        hash.update(c14n_doc.encode())

        # TODO verify this is the right return type
        return hash.digest()

    async def canonize(self, input_, *, document_loader: callable = None):
        return jsonld.normalize(
            input_,
            {
                "algorithm": "URDNA2015",
                "format": "application/n-quads",
                "documentLoader": document_loader,
            },
        )

    async def canonize_proof(self, proof: dict, *, document_loader: callable = None):
        print(proof)
        proof = proof.copy()

        # TODO check if these values ever exist in our use case
        # del proof['jws']
        # del proof['signatureValue']
        # del proof['proofValue']

        return await self.canonize(proof, document_loader=document_loader)

    async def update_proof(self, proof: dict):
        """
        Extending classes may do more
        """
        return proof

    async def verify_proof(
        self,
        proof: dict,
        document: dict,
        purpose: ProofPurpose,
        document_loader: callable,
    ):
        try:
            verify_data = await self.create_verify_data(
                document, proof, document_loader=document_loader
            )
            verification_method = await self.get_verification_method(
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

    async def get_verification_method(self, proof: dict, document_loader: callable):

        verification_method = proof.get("verificationMethod")
        if not verification_method:
            raise Exception('No "verificationMethod" found in proof')

        framed = await jsonld.frame(
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

    @abstractmethod
    def sign(self, verify_data: bytes, proof: dict):
        pass

    @abstractmethod
    def verify_signature(
        self, verify_data: bytes, verification_method: dict, proof: dict
    ):
        pass


__all__ = [LinkedDataSignature]
