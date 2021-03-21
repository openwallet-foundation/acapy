import asyncio
from pyld.jsonld import JsonLdProcessor
from typing import Mapping

from ..ld_proofs import (
    LinkedDataProof,
    CredentialIssuancePurpose,
    DocumentLoader,
    ProofPurpose,
    AuthenticationProofPurpose,
    verify as ld_proofs_verify,
)


async def _verify_credential(
    *,
    credential: dict,
    document_loader: DocumentLoader,
    suite: LinkedDataProof,
    purpose: ProofPurpose = None,
) -> dict:
    # TODO: validate credential structure

    if not purpose:
        purpose = CredentialIssuancePurpose()

    result = await ld_proofs_verify(
        document=credential,
        suites=[suite],
        purpose=purpose,
        document_loader=document_loader,
    )

    return result


async def verify_credential(
    *,
    credential: dict,
    suite: LinkedDataProof,
    document_loader: DocumentLoader,
    purpose: ProofPurpose = None,
) -> dict:
    try:
        return await _verify_credential(
            credential=credential,
            document_loader=document_loader,
            suite=suite,
            purpose=purpose,
        )
    except Exception as e:
        # TODO: use class instance OR typed dict, as this is confusing
        return {
            "verified": False,
            "results": [{"credential": credential, "verified": False, "error": e}],
            "error": e,
        }


async def _verify_presentation(
    *,
    presentation: dict,
    challenge: str = None,
    domain: str = None,
    purpose: ProofPurpose = None,
    suite_map: Mapping[str, LinkedDataProof] = None,
    suite: LinkedDataProof = None,
    document_loader: DocumentLoader = None,
):

    if not purpose and not challenge:
        raise Exception(
            'A "challenge" param is required for AuthenticationProofPurpose.'
        )
    if not purpose:
        purpose = AuthenticationProofPurpose(challenge=challenge, domain=domain)

    # TODO validate presentation structure here
    if "proof" not in presentation:
        raise Exception('presentation must contain "proof"')

    proof_type = presentation.get("proof").get("type")
    suite = suite_map[proof_type]

    presentation_result = await ld_proofs_verify(
        document=presentation,
        suite=suite,
        purpose=purpose,
        document_loader=document_loader,
    )

    credential_results = None
    verified = True

    credentials = JsonLdProcessor.get_values(presentation, "verifiableCredential")

    def v(credential: dict):
        if suite_map:
            suite = suite_map[credential["proof"]["type"]]()
        return verify_credential(credential, suite, purpose)

    credential_results = asyncio.gather(*[v(x) for x in credentials])

    def d(cred: dict, index: int):
        cred["credentialId"] = credentials[index]["id"]
        return cred

    credential_results = [d(x, i) for x, i in enumerate(credential_results)]

    verified = all([x["verified"] for x in credential_results])

    return {
        "presentation_result": presentation_result,
        "verified": verified and presentation_result["verified"],
        "credential_results": credential_results,
        "error": presentation_result["error"],
    }


async def verify_presentation(
    *,
    presentation: dict = None,
    challenge: str,
    purpose: ProofPurpose = None,
    suite_map: Mapping[str, LinkedDataProof] = None,
    suite: LinkedDataProof = None,
    controller: dict = None,
    domain: str = None,
    document_loader: DocumentLoader = None,
):

    try:
        if not presentation and not unsigned_presentation:
            raise TypeError(
                'A "presentation" or "unsignedPresentation" property is required for verifying.'
            )

        return await _verify_presentation(
            presentation=presentation,
            unsigned_presentation=unsigned_presentation,
            challenge=challenge,
            purpose=purpose,
            suite=suite,
            suite_map=suite_map,
            controller=controller,
            domain=domain,
            document_loader=document_loader,
        )
    except Exception as e:
        return {
            "verified": False,
            "results": [{"presentation": presentation, "verified": False, "error": e}],
            "error": e,
        }


__all__ = [verify_presentation, verify_credential]
