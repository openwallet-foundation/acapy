from tempfile import NamedTemporaryFile

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ...utils.stats import Collector

from ..injection_context import InjectionContext
from ..provider import BaseProvider, StatsProvider
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
        mock_provider = async_mock.MagicMock(BaseProvider, autospec=True)
        stats_provider = StatsProvider(mock_provider, ("mock_method"))
        collector = Collector(log_path=timing_log)

        context = InjectionContext(settings=settings, enforce_typing=False)
        context.injector.bind_instance(Collector, collector)

        await stats_provider.provide(Settings(settings), context.injector)
