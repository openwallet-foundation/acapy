from ..ld_proofs import (
    LinkedDataProof,
    ProofPurpose,
    sign,
    did_key_document_loader,
    CredentialIssuancePurpose,
    DocumentLoader,
)

# from .checker import check_credential


async def issue(
    *,
    credential: dict,
    suite: LinkedDataProof,
    purpose: ProofPurpose = None,
    document_loader: DocumentLoader = None,
) -> dict:
    # TODO: validate credential format

    if not purpose:
        purpose = CredentialIssuancePurpose()

    signed_credential = await sign(
        document=credential,
        suite=suite,
        purpose=purpose,
        document_loader=document_loader or did_key_document_loader,
    )

    return signed_credential
