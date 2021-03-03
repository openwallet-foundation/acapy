from ..ld_proofs import AuthenticationProofPurpose, ProofPurpose, DocumentLoader, sign
from .constants import CREDENTIALS_CONTEXT_V1_URL


async def create_presentation(
    verifiable_credential: Union[dict, List[dict]], id_: str = None
) -> dict:
    presentation = {
        "@context": [CREDENTIALS_CONTEXT_V1_URL],
        "type": ["VerifiablePresentation"],
    }

    if isinstance(verifiable_credential, dict):
        verifiable_credential = [verifiable_credential]

    # TODO loop through all credentials and validate credential structure

    presentation["verifiableCredential"] = verifiable_credential

    if id_:
        presentation["id"] = id_

    # TODO validate presentation structure

    return presentation


async def sign_presentation(
    presentation: dict,
    suite: LinkedProofSignature,
    document_loader: DocumentLoader,
    domain: str,
    challenge: str,
    purpose: ProofPurpose = None,
):

    if not purpose:
        if not domain and challenge:
            raise Exception(
                '"domain" and "challenge" must be provided when not providing a "purpose"'
            )
        purpose = AuthenticationProofPurpose(challenge=challenge, domain=domain)

    return await sign(
        document=presentaton,
        suite=suite,
        purpose=purpose,
        document_loader=document_loader,
    )
