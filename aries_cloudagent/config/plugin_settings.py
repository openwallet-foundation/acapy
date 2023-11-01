"""Settings implementation for plugins."""

from typing import Any, Mapping, Optional

from .base import BaseSettings


PLUGIN_CONFIG_KEY = "plugin_config"


class PluginSettings(BaseSettings):
    """Retrieve immutable settings for plugins.

    Plugin settings should be retrieved by calling:

        PluginSettings.for_plugin(settings, "my_plugin", {"default": "values"})

    This will extract the PLUGIN_CONFIG_KEY in "settings" and return a new
    PluginSettings instance.
    """

    def __init__(self, values: Optional[Mapping[str, Any]] = None):
        """Initialize a Settings object.

        Args:
            values: An optional dictionary of settings
        """
        self._values = {}
        if values:
            self._values.update(values)

    def __contains__(self, index):
        """Define 'in' operator."""
        return index in self._values

    def __iter__(self):
        """Iterate settings keys."""
        return iter(self._values)

    def __len__(self):
        """Fetch the length of the mapping."""
        return len(self._values)

    def __bool__(self):
        """Convert settings to a boolean."""
        return True

    def copy(self) -> BaseSettings:
        """Produce a copy of the settings instance."""
        return PluginSettings(self._values)

    def extend(self, other: Mapping[str, Any]) -> BaseSettings:
        """Merge another settings instance to produce a new instance."""
        vals = self._values.copy()
        vals.update(other)
        return PluginSettings(vals)

    def to_dict(self) -> dict:
        """Return a dict of the settings instance."""
        setting_dict = {}
        for k in self:
            setting_dict[k] = self[k]
        return setting_dict

    def get_value(self, *var_names: str, default: Any = None):
        """Fetch a setting.

        Args:
            var_names: A list of variable name alternatives
            default: The default value to return if none are defined
        """
        for k in var_names:
            if k in self._values:
                return self._values[k]
        return default

    @classmethod
    def for_plugin(
        cls,
        settings: BaseSettings,
        plugin: str,
        default: Optional[Mapping[str, Any]] = None,
    ) -> "PluginSettings":
        """Construct a PluginSettings object from another settings object.

        PLUGIN_CONFIG_KEY is read from settings.
        """
        return cls(settings.get(PLUGIN_CONFIG_KEY, {}).get(plugin, default))
