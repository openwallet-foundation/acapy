from tempfile import NamedTemporaryFile

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ...storage.provider import StorageProvider
from ...utils.stats import Collector
from ...wallet.base import BaseWallet
from ...wallet.basic import BasicWallet

from ..injection_context import InjectionContext
from ..provider import StatsProvider
from ..settings import Settings


class TestProvider(AsyncTestCase):
    async def test_stats_provider_init_x(self):
        """Cover stats provider init error on no provider."""
        with self.assertRaises(ValueError):
            StatsProvider(None, ["method"])

    async def test_stats_provider_provide_collector(self):
        """Cover call to provide with collector."""

        timing_log = NamedTemporaryFile().name
        settings = {"timing.enabled": True, "timing.log.file": timing_log}
        stats_provider = StatsProvider(
            StorageProvider(), ("add_record", "get_record", "search_records")
        )
        collector = Collector(log_path=timing_log)

        wallet = BasicWallet()
        context = InjectionContext(settings=settings, enforce_typing=False)
        context.injector.bind_instance(Collector, collector)
        context.injector.bind_instance(BaseWallet, wallet)

        await stats_provider.provide(Settings(settings), context.injector)
