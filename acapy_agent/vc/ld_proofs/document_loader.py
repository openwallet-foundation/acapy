"""JSON-LD document loader methods."""

import asyncio
from typing import Callable

from pydid.did_url import DIDUrl

from ...cache.base import BaseCache
from ...core.profile import Profile
from ...resolver.did_resolver import DIDResolver
from .document_downloader import StaticCacheJsonLdDownloader
from .error import LinkedDataProofException


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
        self.requests_loader = StaticCacheJsonLdDownloader().load
        self.cache_ttl = cache_ttl
        self._event_loop = asyncio.get_event_loop()

    def _cache_key(self, url: str) -> str:
        return f"json_ld_document_resolver::{url}"

    async def _get_cached_document(self, url: str):
        if self.cache:
            return await self.cache.get(self._cache_key(url))
        return None

    async def _set_cached_document(self, url: str, document: dict):
        if self.cache:
            await self.cache.set(self._cache_key(url), document, self.cache_ttl)

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

    async def _load_http_document(self, url: str, options: dict):
        document = await self.requests_loader(url, options)

        return document

    # Async document loader can use await for cache and did resolver
    async def _load_async(self, url: str, options: dict):
        """Retrieve http(s) or did document."""
        # Resolve DIDs using did resolver
        if url.startswith("did:"):
            document = await self._load_did_document(url, options)
        elif url.startswith("http://") or url.startswith("https://"):
            document = await self._load_http_document(url, options)
        else:
            raise LinkedDataProofException(
                "Unrecognized url format. Must start with 'did:', 'http://' or 'https://'"
            )

        return document

    async def load_document(self, url: str, options: dict):
        """Load JSON-LD document.

        Method signature conforms to PyLD document loader interface

        Document loading is processed in separate thread to deal with
        async to sync transformation.
        """
        document = await self._get_cached_document(url)
        if document:
            return document

        document = await self._load_async(url, options)

        await self._set_cached_document(url, document)

        return document

    def __call__(self, url: str, options: dict):
        """Load JSON-LD Document.

        This loader is invoked synchronously by PyLD.  Because it needs async
        ACA-Py services (DID resolution, cache, and now aiohttp document
        fetching), it schedules ``load_document`` on the event loop that was
        active when the loader was created.  Callers must run PyLD through
        ``acapy_agent.vc.ld_proofs.pyld_util.run_sync`` so that this callback
        is executing on a worker thread and can safely wait for the main loop
        to finish the async work.
        """
        loop = self._event_loop
        coroutine = self.load_document(url, options)

        if not loop.is_running():
            return loop.run_until_complete(coroutine)

        # Safely check if an event loop is running in the current thread.
        # If called from a worker thread, this will raise RuntimeError,
        # which we catch safely instead of crashing.
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        # If we are on the loop's own thread while it is running, blocking would deadlock.
        if current_loop is not None and current_loop == loop:
            raise RuntimeError(
                "DocumentLoader.__call__ was invoked from the event loop thread "
                "while the loop is running. Run the PyLD operation through "
                "acapy_agent.vc.ld_proofs.pyld_util.run_sync instead."
            )

        return asyncio.run_coroutine_threadsafe(coroutine, loop).result()


DocumentLoaderMethod = Callable[[str, dict], dict]

__all__ = ["DocumentLoaderMethod", "DocumentLoader"]
