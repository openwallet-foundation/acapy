from typing import Any, Awaitable, Callable, Mapping
import asyncio

from pyld import jsonld
from ..ld_proofs import (
    DocumentLoader,
    LinkedDataSignature,
    ProofPurpose,
    AuthenticationProofPurpose,
    verify as ld_proofs_verify,
)
from .checker import check_credential
from .purposes import IssueCredentialProofPurpose


async def _verify_credential(
    credential: dict,
    controller: dict,
    document_loader: DocumentLoader,
    suite: LinkedDataSignature,
    purpose: ProofPurpose = None,
    check_status: Callable = None,
) -> Awaitable(dict):
    # TODO: validate credential structure

    if credential["credentialStatus"] and not check_status:
        raise Exception(
            'A "check_status function must be provided to verify credentials with "credentialStatus" set.'
        )

    if not purpose:
        purpose = IssueCredentialProofPurpose()

    result = await ld_proofs_verify(
        document=credential,
        suite=suite,
        purpose=purpose,
        document_loader=document_loader,
    )

    if not result["verified"]:
        return result

    if credential["credentialStatus"]:
        # CHECK make sure this is how check_status should be called
        result["credentialStatus"] = await check_status(credential)

    if not result["statusResult"]["verified"]:
        result["verified"] = False

    return result


async def verify_credential(
    credential: dict,
    controller: dict,
    document_loader: DocumentLoader,
    suite: LinkedDataSignature,
    purpose: ProofPurpose = None,
    check_status: Callable = None,
) -> dict:
    try:
        return await _verify_credential(
            credential, controller, document_loader, suite, purpose, check_status
        )
    except Exception as e:
        return {
            "verified": False,
            "results": [{"credential": credential, "verified": False, "error": e}],
            "error": e,
        }


async def _verify_presentation(
    challenge: str,
    presentation: dict = None,
    purpose: LinkedDataSignature = None,
    unsigned_presentation: dict = None,
    suite_map: Mapping[str, LinkedDataSignature] = None,
    suite: LinkedDataSignature = None,
    controller: dict = None,
    domain: str = None,
    document_loader: DocumentLoader = None,
):
    if presentation and unsigned_presentation:
        raise Exception(
            'Either "presentation" or "unsigned_presentation" must be present, not both.'
        )

    if not purpose:
        purpose = AuthenticationProofPurpose(controller, challenge, domain=domain)

    vp, presentation_result = None, None

    if presentation:
        # TODO validate presentation structure here

        vp = presentation

        if "proof" not in vp:
            raise Exception('presentation must contain "proof"')

        if not purpose and not challenge:
            raise Exception(
                'A "challenge" param is required for AuthenticationProofPurpose.'
            )

        suite = suite_map[presentation["proof"]["type"]]()

        presentation_result = await ld_proofs_verify(
            document=presentation,
            suite=suite,
            purpose=purpose,
            document_loader=document_loader,
        )

    if unsigned_presentation:
        # TODO check presentation here
        vp = unsigned_presentation

        if vp["proof"]:
            raise Exception('"unsigned_presentation" must not contain "proof"')

    credential_results = None
    verified = True

    credentials = jsonld.get_values(vp, "verifiableCredential")

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

    if unsigned_presentation:
        return {
            "verified": verified,
            "results": [vp],
            "credential_results": credential_results,
        }

    return {
        "presentation_result": presentation_result,
        "verified": verified and presentation_result["verified"],
        "credential_results": credential_results,
        "error": presentation_result["error"],
    }


async def verify(
    challenge: str,
    presentation: dict = None,
    purpose: LinkedDataSignature = None,
    unsigned_presentation: dict = None,
    suite_map: Mapping[str, LinkedDataSignature] = None,
    suite: LinkedDataSignature = None,
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
            "results": [
                {"presentation": presentation, "verified": False, "error": error}
            ],
            "error": error,
        }


__all__ = [verify, verify_credential]
