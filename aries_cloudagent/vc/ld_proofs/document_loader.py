from pyld.documentloader import requests
from .wallet_util import did_key_to_naked
from ...wallet.util import did_key_to_naked 

def resolve_ed25519_did_key(did_key: str) -> dict:
    pub_key_base58 = did_key_to_naked(did_key)
    key_ref = f"#{did_key[8:]}"
    did_key_with_key_ref = did_key + key_ref

    return {
        "contentType": "application/ld+json",
        "contextUrl": "https://w3id.org/did/v1",
        "documentUrl": did_key,
        "document": {
            "@context": "https://w3id.org/did/v1",
            "id": did_key,
            "verificationMethod": [
                {
                    "id": did_key_with_key_ref,
                    "type": "Ed25519VerificationKey2018",
                    "controller": did_key,
                    "publicKeyBase58": pub_key_base58,
                }
            ],
            "authentication": [did_key_with_key_ref],
            "assertionMethod": [did_key_with_key_ref],
            "capabilityDelegation": [did_key_with_key_ref],
            "capabilityInvocation": [did_key_with_key_ref],
            "keyAgreement": [],
        },
    }


def document_loader(url: str, options: dict):
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
