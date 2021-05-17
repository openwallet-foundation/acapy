"""Verifiable Credential and Presentation proving methods."""

from typing import List


from ..ld_proofs import (
    AuthenticationProofPurpose,
    ProofPurpose,
    DocumentLoaderMethod,
    sign,
    LinkedDataProof,
    LinkedDataProofException,
    derive,
)
from ..ld_proofs.constants import CREDENTIALS_CONTEXT_V1_URL
from .models.credential import VerifiableCredentialSchema


async def create_presentation(
    *, credentials: List[dict], presentation_id: str = None
) -> dict:
    """Create presentation and add the credentials to it.

    Will validates the structure off all credentials, but does
    not sign the presentation yet. Call sing_presentation to do this.

    Args:
        credentials (List[dict]): Credentails to add to the presentation
        presentation_id (str, optional): Id of the presentation. Defaults to None.

    Raises:
        LinkedDataProofException: When not all credentials have a valid structure

    Returns:
        dict: The unsigned presentation object

    """
    presentation = {
        "@context": [CREDENTIALS_CONTEXT_V1_URL],
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
    document_loader: DocumentLoaderMethod,
    purpose: ProofPurpose = None,
    challenge: str = None,
    domain: str = None,
) -> dict:
    """Sign the presentation with the passed signature suite.

    Will set a default AuthenticationProofPurpose if no proof purpose is passed.

    Args:
        presentation (dict): The presentation to sign
        suite (LinkedDataProof): The signature suite to sign the presentation with
        document_loader (DocumentLoader): Document loader to use.
        purpose (ProofPurpose, optional): Purpose to use. Required if challenge is None
        challenge (str, optional): Challenge to use. Required if domain is None.
        domain (str, optional): Domain to use. Only used if purpose is None.

    Raises:
        LinkedDataProofException: When both purpose and challenge are not provided
            And when signing of the presentation fails

    Returns:
        dict: A verifiable presentation object

    """
    if not purpose and not challenge:
        raise LinkedDataProofException(
            'A "challenge" param is required when not providing a'
            ' "purpose" (for AuthenticationProofPurpose).'
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


async def derive_credential(
    *,
    credential: dict,
    reveal_document: dict,
    suite: LinkedDataProof,
    document_loader: DocumentLoaderMethod,
) -> dict:
    """Derive new credential from the existing credential and the reveal document.

    All proofs matching the signature suite type will be replaced with a derived
    proof. Other proofs will be discarded.

    Args:
        credential (dict): The credential to derive the new credential from.
        reveal_document (dict): JSON-LD frame to select which attributes to include.
        suite (LinkedDataProof): The signature suite to use for derivation
        document_loader (DocumentLoader): The document loader to use.

    Returns:
        dict: The derived credential.

    """

    # Validate credential structure
    errors = VerifiableCredentialSchema().validate(credential)
    if len(errors) > 0:
        raise LinkedDataProofException(
            f"Unable to derive from credential with invalid structure: {errors}"
        )

    return await derive(
        document=credential,
        reveal_document=reveal_document,
        suite=suite,
        document_loader=document_loader,
    )
