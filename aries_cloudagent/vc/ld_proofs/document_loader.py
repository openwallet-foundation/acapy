"""JSON-LD document loader methods"""

from pyld.documentloader import requests
from typing import Callable

from ...core.profile import Profile
from ...did.did_key import DIDKey
from .error import LinkedDataProofException


def get_default_document_loader(profile: Profile) -> "DocumentLoader":
    """Return the default document loader"""

    def default_document_loader(url: str, options: dict):
        """Default document loader implementation"""
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
            raise LinkedDataProofException(
                "Unrecognized url format. Must start with 'did:key:', 'http://' or 'https://'"
            )

    return default_document_loader


DocumentLoader = Callable[[str, dict], dict]

__all__ = [DocumentLoader, get_default_document_loader]
