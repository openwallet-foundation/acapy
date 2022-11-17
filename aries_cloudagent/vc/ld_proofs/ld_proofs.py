"""Linked data proof signing and verification methods."""

from typing import List

from .document_loader import DocumentLoaderMethod
from .proof_set import ProofSet
from .purposes import _ProofPurpose as ProofPurpose
from .suites import _LinkedDataProof as LinkedDataProof
from .validation_result import DocumentVerificationResult


async def sign(
    *,
    document: dict,
    suite: LinkedDataProof,
    purpose: ProofPurpose,
    document_loader: DocumentLoaderMethod,
) -> dict:
    """Cryptographically signs the provided document by adding a `proof` section.

    Proof is added based on the provided suite and proof purpose

    Args:
        document (dict): JSON-LD document to be signed.
        suite (LinkedDataProof): The linked data signature cryptographic suite
            with which to sign the document
        purpose (ProofPurpose): A proof purpose instance that will match proofs to be
            verified and ensure they were created according to the appropriate purpose.
        document_loader (DocumentLoader): The document loader to use.

    Raises:
        LinkedDataProofException: When a jsonld url cannot be resolved, OR signing fails.
    Returns:
        dict: Signed document.

    """
    return await ProofSet.add(
        document=document,
        suite=suite,
        purpose=purpose,
        document_loader=document_loader,
    )


async def verify(
    *,
    document: dict,
    suites: List[LinkedDataProof],
    purpose: ProofPurpose,
    document_loader: DocumentLoaderMethod,
) -> DocumentVerificationResult:
    """Verify the linked data signature on the provided document.

    Args:
        document (dict): The document with one or more proofs to be verified.
        suites (List[LinkedDataProof]): Acceptable signature suite instances for
            verifying the proof(s).
        purpose (ProofPurpose): A proof purpose instance that will match proofs to be
            verified and ensure they were created according to the appropriate purpose.
        document_loader (DocumentLoader): The document loader to use.

    Returns:
        DocumentVerificationResult: Object with a `verified` boolean property that is
            `True` if at least one proof matching the given purpose and suite verifies
            and `False` otherwise. a `results` property with an array of detailed
            results. if `False` an `errors` property will be present, with a list
            containing all of the errors that occurred during the verification process.

    """

    result = await ProofSet.verify(
        document=document,
        suites=suites,
        purpose=purpose,
        document_loader=document_loader,
    )

    return result


async def derive(
    *,
    document: dict,
    reveal_document: dict,
    suite: LinkedDataProof,
    document_loader: DocumentLoaderMethod,
    nonce: bytes = None,
) -> dict:
    """Derive proof(s) for document with reveal document.

    All proofs matching the signature suite type will be replaced with a derived
    proof. Other proofs will be discarded.

    Args:
        document (dict): The document with one or more proofs to be derived
        reveal_document (dict): The JSON-LD frame specifying the revealed attributes
        suite (LinkedDataProof): The linked data signature cryptographic suite
            with which to derive the proof
        document_loader (DocumentLoader): The document loader to use.
        nonce (bytes, optional): Nonce to use for the proof. Defaults to None.

    Returns:
        dict: The document with derived proof(s).

    """

    result = await ProofSet.derive(
        document=document,
        reveal_document=reveal_document,
        suite=suite,
        document_loader=document_loader,
        nonce=nonce,
    )

    return result
