from ..ld_proofs import LinkedDataSignature, ProofPurpose, sign, did_key_document_loader
from .purposes import IssueCredentialProofPurpose
from .checker import check_credential


async def issue(
    credential: dict, suite: LinkedDataSignature, *, purpose: ProofPurpose = None
) -> dict:
    # TODO: validate credential format

    if not purpose:
        purpose = IssueCredentialProofPurpose()

    signed_credential = await sign(
        document=credential,
        suite=suite,
        purpose=purpose,
        document_loader=did_key_document_loader,
    )
    return signed_credential
