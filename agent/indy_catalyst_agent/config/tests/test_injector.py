from asynctest import TestCase as AsyncTestCase

from ..base import BaseProvider, BaseInjector, BaseSettings, InjectorError
from ..injector import Injector
from ..provider import ClassProvider, CachedProvider


class MockProvider(BaseProvider):
    def __init__(self, value):
        self.settings = None
        self.injector = None
        self.value = value

    async def provide(self, settings: BaseSettings, injector: BaseInjector):
        self.settings = settings
        self.injector = injector
        return self.value


class MockInstance:
    def __init__(self, value):
        self.opened = False
        self.value = value

    async def open(self):
        self.opened = True


class TestInjector(AsyncTestCase):
    def setUp(self):
        self.test_key = "TEST"
        self.test_value = "VALUE"
        self.test_settings = {self.test_key: self.test_value}
        self.test_instance = Injector(settings=self.test_settings)

    def test_settings_init(self):
        """Test settings initialization."""
        for key in self.test_settings:
            assert key in self.test_instance.settings
            assert self.test_instance.settings[key] == self.test_settings[key]

    async def test_inject_simple(self):
        """Test a basic injection."""
        assert (await self.test_instance.inject(str, required=False)) is None
        with self.assertRaises(InjectorError):
            await self.test_instance.inject(str)
        with self.assertRaises(ValueError):
            await self.test_instance.bind_instance(str, None)
        self.test_instance.bind_instance(str, self.test_value)
        assert (await self.test_instance.inject(str)) is self.test_value

    async def test_inject_provider(self):
        """Test a provider injection."""
        mock_provider = MockProvider(self.test_value)
        self.test_instance.bind_provider(str, mock_provider)
        assert self.test_instance.get_provider(str) is mock_provider
        override_settings = {self.test_key: "NEWVAL"}
        assert (
            await self.test_instance.inject(str, override_settings)
        ) is self.test_value
        assert mock_provider.settings[self.test_key] == override_settings[self.test_key]
        assert mock_provider.injector is self.test_instance

    async def test_inject_class(self):
        """Test a provider class injection."""
        provider = ClassProvider(MockInstance, self.test_value, async_init="open")
        self.test_instance.bind_provider(str, provider)
        assert self.test_instance.get_provider(str) is provider
        instance = await self.test_instance.inject(str)
        assert isinstance(instance, MockInstance)
        assert instance.value is self.test_value
        assert instance.opened

    async def test_inject_cached(self):
        """Test a provider class injection."""
        with self.assertRaises(ValueError):
            CachedProvider(None)
        provider = ClassProvider(MockInstance, self.test_value, async_init="open")
        cached = CachedProvider(provider)
        self.test_instance.bind_provider(str, cached)
        assert self.test_instance.get_provider(str) is cached
        i1 = await self.test_instance.inject(str)
        i2 = await self.test_instance.inject(str)
        assert i1 is i2

        provider = ClassProvider(MockInstance, self.test_value, async_init="open")
        self.test_instance.bind_provider(str, provider, cache=True)
        i1 = await self.test_instance.inject(str)
        i2 = await self.test_instance.inject(str)
        assert i1 is i2
