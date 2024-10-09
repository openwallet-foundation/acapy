from unittest import IsolatedAsyncioTestCase

from ..base import InjectionError
from ..injection_context import InjectionContext


class TestInjectionContext(IsolatedAsyncioTestCase):
    def setUp(self):
        self.test_key = "TEST"
        self.test_value = "VALUE"
        self.test_scope = "SCOPE"
        self.test_settings = {self.test_key: self.test_value}
        self.test_instance = InjectionContext(settings=self.test_settings)

    def test_settings_init(self):
        """Test settings initialization."""
        for key in self.test_settings:
            assert key in self.test_instance.settings
            assert self.test_instance.settings[key] == self.test_settings[key]

    def test_settings_scope(self):
        """Test scoped settings."""
        upd_settings = {self.test_key: "NEWVAL"}
        context = self.test_instance.start_scope(upd_settings)
        assert context.settings[self.test_key] == "NEWVAL"
        assert self.test_instance.settings[self.test_key] == self.test_value

        context.settings = upd_settings
        assert context.settings == upd_settings

    async def test_inject_simple(self):
        """Test a basic injection."""
        assert self.test_instance.inject_or(str) is None
        with self.assertRaises(InjectionError):
            self.test_instance.inject(str)
        self.test_instance.injector.bind_instance(str, self.test_value)
        assert self.test_instance.inject(str) is self.test_value

        self.test_instance.injector = None
        assert self.test_instance.injector is None

    async def test_inject_scope(self):
        """Test a scoped injection."""
        context = self.test_instance.start_scope()
        assert context.inject_or(str) is None
        context.injector.bind_instance(str, self.test_value)
        assert context.inject(str) is self.test_value
        assert self.test_instance.inject_or(str) is None
