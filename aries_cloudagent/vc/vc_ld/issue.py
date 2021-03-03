from typing import Any


from ..ld_proofs import LinkedDataSignature, ProofPurpose, sign, document_loader
from .purposes import IssueCredentialProofPurpose
from .checker import check_credential


def issue(
    credential: dict, suite: LinkedDataSignature, *, purpose: ProofPurpose = None
):
    # TODO: validate credential format

    if not purpose:
        purpose = IssueCredentialProofPurpose()

    signed_credential = sign(
        document=credential,
        suite=suite,
        purpose=purpose,
        document_loader=document_loader,
    )
    return signed_credential
