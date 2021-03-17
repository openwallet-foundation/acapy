"""Linked data proof signing and verification methods."""

from typing import List
from pyld.jsonld import JsonLdError

from .document_loader import DocumentLoader
from .ProofSet import ProofSet
from .purposes import ProofPurpose
from .suites import LinkedDataProof
from .VerificationException import VerificationException


async def sign(
    *,
    document: dict,
    # TODO: support multiple signature suites
    suite: LinkedDataProof,
    purpose: ProofPurpose,
    document_loader: DocumentLoader,
) -> dict:
    """Cryptographically signs the provided document by adding a `proof` section.

    Proof is added based on the provided suite and proof purpose

    Args:
        document (dict): The document to be signed.
        suite (LinkedDataProof): The linked data signature cryptographic suite
            with which to sign the document
        purpose (ProofPurpose): A proof purpose instance that will match proofs to be
            verified and ensure they were created according to the appropriate purpose.
        document_loader (DocumentLoader): The document loader to use.

    Raises:
        Exception: When a jsonld url cannot be resolved, OR signing fails.
    Returns:
        dict: Signed document.
    """
    try:
        return await ProofSet.add(
            document=document,
            suite=suite,
            purpose=purpose,
            document_loader=document_loader,
        )

    except JsonLdError as e:
        if e.type == "jsonld.InvalidUrl":
            raise Exception(
                f'A URL "{e.details}" could not be fetched; you need to pass a DocumentLoader function that can resolve this URL, or resolve the URL before calling "sign".'
            )
        raise e


async def verify(
    *,
    document: dict,
    suites: List[LinkedDataProof],
    purpose: ProofPurpose,
    document_loader: DocumentLoader,
) -> dict:
    """Verifies the linked data signature on the provided document.

    Args:
        document (dict): The document with one or more proofs to be verified.
        suites (List[LinkedDataProof]): Acceptable signature suite instances for
            verifying the proof(s).
        purpose (ProofPurpose): A proof purpose instance that will match proofs to be
            verified and ensure they were created according to the appropriate purpose.
        document_loader (DocumentLoader): The document loader to use.

    Returns:
        dict: Dict with a `verified` boolean property that is `True` if at least one
            proof matching the given purpose and suite verifies and `False` otherwise.
            a `results` property with an array of detailed results.
            if `False` an `error` property will be present, with `error.errors`
            containing all of the errors that occurred during the verification process.
    """

    result = await ProofSet.verify(
        document=document,
        suites=suites,
        purpose=purpose,
        document_loader=document_loader,
    )

    if result.get("error"):
        # TODO: is this necessary? Seems like it is vc-js specific
        # TODO: error returns list, not object with type??
        # if result.get("error", {}).get("type") == "jsonld.InvalidUrl":
        #     url_err = Exception(
        #         f'A URL "{result.get("error").get("details")}" could not be fetched; you need to pass a DocumentLoader function that can resolve this URL, or resolve the URL before calling "sign".'
        #     )
        #     result["error"] = VerificationException(url_err)
        # else:
        result["error"] = VerificationException(result.get("error"))

    return result
