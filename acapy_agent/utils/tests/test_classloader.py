from unittest import TestCase, mock

from ...core.error import BaseError
from .. import classloader as test_module
from ..classloader import ClassLoader, ClassNotFoundError, ModuleLoadError


class TestClassLoader(TestCase):
    def test_import_loaded(self):
        assert ClassLoader.load_module("unittest")

    def test_import_local(self):
        with mock.patch.object(test_module.sys, "modules", {}):
            assert (
                ClassLoader.load_module("acapy_agent.transport").__name__
                == "acapy_agent.transport"
            )

    def test_import_relative(self):
        with mock.patch.object(test_module.sys, "modules", {}):
            assert (
                ClassLoader.load_module("transport", "acapy_agent").__name__
                == "acapy_agent.transport"
            )
        with mock.patch.object(test_module.sys, "modules", {}):
            assert (
                ClassLoader.load_module(".transport", "acapy_agent").__name__
                == "acapy_agent.transport"
            )
        with mock.patch.object(test_module.sys, "modules", {}):
            assert (
                ClassLoader.load_module("..transport", "acapy_agent.config").__name__
                == "acapy_agent.transport"
            )

    def test_import_missing(self):
        with mock.patch.object(test_module.sys, "modules", {}):
            assert ClassLoader.load_module("acapy_agent.not") is None
        with mock.patch.object(test_module.sys, "modules", {}):
            assert ClassLoader.load_module("acapy_agent.not.a-module") is None
        with mock.patch.object(test_module.sys, "modules", {}):
            assert ClassLoader.load_module("acapy_agent", "not.a-module") is None

    def test_import_error(self):
        with (
            mock.patch.object(
                test_module, "import_module", autospec=True
            ) as import_module,
            mock.patch.object(test_module.sys, "modules", {}),
        ):
            import_module.side_effect = ModuleNotFoundError
            with self.assertRaises(ModuleLoadError):
                ClassLoader.load_module("acapy_agent.config")

    def test_load_class(self):
        assert ClassLoader.load_class("TestCase", "unittest") is TestCase
        assert ClassLoader.load_class("unittest.TestCase") is TestCase

    def test_load_class_missing(self):
        with self.assertRaises(ClassNotFoundError):
            # with no default module
            assert ClassLoader.load_class("NotAClass")
        with self.assertRaises(ClassNotFoundError):
            assert ClassLoader.load_class("acapy_agent.NotAClass")
        with self.assertRaises(ClassNotFoundError):
            assert ClassLoader.load_class("not-a-module.NotAClass")
        with self.assertRaises(ClassNotFoundError):
            # should be a string, not a type
            assert ClassLoader.load_class("acapy_agent.version.__version__")

    def test_load_subclass(self):
        assert ClassLoader.load_subclass_of(BaseError, "acapy_agent.config.base")

    def test_load_subclass_missing(self):
        with self.assertRaises(ClassNotFoundError):
            assert ClassLoader.load_subclass_of(TestCase, "acapy_agent.config.base")
        with self.assertRaises(ClassNotFoundError):
            assert ClassLoader.load_subclass_of(TestCase, "acapy_agent.not-a-module")

    def test_scan_packages(self):
        pkgs = ClassLoader.scan_subpackages("acapy_agent")
        assert "acapy_agent.transport" in pkgs
        pkgs = ClassLoader.scan_subpackages("acapy_agent.transport")
        assert "acapy_agent.transport.inbound" in pkgs

    def test_scan_packages_missing(self):
        with self.assertRaises(ModuleLoadError):
            ClassLoader.scan_subpackages("acapy_agent.not-a-module")
