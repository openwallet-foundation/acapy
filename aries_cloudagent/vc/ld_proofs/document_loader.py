"""JSON-LD document loader methods."""

import asyncio
import concurrent.futures

from typing import Callable

from pydid.did_url import DIDUrl
from pyld.documentloader import requests

from ...cache.base import BaseCache
from ...core.profile import Profile
from ...resolver.did_resolver import DIDResolver

from .error import LinkedDataProofException

import nest_asyncio

nest_asyncio.apply()


class DocumentLoader:
    """JSON-LD document loader."""

    def __init__(self, profile: Profile, cache_ttl: int = 300) -> None:
        """Initialize new DocumentLoader instance.

        Args:
            profile (Profile): The profile
            cache_ttl (int, optional): TTL for cached documents. Defaults to 300.

        """
        self.profile = profile
        self.resolver = profile.inject(DIDResolver)
        self.cache = profile.inject_or(BaseCache)
        self.requests_loader = requests.requests_document_loader()
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.cache_ttl = cache_ttl
        self._event_loop = asyncio.get_event_loop()

    async def _load_did_document(self, did: str, options: dict):
        # Resolver expects plain did without path, query, etc...
        # DIDUrl throws error if it contains no path, query etc...
        # This makes sure we get a plain did
        did = DIDUrl.parse(did).did if DIDUrl.is_valid(did) else did

        did_document = await self.resolver.resolve(self.profile, did)

        document = {
            "contentType": "application/ld+json",
            "contextUrl": None,
            "documentUrl": did,
            "document": did_document,
        }

        return document

    def _load_http_document(self, url: str, options: dict):
        document = self.requests_loader(url, options)

        return document

    # Async document loader can use await for cache and did resolver
    async def _load_async(self, url: str, options: dict):
        """Retrieve http(s) or did document."""

        # Resolve DIDs using did resolver
        if url.startswith("did:"):
            document = await self._load_did_document(url, options)
        elif url.startswith("http://") or url.startswith("https://"):
            document = self._load_http_document(url, options)
        else:
            raise LinkedDataProofException(
                "Unrecognized url format. Must start with "
                "'did:', 'http://' or 'https://'"
            )

        return document

    async def load_document(self, url: str, options: dict):
        """Load JSON-LD document.

        Method signature conforms to PyLD document loader interface

        Document loading is processed in separate thread to deal with
        async to sync transformation.
        """
        cache_key = f"json_ld_document_resolver::{url}"

        # Try to get from cache
        if self.cache:
            document = await self.cache.get(cache_key)
            if document:
                return document

        document = await self._load_async(url, options)

        # Cache document, if cache is available
        if self.cache:
            await self.cache.set(cache_key, document, self.cache_ttl)

        return document

    def __call__(self, url: str, options: dict):
        """Load JSON-LD Document."""

        loop = self._event_loop
        coroutine = self.load_document(url, options)
        document = loop.run_until_complete(coroutine)

        return document


DocumentLoaderMethod = Callable[[str, dict], dict]

__all__ = ["DocumentLoaderMethod", "DocumentLoader"]
