from ..ld_proofs import (
    LinkedDataProof,
    ProofPurpose,
    sign,
    CredentialIssuancePurpose,
    DocumentLoader,
    LinkedDataProofException,
)
from .models.credential_schema import CredentialSchema


async def issue(
    *,
    credential: dict,
    suite: LinkedDataProof,
    document_loader: DocumentLoader,
    purpose: ProofPurpose = None,
) -> dict:
    # Validate credential
    errors = CredentialSchema().validate(credential)
    if len(errors) > 0:
        raise LinkedDataProofException(
            f"Credential contains invalid structure: {errors}"
        )

    if not purpose:
        purpose = CredentialIssuancePurpose()

    signed_credential = await sign(
        document=credential,
        suite=suite,
        purpose=purpose,
        document_loader=document_loader,
    )

    return signed_credential
