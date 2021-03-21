from ..ld_proofs import (
    LinkedDataProof,
    ProofPurpose,
    sign,
    default_document_loader,
    CredentialIssuancePurpose,
    DocumentLoader,
)


async def issue(
    *,
    credential: dict,
    suite: LinkedDataProof,
    purpose: ProofPurpose = None,
    document_loader: DocumentLoader = None,
) -> dict:
    # NOTE: API assumes credential is validated on higher level
    # we should probably change that, but also want to avoid revalidation on every level

    if not purpose:
        purpose = CredentialIssuancePurpose()

    signed_credential = await sign(
        document=credential,
        suite=suite,
        purpose=purpose,
        document_loader=document_loader or default_document_loader,
    )

    return signed_credential
