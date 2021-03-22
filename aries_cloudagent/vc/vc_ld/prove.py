from typing import List


from ..ld_proofs import (
    AuthenticationProofPurpose,
    ProofPurpose,
    DocumentLoader,
    sign,
    LinkedDataProof,
    LinkedDataProofException,
)
from ..ld_proofs.constants import CREDENTIALS_V1_URL
from .models.credential_schema import VerifiableCredentialSchema


async def create_presentation(
    *, credentials: List[dict], presentation_id: str = None
) -> dict:
    presentation = {
        "@context": [CREDENTIALS_V1_URL],
        "type": ["VerifiablePresentation"],
    }

    # Validate structure of all credentials
    errors = VerifiableCredentialSchema().validate(credentials, many=True)
    if len(errors) > 0:
        raise LinkedDataProofException(
            f"Not all credentials have a valid structure: {errors}"
        )

    presentation["verifiableCredential"] = credentials

    if presentation_id:
        presentation["id"] = presentation_id

    return presentation


async def sign_presentation(
    *,
    presentation: dict,
    suite: LinkedDataProof,
    document_loader: DocumentLoader,
    challenge: str = None,
    domain: str = None,
    purpose: ProofPurpose = None,
):
    if not purpose and not challenge:
        raise LinkedDataProofException(
            'A "challenge" param is required when not providing a "purpose" (for AuthenticationProofPurpose).'
        )
    if not purpose:
        purpose = AuthenticationProofPurpose(challenge=challenge, domain=domain)

    # TODO: validate structure of presentation

    return await sign(
        document=presentation,
        suite=suite,
        purpose=purpose,
        document_loader=document_loader,
    )
