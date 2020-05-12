"""Handle registration of plugin modules for extending functionality."""

import logging
from collections import OrderedDict
from types import ModuleType
from typing import Sequence

from .error import ProtocolDefinitionValidationError

from ..config.injection_context import InjectionContext
from ..utils.classloader import ClassLoader, ModuleLoadError

from .protocol_registry import ProtocolRegistry

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

    def validate_version(self, version_list, module_name):
        """Validate version dict format."""

        is_list = type(version_list) is list

        # Must be a list
        if not is_list:
            raise ProtocolDefinitionValidationError(
                "Versions definition is not of type list"
            )

        # Must have at least one definition
        if len(version_list) < 1:
            raise ProtocolDefinitionValidationError(
                "Versions list must define at least one version module"
            )

        for version_dict in version_list:
            # Dicts must have correct format
            is_dict = type(version_dict) is dict
            if not is_dict:
                raise ProtocolDefinitionValidationError(
                    "Element of versions definition list is not of type dict"
                )

            try:
                type(version_dict["major_version"]) is int and type(
                    version_dict["minimum_minor_version"]
                ) is int and type(
                    version_dict["current_minor_version"]
                ) is int and type(
                    version_dict["path"]
                ) is str
            except KeyError as e:
                raise ProtocolDefinitionValidationError(
                    f"Element of versions definition list is missing an attribute: {e}"
                )

            # Version number cannot be negative
            if (
                version_dict["major_version"] < 0
                or version_dict["minimum_minor_version"] < 0
                or version_dict["current_minor_version"] < 0
            ):
                raise ProtocolDefinitionValidationError(
                    "Version number cannot be negative"
                )

            # Minimum minor version cannot be great than current version
            if (
                version_dict["minimum_minor_version"]
                > version_dict["current_minor_version"]
            ):
                raise ProtocolDefinitionValidationError(
                    "Minimum supported minor version cannot"
                    + " be greater than current minor version"
                )

            # There can only be one definition per major version
            major_version = version_dict["major_version"]
            count = 0
            for version_dict_outer in version_list:
                if version_dict_outer["major_version"] == major_version:
                    count += 1
            if count > 1:
                raise ProtocolDefinitionValidationError(
                    "There can only be one definition per major version. "
                    + f"Found {count} for major version {major_version}."
                )

            # Specified module must be loadable
            version_path = version_dict["path"]
            mod = ClassLoader.load_module(version_path, module_name)

            if not mod:
                raise ProtocolDefinitionValidationError(
                    "Version module path is not "
                    + f"loadable: {module_name}, {version_path}"
                )

        return True

    def register_plugin(self, module_name: str) -> ModuleType:
        """Register a plugin module."""
        if module_name in self._plugins:
            mod = self._plugins[module_name]
        else:
            try:
                mod = ClassLoader.load_module(module_name)
                LOGGER.debug(f"Loaded module: {module_name}")
            except ModuleLoadError as e:
                LOGGER.error(f"Error loading plugin module: {e}")
                return None

            # Module must exist
            if not mod:
                LOGGER.error(f"Module doesn't exist: {module_name}")
                return None

            # Make an exception for non-protocol modules
            # that contain admin routes and for old-style protocol
            # modules with out version support
            routes = ClassLoader.load_module("routes", module_name)
            message_types = ClassLoader.load_module("message_types", module_name)
            if routes or message_types:
                self._plugins[module_name] = mod
                return mod

            definition = ClassLoader.load_module("definition", module_name)

            # definition.py must exist in protocol
            if not definition:
                LOGGER.error(f"Protocol does not include definition.py: {module_name}")
                return None

            # definition.py must include versions attribute
            if not hasattr(definition, "versions"):
                LOGGER.error(
                    "Protocol definition does not "
                    + f"include versions attribute: {module_name}"
                )
                return None

            # Definition list must not be malformed
            try:
                self.validate_version(definition.versions, module_name)
            except ProtocolDefinitionValidationError as e:
                LOGGER.error(f"Protocol versions definition is malformed. {e}")
                return None

        self._plugins[module_name] = mod
        return mod

        # # Load each version as a separate plugin
        # for version in definition.versions:
        #     mod = ClassLoader.load_module(f"{module_name}.{version['path']}")
        #     self._plugins[module_name] = mod
        #     return mod

    def register_package(self, package_name: str) -> Sequence[ModuleType]:
        """Register all modules (sub-packages) under a given package name."""
        try:
            module_names = ClassLoader.scan_subpackages(package_name)
        except ModuleLoadError:
            LOGGER.error("Plugin module package not found: %s", package_name)
            module_names = []
        return list(
            filter(
                None,
                (self.register_plugin(module_name) for module_name in module_names),
            )
        )

    async def init_context(self, context: InjectionContext):
        """Call plugin setup methods on the current context."""
        for plugin in self._plugins.values():
            if hasattr(plugin, "setup"):
                await plugin.setup(context)
            else:
                await self.load_protocols(context, plugin)

    async def load_protocol_version(
        self,
        context: InjectionContext,
        mod: ModuleType,
        version_definition: dict = None,
    ):
        """Load a particular protocol version."""
        registry = await context.inject(ProtocolRegistry)

        if hasattr(mod, "MESSAGE_TYPES"):
            registry.register_message_types(
                mod.MESSAGE_TYPES, version_definition=version_definition
            )
        if hasattr(mod, "CONTROLLERS"):
            registry.register_controllers(
                mod.CONTROLLERS, version_definition=version_definition
            )

    async def load_protocols(self, context: InjectionContext, plugin: ModuleType):
        """For modules that don't implement setup, register protocols manually."""

        # If this module contains message_types, then assume that
        # this is a valid module of the old style (not versioned)
        try:
            mod = ClassLoader.load_module(plugin.__name__ + ".message_types")
        except ModuleLoadError as e:
            LOGGER.error("Error loading plugin module message types: %s", e)
            return

        if mod:
            await self.load_protocol_version(context, mod)
        else:
            # Otherwise, try check for definition.py for versioned
            # protocol packages
            try:
                definition = ClassLoader.load_module(plugin.__name__ + ".definition")
            except ModuleLoadError as e:
                LOGGER.error("Error loading plugin definition module: %s", e)
                return

            if definition:
                for protocol_version in definition.versions:
                    try:
                        mod = ClassLoader.load_module(
                            f"{plugin.__name__}.{protocol_version['path']}"
                            + ".message_types"
                        )
                        await self.load_protocol_version(context, mod, protocol_version)

                    except ModuleLoadError as e:
                        LOGGER.error("Error loading plugin module message types: %s", e)
                        return

    async def register_admin_routes(self, app):
        """Call route registration methods on the current context."""
        for plugin in self._plugins.values():
            definition = ClassLoader.load_module("definition", plugin.__name__)
            if definition:
                # Load plugin routes that are in a versioned package.
                for plugin_version in definition.versions:
                    try:
                        mod = ClassLoader.load_module(
                            f"{plugin.__name__}.{plugin_version['path']}.routes"
                        )
                    except ModuleLoadError as e:
                        LOGGER.error("Error loading admin routes: %s", e)
                        continue
                    if mod and hasattr(mod, "register"):
                        await mod.register(app)
            else:
                # Load plugin routes that aren't in a versioned package.
                try:
                    mod = ClassLoader.load_module(f"{plugin.__name__}.routes")
                except ModuleLoadError as e:
                    LOGGER.error("Error loading admin routes: %s", e)
                    continue
                if mod and hasattr(mod, "register"):
                    await mod.register(app)

    def set_openapi_file_responses(self, app):
        """Call route binary file response OpenAPI fixups if applicable."""
        for plugin in self._plugins.values():
            definition = ClassLoader.load_module("definition", plugin.__name__)
            if definition:
                # Set binary file responses for routes that are in a versioned package.
                for plugin_version in definition.versions:
                    try:
                        mod = ClassLoader.load_module(
                            f"{plugin.__name__}.{plugin_version['path']}.routes"
                        )
                    except ModuleLoadError as e:
                        LOGGER.error("Error loading admin routes: %s", e)
                        continue
                    if mod and hasattr(mod, "set_openapi_file_responses"):
                        mod.set_openapi_file_responses(app)
            else:
                # Set binary file responses for routes not in a versioned package.
                try:
                    mod = ClassLoader.load_module(f"{plugin.__name__}.routes")
                except ModuleLoadError as e:
                    LOGGER.error("Error loading admin routes: %s", e)
                    continue
                if mod and hasattr(mod, "set_openapi_file_responses"):
                    mod.set_openapi_file_responses(app)

    def __repr__(self) -> str:
        """Return a string representation for this class."""
        return "<{}>".format(self.__class__.__name__)
