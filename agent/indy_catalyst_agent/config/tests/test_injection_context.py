from asynctest import TestCase as AsyncTestCase

from ..base import BaseInjector, InjectorError
from ..context import InjectionContext, InjectionContextError


class TestInjectionContext(AsyncTestCase):
    def setUp(self):
        self.test_key = "TEST"
        self.test_value = "VALUE"
        self.test_settings = {self.test_key: self.test_value}
        self.test_instance = InjectionContext(settings=self.test_settings)

    def test_settings_init(self):
        """Test settings initialization."""
        assert self.test_instance.scope_name == self.test_instance.ROOT_SCOPE
        for key in self.test_settings:
            assert key in self.test_instance.settings
            assert self.test_instance.settings[key] == self.test_settings[key]

    def test_simple_scope(self):
        """Test scope entrance and exit."""
        self.test_instance.start_scope("SCOPE")
        with self.assertRaises(InjectionContextError):
            self.test_instance.end_scope("BAD_SCOPE")
        self.test_instance.end_scope("SCOPE")
        assert self.test_instance.scope_name == self.test_instance.ROOT_SCOPE

    def test_settings_scope(self):
        """Test scoped settings."""
        upd_settings = {self.test_key: "NEWVAL"}
        self.test_instance.start_scope("SCOPE", upd_settings)
        assert self.test_instance.settings[self.test_key] == "NEWVAL"
        self.test_instance.end_scope("SCOPE")
        assert self.test_instance.settings[self.test_key] == self.test_value

    async def test_inject_simple(self):
        """Test a basic injection."""
        assert (await self.test_instance.inject(str, required=False)) is None
        with self.assertRaises(InjectorError):
            await self.test_instance.inject(str)
        self.test_instance.injector.bind_instance(str, self.test_value)
        assert (await self.test_instance.inject(str)) is self.test_value

    async def test_inject_scope(self):
        """Test a scoped injection."""
        self.test_instance.start_scope("SCOPE")
        assert (await self.test_instance.inject(str, required=False)) is None
        self.test_instance.injector.bind_instance(str, self.test_value)
        assert (await self.test_instance.inject(str)) is self.test_value
        self.test_instance.end_scope("SCOPE")
        assert (await self.test_instance.inject(str, required=False)) is None
