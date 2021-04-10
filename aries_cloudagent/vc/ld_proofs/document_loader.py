"""JSON-LD document loader methods."""

from pydid.did_url import DIDUrl
from pyld.documentloader import requests
from typing import Callable
import asyncio
import concurrent.futures

from ...resolver.did_resolver import DIDResolver
from ...cache.base import BaseCache
from ...core.profile import Profile
from .error import LinkedDataProofException


def get_default_document_loader(profile: Profile) -> "DocumentLoader":
    """Return the default document loader."""

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    cache = profile.inject(BaseCache, required=False)
    resolver = profile.inject(DIDResolver)
    requests_loader = requests.requests_document_loader()

    # Async document loader can use await for cache and did resolver
    async def async_document_loader(url: str, options: dict):
        """Retrieve http(s) or did:key document."""

        cache_key = f"json_ld_document_resolver::{url}"

        # Try to get from cache
        if cache:
            document = await cache.get(cache_key)
            if document:
                return document

        # Resolve DIDs using did resolver
        if url.startswith("did:"):
            # Resolver expects plain did without path, query, etc...
            # DIDUrl throws error if it contains no path, query etc...
            # This makes sure we get a plain did
            did = DIDUrl.parse(url).did if DIDUrl.is_valid(url) else url

            did_document = await resolver.resolve(profile, did)

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
                await cache.set(cache_key, document)
        else:
            raise LinkedDataProofException(
                "Unrecognized url format. Must start with "
                "'did:', 'http://' or 'https://'"
            )

        return document

    # Thread document loader makes async document loader sync
    def thread_document_loader(url: str, options: dict):
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(async_document_loader(url, options))

    # Loader must be run in separate thread because we can't nest asyncio
    # loop calls.
    def loader(url: str, options: dict):
        future = executor.submit(thread_document_loader, url, options)
        return future.result()

    return loader


DocumentLoader = Callable[[str, dict], dict]

__all__ = [DocumentLoader, get_default_document_loader]
