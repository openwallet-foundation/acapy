"""Verifiable Credential and Presentation verification methods."""

import asyncio
from typing import List
from pyld.jsonld import JsonLdProcessor

from ...core.profile import Profile
from ...anoncreds.verifier import AnonCredsVerifier
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
from ..vc_ld.models.credential import VerifiableCredentialSchema
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
            anoncreds_pres_req,
            presentation,
        )
    except Exception as e:
        raise e
        # return PresentationVerificationResult(verified=False, errors=[e])


__all__ = ["verify_presentation", "verify_credential"]
