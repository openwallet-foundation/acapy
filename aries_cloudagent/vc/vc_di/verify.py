"""Verifiable Credential and Presentation verification methods."""

from ...core.profile import Profile
from ...anoncreds.verifier import AnonCredsVerifier
from ..ld_proofs import (
    ProofPurpose,
)
from ..vc_ld.validation_result import PresentationVerificationResult
from .prove import create_signed_anoncreds_presentation


async def verify_signed_anoncredspresentation(
    *,
    profile: Profile,
    presentation: dict,
    purpose: ProofPurpose = None,
    challenge: str = None,
    domain: str = None,
    pres_req: dict = None,
) -> PresentationVerificationResult:
    """Verify presentation structure, credentials, proof purpose and signature.

    Args:
        profile (Profile): The profile to use for verification
        presentation (dict): The presentation to verify
        purpose (ProofPurpose, optional): Proof purpose to use.
        challenge (str, optional): The challenge to use for authentication.
        domain (str, optional): Domain to use for the authentication proof purpose.
        pres_req (dict, optional): The presentation request to verify against.

    Returns:
        PresentationVerificationResult: The result of the verification. Verified property
            indicates whether the verification was successful

    """

    # TODO: I think we should add some sort of options to authenticate the subject id
    # to the presentation verification method controller
    anoncreds_verifier = AnonCredsVerifier(profile)

    credentials = presentation["verifiableCredential"]
    pres_definition = pres_req["presentation_definition"]

    (anoncreds_pres_req, _signed_vp, cred_metadata) = (
        await create_signed_anoncreds_presentation(
            profile=profile,
            pres_definition=pres_definition,
            presentation=presentation,
            credentials=credentials,
            challenge=challenge,
            domain=domain,
            holder=False,
        )
    )

    try:
        return await anoncreds_verifier.verify_presentation_w3c(
            anoncreds_pres_req, presentation, cred_metadata
        )
    except Exception as e:
        raise e
        # return PresentationVerificationResult(verified=False, errors=[e])
