"""Verifiable Credential and Presentation verification methods."""

from typing import Optional

from anoncreds import AnoncredsError

from acapy_agent.anoncreds.holder import AnonCredsHolderError

from ...anoncreds.verifier import AnonCredsVerifier
from ...core.profile import Profile
from ..ld_proofs import ProofPurpose
from ..vc_ld.validation_result import PresentationVerificationResult
from .prove import _load_w3c_credentials, prepare_data_for_presentation


async def verify_signed_anoncredspresentation(
    *,
    profile: Profile,
    presentation: dict,
    purpose: Optional[ProofPurpose] = None,
    challenge: Optional[str] = None,
    domain: Optional[str] = None,
    pres_req: Optional[dict] = None,
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
    w3c_creds = await _load_w3c_credentials(credentials)

    (anoncreds_pres_req, cred_metadata) = await prepare_data_for_presentation(
        presentation=presentation,
        w3c_creds=w3c_creds,
        pres_definition=pres_definition,
        profile=profile,
        challenge=challenge,
    )

    try:
        return await anoncreds_verifier.verify_presentation_w3c(
            anoncreds_pres_req, presentation, cred_metadata
        )
    except AnoncredsError as err:
        raise AnonCredsHolderError("Error loading master secret") from err
