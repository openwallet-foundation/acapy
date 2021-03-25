from .contexts import (
    DID_V1,
    SECURITY_V1,
    SECURITY_V2,
    CREDENTIALS_V1,
    EXAMPLES_V1,
    BBS_V1,
    CITIZENSHIP_V1,
    ODRL,
)
from ..ld_proofs.constants import (
    SECURITY_CONTEXT_V2_URL,
    SECURITY_CONTEXT_V1_URL,
    DID_V1_CONTEXT_URL,
    SECURITY_CONTEXT_BBS_URL,
    CREDENTIALS_CONTEXT_V1_URL,
)
from .dids import DID_z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL

DOCUMENTS = {
    DID_z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL.get(
        "id"
    ): DID_z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL,
    SECURITY_CONTEXT_V1_URL: SECURITY_V1,
    SECURITY_CONTEXT_V2_URL: SECURITY_V2,
    DID_V1_CONTEXT_URL: DID_V1,
    CREDENTIALS_CONTEXT_V1_URL: CREDENTIALS_V1,
    SECURITY_CONTEXT_BBS_URL: BBS_V1,
    "https://www.w3.org/2018/credentials/examples/v1": EXAMPLES_V1,
    "https://w3id.org/citizenship/v1": CITIZENSHIP_V1,
    "https://www.w3.org/ns/odrl.jsonld": ODRL,
}


def custom_document_loader(url: str, options: dict):
    without_fragment = url.split("#")[0]

    if without_fragment in DOCUMENTS:
        return {
            "contentType": "application/ld+json",
            "contextUrl": None,
            "document": DOCUMENTS[without_fragment],
            "documentUrl": url,
        }

    raise Exception(f"No custom context support for {url}")
