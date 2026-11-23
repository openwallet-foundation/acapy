from unittest.mock import AsyncMock, Mock

import pytest

from acapy_agent.vc.ld_proofs.document_downloader import StaticCacheJsonLdDownloader


@pytest.mark.asyncio
async def test_load_cache_hit():
    downloader = Mock()
    context_loader = StaticCacheJsonLdDownloader(document_downloader=downloader)

    await context_loader.load("https://www.w3.org/2018/credentials/v1")
    downloader.download.assert_not_called()


@pytest.mark.asyncio
async def test_load_cache_miss_triggers_download():
    downloader = Mock()
    downloader.download = AsyncMock(return_value=(None, None))
    context_loader = StaticCacheJsonLdDownloader(document_downloader=downloader)

    await context_loader.load("https://www.w3.org/2018/very_unlikely_name/v1")
    downloader.download.assert_awaited()
