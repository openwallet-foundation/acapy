import asyncio
import concurrent.futures
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ....resolver.default.key import KeyDIDResolver
from ....resolver.did_resolver import DIDResolver
from ....utils.testing import create_test_profile
from ..document_loader import DEFAULT_DOCUMENT_LOADER_TIMEOUT, DocumentLoader
from ..error import LinkedDataProofException


@pytest.fixture
async def profile():
    profile = await create_test_profile()
    profile.context.injector.bind_instance(DIDResolver, DIDResolver([KeyDIDResolver()]))
    yield profile


class TestDocumentLoader:
    async def test_http_fetch_is_async_and_yields(self, profile):
        """HTTP fetches should be async and yield control to the event loop."""
        loader = DocumentLoader(profile)

        background_ran = False

        async def mock_load_http(url, options):
            await asyncio.sleep(0)
            nonlocal background_ran
            return {
                "contentType": "application/ld+json",
                "contextUrl": None,
                "documentUrl": url,
                "document": {"background_ran": background_ran},
            }

        async def background():
            nonlocal background_ran
            background_ran = True

        loader._load_http_document = mock_load_http

        task = asyncio.create_task(background())
        result = await loader.load_document("https://example.com/context", {})
        await task

        assert result["documentUrl"] == "https://example.com/context"
        assert result["document"]["background_ran"] is True

    async def test_load_http_document_awaits_downloader(self, profile):
        """_load_http_document should await the async downloader."""
        loader = DocumentLoader(profile)

        with patch.object(
            loader,
            "requests_loader",
            new=AsyncMock(
                return_value={
                    "contentType": "application/ld+json",
                    "contextUrl": None,
                    "documentUrl": "https://example.com/context",
                    "document": {},
                }
            ),
        ) as mock_loader:
            result = await loader._load_http_document("https://example.com/context", {})

        mock_loader.assert_awaited_once_with("https://example.com/context", {})
        assert result["documentUrl"] == "https://example.com/context"

    async def test_did_fetch_is_async(self, profile):
        """DID documents should still be resolved asynchronously."""
        loader = DocumentLoader(profile)

        with patch.object(
            loader.resolver,
            "resolve",
            new=AsyncMock(return_value={"id": "did:key:z6MkqRY"}),
        ) as mock_resolve:
            result = await loader.load_document("did:key:z6MkqRY", {})

        mock_resolve.assert_awaited_once()
        assert result["documentUrl"] == "did:key:z6MkqRY"

    async def test_timeout_setting_is_read_from_profile(self, profile):
        profile.settings["document_loader.timeout"] = 5
        loader = DocumentLoader(profile)
        assert loader._timeout == 5

    async def test_default_timeout_is_used_when_not_configured(self, profile):
        loader = DocumentLoader(profile)
        assert loader._timeout == DEFAULT_DOCUMENT_LOADER_TIMEOUT

    async def test_call_passes_timeout_to_run_coroutine_threadsafe_result(
        self, profile
    ):
        profile.settings["document_loader.timeout"] = 0.01
        loader = DocumentLoader(profile)
        loader._event_loop = MagicMock()
        loader._event_loop.is_running.return_value = True
        loader.load_document = MagicMock(return_value=MagicMock())

        mock_future = MagicMock()
        mock_future.result.side_effect = concurrent.futures.TimeoutError

        with patch(
            "acapy_agent.vc.ld_proofs.document_loader.asyncio.run_coroutine_threadsafe",
            return_value=mock_future,
        ):
            with pytest.raises(LinkedDataProofException):
                loader("did:key:z6MkqRY", {})

        mock_future.result.assert_called_once_with(timeout=0.01)


