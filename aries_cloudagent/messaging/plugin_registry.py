"""Handle registration of plugin modules for extending functionality."""

import logging
from collections import OrderedDict
from types import ModuleType
from typing import Sequence

from ..classloader import ClassLoader, ModuleLoadError
from ..config.injection_context import InjectionContext
from ..messaging.protocol_registry import ProtocolRegistry

LOGGER = logging.getLogger(__name__)


class PluginRegistry:
    """Plugin registry for indexing application plugins."""

    def __init__(self):
        """Initialize a `PluginRegistry` instance."""
        self._plugins = OrderedDict()

    @property
    def plugin_names(self) -> Sequence[str]:
        """Accessor for a list of all plugin modules."""
        return list(self._plugins.keys())

    @property
    def plugins(self) -> Sequence[ModuleType]:
        """Accessor for a list of all plugin modules."""
        return list(self._plugins.values())

    def register_plugin(self, module_name) -> ModuleType:
        """Register a plugin module."""
        if module_name not in self._plugins:
            self._plugins[module_name] = ClassLoader.load_module(module_name)
        return self._plugins[module_name]

    def register_package(self, package_name: str) -> Sequence[ModuleType]:
        """Register all modules (sub-packages) under a given package name."""
        module_names = ClassLoader.scan_subpackages(package_name)
        return [self.register_plugin(module_name) for module_name in module_names]

    async def init_context(self, context: InjectionContext):
        """Call plugin setup methods on the current context."""
        for plugin in self._plugins.values():
            if hasattr(plugin, "setup"):
                await plugin.setup(context)
            else:
                await self.load_message_types(context, plugin)

    async def load_message_types(self, context: InjectionContext, plugin: ModuleType):
        """For modules that don't implement setup, register protocols manually."""
        registry = await context.inject(ProtocolRegistry)
        try:
            mod = ClassLoader.load_module(plugin.__name__ + ".message_types")
        except ModuleLoadError:
            LOGGER.info(
                "No message types defined for plugin module: %s", plugin.__name__
            )
            return
        if hasattr(mod, "MESSAGE_TYPES"):
            registry.register_message_types(mod.MESSAGE_TYPES)
        if hasattr(mod, "CONTROLLERS"):
            registry.register_controllers(mod.CONTROLLERS)

    async def register_admin_routes(self, app):
        """Call route registration methods on the current context."""
        for plugin in self._plugins.values():
            try:
                mod = ClassLoader.load_module(plugin.__name__ + ".routes")
            except ModuleLoadError:
                continue
            if hasattr(mod, "register"):
                await mod.register(app)

    def __repr__(self) -> str:
        """Return a string representation for this class."""
        return "<{}>".format(self.__class__.__name__)
