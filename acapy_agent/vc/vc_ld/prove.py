"""Verifiable Credential and Presentation proving methods."""

from typing import List, Optional

from ..ld_proofs import (
    AuthenticationProofPurpose,
    DocumentLoaderMethod,
    LinkedDataProof,
    LinkedDataProofException,
    ProofPurpose,
    derive,
    sign,
)
from ..ld_proofs.constants import CREDENTIALS_CONTEXT_V1_URL, CREDENTIALS_CONTEXT_V2_URL
from .models.credential import VerifiableCredentialSchema


def _context_urls(credential: dict) -> List[str]:
    """Return a raw credential dict's `@context` entries that are string URLs.

    `create_presentation` receives credentials as plain dicts (not `VerifiableCredential`
    model instances), so this mirrors `VerifiableCredential.context_urls` for that shape
    without requiring a full model parse.
    """
    context = credential.get("@context") or []
    if isinstance(context, str):
        context = [context]
    return [url for url in context if isinstance(url, str)]


def _presentation_context(credentials: List[dict]) -> List[str]:
    """Choose the `@context` for a presentation wrapping the given credentials.

    A Verifiable Presentation's own `@context` must be able to resolve the proof object
    that will later be added to the *presentation itself* by `sign_presentation` — not
    just whatever the embedded credentials already declare. Defaulting to VCDM 1.1
    unconditionally (the previous behaviour) produces a structurally invalid document
    when every embedded credential is VCDM 2.0: VCDM 1.1's base context does not define
    Data Integrity proof terms (`verificationMethod`, `created`, `proofPurpose`,
    `challenge`), VCDM 2.0's base context alone does not either (confirmed directly —
    only `proof`/`type` survive JSON-LD expansion), and those terms are only resolved
    once the relevant suite-specific security context (e.g. the Ed25519-2020 or BBS+
    context `prepare_credential` already attaches to a credential at issuance time) is
    also present. If every credential is VCDM 2.0, use VCDM 2.0 for the presentation
    too, and carry over any additional context entries already present on the
    credentials (ignoring the base context itself) so that a suite-specific context
    used by the credential(s) is also available to the presentation's own proof. Mixed
    VCDM 1.1/2.0 credentials are not well-defined by the spec; this conservatively
    falls back to VCDM 1.1 (the original behaviour) in that case, same as when there
    are no credentials at all.
    """
    if credentials and all(
        _context_urls(credential)[:1] == [CREDENTIALS_CONTEXT_V2_URL]
        for credential in credentials
    ):
        context = [CREDENTIALS_CONTEXT_V2_URL]
        for credential in credentials:
            for url in _context_urls(credential)[1:]:
                if url not in context:
                    context.append(url)
        return context

    return [CREDENTIALS_CONTEXT_V1_URL]


async def create_presentation(
    *, credentials: List[dict], presentation_id: Optional[str] = None
) -> dict:
    """Create presentation and add the credentials to it.

    Will validates the structure off all credentials, but does
    not sign the presentation yet. Call sing_presentation to do this.

    Args:
        credentials (List[dict]): Credentials to add to the presentation
        presentation_id (str, optional): Id of the presentation. Defaults to None.

    Raises:
        LinkedDataProofException: When not all credentials have a valid structure

    Returns:
        dict: The unsigned presentation object

    """
    presentation = {
        "@context": _presentation_context(credentials),
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
    purpose: Optional[ProofPurpose] = None,
    challenge: Optional[str] = None,
    domain: Optional[str] = None,
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
