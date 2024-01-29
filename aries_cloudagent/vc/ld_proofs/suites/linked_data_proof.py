"""Abstract base class for linked data proofs."""

from aiohttp import ClientSession
from abc import ABC
from typing import ClassVar, List, Optional, Union

from pyld import jsonld
from typing_extensions import TypedDict


from ..check import get_properties_without_context
from ..constants import SECURITY_CONTEXT_URL
from ..document_loader import DocumentLoaderMethod
from ..error import LinkedDataProofException
from ..purposes import _ProofPurpose as ProofPurpose
from ..validation_result import ProofResult


class DeriveProofResult(TypedDict):
    """Result dict for deriving a proof."""

    document: dict
    proof: Union[dict, List[dict]]


class LinkedDataProof(ABC):
    """Base Linked data proof."""

    signature_type: ClassVar[str]

    def __init__(
        self,
        *,
        proof: Optional[dict] = None,
        supported_derive_proof_types: Optional[List[str]] = None,
    ):
        """Initialize new LinkedDataProof instance."""
        self.proof = proof
        self.supported_derive_proof_types = supported_derive_proof_types

    async def create_proof(
        self,
        *,
        document: dict,
        purpose: ProofPurpose,
        document_loader: DocumentLoaderMethod,
    ) -> dict:
        """Create proof for document.

        Args:
            document (dict): The document to create the proof for
            purpose (ProofPurpose): The proof purpose to include in the proof
            document_loader (DocumentLoader): Document loader used for resolving

        Returns:
            dict: The proof object

        """
        raise LinkedDataProofException(
            f"{self.signature_type} signature suite does not support creating proofs"
        )

    async def verify_proof(
        self,
        *,
        proof: dict,
        document: dict,
        purpose: ProofPurpose,
        document_loader: DocumentLoaderMethod,
    ) -> ProofResult:
        """Verify proof against document and proof purpose.

        Args:
            proof (dict): The proof to verify
            document (dict): The document to verify the proof against
            purpose (ProofPurpose): The proof purpose to verify the proof against
            document_loader (DocumentLoader): Document loader used for resolving

        Returns:
            ValidationResult: The results of the proof verification

        """
        raise LinkedDataProofException(
            f"{self.signature_type} signature suite does not support verifying proofs"
        )

    async def derive_proof(
        self,
        *,
        proof: dict,
        document: dict,
        reveal_document: dict,
        document_loader: DocumentLoaderMethod,
        nonce: Optional[bytes] = None,
    ) -> DeriveProofResult:
        """Derive proof for document, returning derived document and proof.

        Args:
            proof (dict): The proof to derive from
            document (dict): The document to derive the proof for
            reveal_document (dict): The JSON-LD frame the revealed attributes
            document_loader (DocumentLoader): Document loader used for resolving
            nonce (bytes, optional): Nonce to use for the proof. Defaults to None.

        Returns:
            DeriveProofResult: The derived document and proof

        """
        raise LinkedDataProofException(
            f"{self.signature_type} signature suite does not support deriving proofs"
        )

    def _canonize(self, *, input, document_loader: DocumentLoaderMethod) -> str:
        """Canonize input document using URDNA2015 algorithm."""
        # application/n-quads format always returns str
        missing_properties = get_properties_without_context(input, document_loader)

        if len(missing_properties) > 0:
            raise LinkedDataProofException(
                f"{len(missing_properties)} attributes dropped. "
                f"Provide definitions in context to correct. {missing_properties}"
            )

        return jsonld.normalize(
            input,
            {
                "algorithm": "URDNA2015",
                "format": "application/n-quads",
                "documentLoader": document_loader,
            },
        )

    async def _get_verification_method(
        self, *, proof: dict, document_loader: DocumentLoaderMethod
    ) -> dict:
        """Get verification method for proof."""

        verification_method = proof.get("verificationMethod")

        if isinstance(verification_method, dict):
            verification_method: str = verification_method.get("id")
        if not verification_method:
            raise LinkedDataProofException('No "verificationMethod" found in proof')

        # if the verification method is a did:web: url, we resolve the document first
        # then remove the traceability context if present before framing it
        # this is to avoid framing errors that could arise from this context
        if verification_method[:8] == "did:web:":
            did = verification_method[8:].split("#")[0]
            did_endpoint = (
                f'https://{did.replace(":", "/")}/did.json'
                if ":" in did
                else f'https://{did}/.well-known/did.json'
            )
            async with ClientSession() as session:
                async with session.get(did_endpoint) as resp:
                    did_document = await resp.json()
            # framed = next((sub for sub in did_document['verificationMethod'] if sub['id'] == verification_method), None)
            framed = jsonld.frame(
                did_document,
                frame={
                    "@context": SECURITY_CONTEXT_URL,
                    "@embed": "@always",
                    "id": verification_method,
                },
                options={
                    # "documentLoader": document_loader,
                    "expandContext": SECURITY_CONTEXT_URL,
                    # if we don't set base explicitly it will remove the base in returned
                    # document (e.g. use key:z... instead of did:key:z...)
                    # same as compactToRelative in jsonld.js
                    # "base": None,
                },
            )
        else:
            # TODO: This should optionally use the context of the document?
            framed = jsonld.frame(
                verification_method,
                frame={
                    "@context": SECURITY_CONTEXT_URL,
                    "@embed": "@always",
                    "id": verification_method,
                },
                options={
                    "documentLoader": document_loader,
                    "expandContext": SECURITY_CONTEXT_URL,
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

    def match_proof(self, signature_type: str) -> bool:
        """Match signature type to signature type of this suite."""
        return signature_type == self.signature_type
