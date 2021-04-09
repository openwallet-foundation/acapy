"""JSON-LD document loader methods."""

from pyld.documentloader import requests
from typing import Callable
import asyncio

from ...resolver.did_resolver import DIDResolver
from ...cache.base import BaseCache
from ...core.profile import Profile
from .error import LinkedDataProofException


def get_default_document_loader(profile: Profile) -> "DocumentLoader":
    """Return the default document loader."""

    loop = asyncio.get_event_loop()
    cache = profile.inject(BaseCache, required=False)
    resolver = profile.inject(DIDResolver)
    requests_loader = requests.requests_document_loader()

    async def async_document_loader(url: str, options: dict):
        """Retrieve http(s) or did:key document."""

        cache_key = f"json_ld_document_resolver::{url}"

        # Try to get from cache
        if cache:
            document = cache.get(cache_key)
            if document:
                return document

        # Resolve DIDs using did resolver
        if url.startswith("did:"):
            did_document = await resolver.resolve(profile, url)

            document = {
                "contentType": "application/ld+json",
                "contextUrl": None,
                "documentUrl": url,
                "document": did_document.serialize(),
            }
        elif url.startswith("http://") or url.startswith("https://"):
            document = requests_loader(url, options)
            # Only cache http document at the moment
            if cache:
                cache.set(cache_key, document)
        else:
            raise LinkedDataProofException(
                "Unrecognized url format. Must start with "
                "'did:', 'http://' or 'https://'"
            )

    # PyLD document loaders must be sync.
    def loader(url: str, options: dict):
        return loop.run_until_complete(async_document_loader(url, options))

    return loader


DocumentLoader = Callable[[str, dict], dict]

__all__ = [DocumentLoader, get_default_document_loader]
