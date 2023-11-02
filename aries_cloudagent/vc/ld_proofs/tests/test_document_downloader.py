from unittest.mock import Mock

from aries_cloudagent.vc.ld_proofs.document_downloader import (
    StaticCacheJsonLdDownloader,
)


def test_load_cache_hit():
    downloader = Mock()
    context_loader = StaticCacheJsonLdDownloader(document_downloader=downloader)

    context_loader.load("https://www.w3.org/2018/credentials/v1")
    downloader.download.assert_not_called()


def test_load_cache_miss_triggers_download():
    downloader = Mock()
    downloader.download = Mock(return_value=(None, None))
    context_loader = StaticCacheJsonLdDownloader(document_downloader=downloader)

    context_loader.load("https://www.w3.org/2018/very_unlikely_name/v1")
    downloader.download.assert_called()
