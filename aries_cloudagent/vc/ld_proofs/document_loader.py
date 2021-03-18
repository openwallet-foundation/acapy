from pyld.documentloader import requests
from ...wallet.util import did_key_to_naked

from typing import Callable


def resolve_ed25519_did_key(did_key: str) -> dict:
    # TODO: optimize
    without_fragment = did_key.split("#")[0]
    pub_key_base58 = did_key_to_naked(without_fragment)
    key_ref = f"#{without_fragment[8:]}"
    did_key_with_key_ref = without_fragment + key_ref

    return {
        "contentType": "application/ld+json",
        "contextUrl": None,
        "documentUrl": did_key,
        "document": {
            "@context": "https://w3id.org/did/v1",
            "id": without_fragment,
            "verificationMethod": [
                {
                    "id": did_key_with_key_ref,
                    "type": "Ed25519VerificationKey2018",
                    "controller": without_fragment,
                    "publicKeyBase58": pub_key_base58,
                }
            ],
            "authentication": [did_key_with_key_ref],
            "assertionMethod": [did_key_with_key_ref],
            "capabilityDelegation": [did_key_with_key_ref],
            "capabilityInvocation": [did_key_with_key_ref],
            "keyAgreement": [
                {
                    "id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6LSbkodSr6SU2trs8VUgnrnWtSm7BAPG245ggrBmSrxbv1R",
                    "type": "X25519KeyAgreementKey2019",
                    "controller": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                    "publicKeyBase58": "5dTvYHaNaB7mk7iA9LqCJEHG2dGZQsvoi8WGzDRtYEf",
                }
            ],
        },
    }


def did_key_document_loader(url: str, options: dict):
    # NOTE: this is a hacky approach for the time being.
    if url.startswith("did:key:"):
        return resolve_ed25519_did_key(url)
    elif url.startswith("http://") or url.startswith("https://"):
        loader = requests.requests_document_loader()
        return loader(url, options)
    else:
        raise Exception(
            "Unrecognized url format. Must start with 'did:key:', 'http://' or 'https://'"
        )


DocumentLoader = Callable[[str, dict], dict]

__all__ = [DocumentLoader, did_key_document_loader]
