"""Verifiable Credential and Presentation verification methods."""

import asyncio
from typing import List
from pyld.jsonld import JsonLdProcessor

from ..ld_proofs import (
    LinkedDataProof,
    CredentialIssuancePurpose,
    DocumentLoaderMethod,
    ProofPurpose,
    AuthenticationProofPurpose,
    verify as ld_proofs_verify,
    DocumentVerificationResult,
    LinkedDataProofException,
)
from .models.credential import VerifiableCredentialSchema
from .validation_result import PresentationVerificationResult


async def _verify_credential(
    *,
    credential: dict,
    suites: List[LinkedDataProof],
    document_loader: DocumentLoaderMethod,
    purpose: ProofPurpose = None,
) -> DocumentVerificationResult:
    """Verify credential structure, proof purpose and signature."""

    # Validate credential structure
    errors = VerifiableCredentialSchema().validate(credential)
    if len(errors) > 0:
        raise LinkedDataProofException(
            f"Unable to verify credential with invalid structure: {errors}"
        )

    if not purpose:
        purpose = CredentialIssuancePurpose()

    result = await ld_proofs_verify(
        document=credential,
        suites=suites,
        purpose=purpose,
        document_loader=document_loader,
    )

    return result


async def verify_credential(
    *,
    credential: dict,
    suites: List[LinkedDataProof],
    document_loader: DocumentLoaderMethod,
    purpose: ProofPurpose = None,
) -> DocumentVerificationResult:
    """Verify credential structure, proof purpose and signature.

    Args:
        credential (dict): The credential to verify
        suites (List[LinkedDataProof]): The signature suites to verify with
        document_loader (DocumentLoader): Document loader used for resolving of documents
        purpose (ProofPurpose, optional): Proof purpose to use.
            Defaults to CredentialIssuancePurpose

    Returns:
        DocumentVerificationResult: The result of the verification. Verified property
            indicates whether the verification was successful

    """
    try:
        return await _verify_credential(
            credential=credential,
            document_loader=document_loader,
            suites=suites,
            purpose=purpose,
        )
    except Exception as e:
        return DocumentVerificationResult(
            verified=False, document=credential, errors=[e]
        )


async def _verify_presentation(
    *,
    presentation: dict,
    suites: List[LinkedDataProof],
    document_loader: DocumentLoaderMethod,
    challenge: str = None,
    domain: str = None,
    purpose: ProofPurpose = None,
):
    """Verify presentation structure, credentials, proof purpose and signature."""

    if not purpose and not challenge:
        raise LinkedDataProofException(
            'A "challenge" param is required for AuthenticationProofPurpose.'
        )
    elif not purpose:
        purpose = AuthenticationProofPurpose(challenge=challenge, domain=domain)

    # TODO validate presentation structure here
    if "proof" not in presentation:
        raise LinkedDataProofException('presentation must contain "proof"')

    presentation_result = await ld_proofs_verify(
        document=presentation,
        suites=suites,
        purpose=purpose,
        document_loader=document_loader,
    )

    credential_results = None
    verified = True

    credentials = JsonLdProcessor.get_values(presentation, "verifiableCredential")
    credential_results = await asyncio.gather(
        *[
            verify_credential(
                credential=credential,
                suites=suites,
                document_loader=document_loader,
                # FIXME: we don't want to interhit the authentication purpose
                # from the presentation. However we do want to have subject
                # authentication I guess
                # purpose=purpose,
            )
            for credential in credentials
        ]
    )

    verified = all([result.verified for result in credential_results])

    return PresentationVerificationResult(
        verified=verified,
        presentation_result=presentation_result,
        credential_results=credential_results,
        errors=presentation_result.errors,
    )


async def verify_presentation(
    *,
    presentation: dict,
    suites: List[LinkedDataProof],
    document_loader: DocumentLoaderMethod,
    purpose: ProofPurpose = None,
    challenge: str = None,
    domain: str = None,
) -> PresentationVerificationResult:
    """Verify presentation structure, credentials, proof purpose and signature.

    Args:
        presentation (dict): The presentation to verify
        suites (List[LinkedDataProof]): The signature suites to verify with
        document_loader (DocumentLoader): Document loader used for resolving of documents
        purpose (ProofPurpose, optional): Proof purpose to use.
            Defaults to AuthenticationProofPurpose
        challenge (str, optional): The challenge to use for authentication.
            Required if purpose is not passed, not used if purpose is passed
        domain (str, optional): Domain to use for the authentication proof purpose.
            Not used if purpose is passed

    Returns:
        PresentationVerificationResult: The result of the verification. Verified property
            indicates whether the verification was successful

    """

    # TODO: I think we should add some sort of options to authenticate the subject id
    # to the presentation verification method controller

    try:
        return await _verify_presentation(
            presentation=presentation,
            challenge=challenge,
            purpose=purpose,
            suites=suites,
            domain=domain,
            document_loader=document_loader,
        )
    except Exception as e:
        return PresentationVerificationResult(verified=False, errors=[e])


__all__ = ["verify_presentation", "verify_credential"]
