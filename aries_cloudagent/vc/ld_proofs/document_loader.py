"""JSON-LD document loader methods."""

from pyld.documentloader import requests
from typing import Callable

from ...cache.base import BaseCache
from ...core.profile import Profile
from ...did.did_key import DIDKey
from .error import LinkedDataProofException


def get_default_document_loader(profile: Profile) -> "DocumentLoader":
    """Return the default document loader."""

    cache = profile.inject(BaseCache, required=False)

    def default_document_loader(url: str, options: dict):
        """Retrieve http(s) or did:key document."""

        cache_key = f"json_ld_document_resolver::{url}"

        # Try to get from cache
        if cache:
            document = cache.get(cache_key)
            if document:
                return document

        # TODO: integrate with did resolver interface
        # https://github.com/hyperledger/aries-cloudagent-python/pull/1033
        if url.startswith("did:key:"):
            did_key = DIDKey.from_did(url)

            document = {
                "contentType": "application/ld+json",
                "contextUrl": None,
                "documentUrl": url,
                "document": did_key.did_doc,
            }
        elif url.startswith("http://") or url.startswith("https://"):
            loader = requests.requests_document_loader()
            document = loader(url, options)

            # Only cache http document at the moment
            if cache:
                cache.set(cache_key, document)
        else:
            raise LinkedDataProofException(
                "Unrecognized url format. Must start with "
                "'did:key:', 'http://' or 'https://'"
            )

    return default_document_loader


DocumentLoader = Callable[[str, dict], dict]

__all__ = [DocumentLoader, get_default_document_loader]
