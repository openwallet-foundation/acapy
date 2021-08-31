from asynctest import TestCase as AsyncTestCase

from ..base import InjectionError
from ..injection_context import InjectionContext, InjectionContextError


class TestInjectionContext(AsyncTestCase):
    def setUp(self):
        self.test_key = "TEST"
        self.test_value = "VALUE"
        self.test_scope = "SCOPE"
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
        with self.assertRaises(InjectionContextError):
            self.test_instance.start_scope(None)
        with self.assertRaises(InjectionContextError):
            self.test_instance.start_scope(self.test_instance.ROOT_SCOPE)

        injector = self.test_instance.injector_for_scope(self.test_instance.ROOT_SCOPE)
        assert injector == self.test_instance.injector
        assert self.test_instance.injector_for_scope("no such scope") is None

        context = self.test_instance.start_scope(self.test_scope)
        assert context.scope_name == self.test_scope
        context.scope_name = "Bob"
        assert context.scope_name == "Bob"

        with self.assertRaises(InjectionContextError):
            context.start_scope(self.test_instance.ROOT_SCOPE)
        assert self.test_instance.scope_name == self.test_instance.ROOT_SCOPE

    def test_settings_scope(self):
        """Test scoped settings."""
        upd_settings = {self.test_key: "NEWVAL"}
        context = self.test_instance.start_scope(self.test_scope, upd_settings)
        assert context.settings[self.test_key] == "NEWVAL"
        assert self.test_instance.settings[self.test_key] == self.test_value
        root = context.injector_for_scope(context.ROOT_SCOPE)
        assert root.settings[self.test_key] == self.test_value

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
        context = self.test_instance.start_scope(self.test_scope)
        assert context.inject_or(str) is None
        context.injector.bind_instance(str, self.test_value)
        assert context.inject(str) is self.test_value
        assert self.test_instance.inject_or(str) is None
        root = context.injector_for_scope(context.ROOT_SCOPE)
        assert root.inject_or(str) is None
        assert self.test_instance.inject_or(str) is None
