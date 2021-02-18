from tempfile import NamedTemporaryFile
from weakref import ref, ReferenceType

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ...utils.stats import Collector

from ..base import InjectionError
from ..injection_context import InjectionContext
from ..provider import (
    BaseProvider,
    ClassProvider,
    InstanceProvider,
    StatsProvider,
    CachedProvider,
)
from ..settings import Settings


class X:
    def __init__(self, *args, **kwargs):
        pass


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
        mock_provider.provide.return_value.mock_method = lambda: ()
        stats_provider = StatsProvider(mock_provider, ("mock_method",))
        collector = Collector(log_path=timing_log)

        context = InjectionContext(settings=settings, enforce_typing=False)
        context.injector.bind_instance(Collector, collector)

        stats_provider.provide(Settings(settings), context.injector)

    async def test_cached_provider_same_unique_settings(self):
        """Cover same unique keys returns same instance."""
        first_settings = Settings(
            {"wallet.name": "wallet.name", "wallet.key": "wallet.key"}
        )
        second_settings = first_settings.extend({"wallet.key": "another.wallet.key"})

        cached_provider = CachedProvider(
            ClassProvider("aries_cloudagent.config.settings.Settings"), ("wallet.name",)
        )
        context = InjectionContext()

        first_instance = cached_provider.provide(first_settings, context.injector)
        second_instance = cached_provider.provide(second_settings, context.injector)

        assert first_instance is second_instance

    async def test_cached_provider_different_unique_settings(self):
        """Cover two different unique keys returns different instance."""
        first_settings = Settings(
            {"wallet.name": "wallet.name", "wallet.key": "wallet.key"}
        )
        second_settings = first_settings.extend({"wallet.name": "another.wallet.name"})

        cached_provider = CachedProvider(
            ClassProvider("aries_cloudagent.config.settings.Settings"), ("wallet.name",)
        )
        context = InjectionContext()

        first_instance = cached_provider.provide(first_settings, context.injector)
        second_instance = cached_provider.provide(second_settings, context.injector)

        assert first_instance is not second_instance

    async def test_instance_provider_ref_gone_x(self):
        context = InjectionContext(settings=Settings({}), enforce_typing=False)
        item = X()
        instance = ref(item)
        del item

        with self.assertRaises(InjectionError):
            provider = InstanceProvider(instance=instance)
            provider.provide(Settings({}), context.injector)

    async def test_class_provider_ref_gone_x(self):
        context = InjectionContext(settings=Settings({}), enforce_typing=False)
        item = X()
        instance = ref(item)
        del item

        with self.assertRaises(InjectionError):
            provider = ClassProvider(X, instance)
            provider.provide(Settings({}), context.injector)

        with self.assertRaises(InjectionError):
            provider = ClassProvider(X, kwarg=instance)
            provider.provide(Settings({}), context.injector)
