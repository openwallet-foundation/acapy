"""Verifiable Credential issuance methods."""

from ..ld_proofs import (
    LinkedDataProof,
    ProofPurpose,
    sign,
    CredentialIssuancePurpose,
    DocumentLoaderMethod,
    LinkedDataProofException,
)
from ..ld_proofs.constants import (
    CREDENTIALS_CONTEXT_V1_URL,
    CREDENTIALS_CONTEXT_V2_URL,
)
from .models.credential import CredentialSchema
from .models.credentialv2 import CredentialV2Schema


async def issue(
    *,
    credential: dict,
    suite: LinkedDataProof,
    document_loader: DocumentLoaderMethod,
    purpose: ProofPurpose = None,
) -> dict:
    """Issue a verifiable credential.

    Takes the base credential document, verifies it, and adds
    a digital signature to it.

    Args:
        credential (dict): Base credential document.
        suite (LinkedDataProof): Signature suite to sign the credential with.
        document_loader (DocumentLoader): Document loader to use
        purpose (ProofPurpose, optional): A proof purpose instance that will match
            proofs to be verified and ensure they were created according to the
            appropriate purpose. Default to CredentialIssuancePurpose

    Raises:
        LinkedDataProofException: When the credential has an invalid structure
            OR signing fails

    Returns:
        dict: The signed verifiable credential

    """
    # Validate credential
    if credential["@context"][0] == CREDENTIALS_CONTEXT_V1_URL:
        errors = CredentialSchema().validate(credential)
    elif credential["@context"][0] == CREDENTIALS_CONTEXT_V2_URL:
        errors = CredentialV2Schema().validate(credential)
    if len(errors) > 0:
        raise LinkedDataProofException(
            f"Credential contains invalid structure: {errors}"
        )

    # Set default proof purpose if not set
    if not purpose:
        purpose = CredentialIssuancePurpose()

    # Sign the credential with LD proof
    signed_credential = await sign(
        document=credential,
        suite=suite,
        purpose=purpose,
        document_loader=document_loader,
    )

    return signed_credential
