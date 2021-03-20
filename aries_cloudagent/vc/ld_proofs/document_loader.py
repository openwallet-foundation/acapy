from pyld.documentloader import requests

from ...did.did_key import DIDKey

from typing import Callable


def did_key_document_loader(url: str, options: dict):
    # TODO: integrate with did resolver interface
    if url.startswith("did:key:"):
        did_key = DIDKey.from_did(url)

        return {
            "contentType": "application/ld+json",
            "contextUrl": None,
            "documentUrl": url,
            "document": did_key.did_doc,
        }
    elif url.startswith("http://") or url.startswith("https://"):
        loader = requests.requests_document_loader()
        return loader(url, options)
    else:
        raise Exception(
            "Unrecognized url format. Must start with 'did:key:', 'http://' or 'https://'"
        )


DocumentLoader = Callable[[str, dict], dict]

__all__ = [DocumentLoader, did_key_document_loader]
