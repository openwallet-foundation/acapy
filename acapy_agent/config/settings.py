"""Settings implementation."""

from typing import Any, Mapping, MutableMapping, Optional

from .base import BaseSettings
from .plugin_settings import PluginSettings


class Settings(BaseSettings, MutableMapping[str, Any]):
    """Mutable settings implementation."""

    def __init__(self, values: Optional[Mapping[str, Any]] = None):
        """Initialize a Settings object.

        Args:
            values: An optional dictionary of settings
        """
        self._values = {}
        if values:
            self._values.update(values)

    def get_value(self, *var_names, default=None):
        """Fetch a setting.

        Args:
            var_names: A list of variable name alternatives
            default: The default value to return if none are defined
        """
        for k in var_names:
            if k in self._values:
                return self._values[k]
        return default

    def set_value(self, var_name: str, value):
        """Add a setting.

        Args:
            var_name: The name of the setting
            value: The value to assign
        """
        if not isinstance(var_name, str):
            raise TypeError("Setting name must be a string")
        if not var_name:
            raise ValueError("Setting name must be non-empty")
        self._values[var_name] = value

    def set_default(self, var_name: str, value):
        """Add a setting if not currently defined.

        Args:
            var_name: The name of the setting
            value: The value to assign
        """
        if var_name not in self:
            self.set_value(var_name, value)

    def clear_value(self, var_name: str):
        """Remove a setting.

        Args:
            var_name: The name of the setting
        """
        if var_name in self._values:
            del self._values[var_name]

    def __contains__(self, index):
        """Define 'in' operator."""
        return index in self._values

    def __iter__(self):
        """Iterate settings keys."""
        return iter(self._values)

    def __setitem__(self, index, value):
        """Implement update operator for array index."""
        self.set_value(index, value)

    def __delitem__(self, index):
        """Implement del operator for array index."""
        self.clear_value(index)

    def __len__(self):
        """Fetch the length of the mapping."""
        return len(self._values)

    def __bool__(self):
        """Convert settings to a boolean."""
        return True

    def copy(self) -> BaseSettings:
        """Produce a copy of the settings instance."""
        return Settings(self._values)

    def extend(self, other: Mapping[str, Any]) -> BaseSettings:
        """Merge another settings instance to produce a new instance."""
        vals = self._values.copy()
        vals.update(other)
        return Settings(vals)

    def to_dict(self) -> dict:
        """Return a dict of the settings instance."""
        setting_dict = {}
        for k in self:
            setting_dict[k] = self[k]
        return setting_dict

    def update(self, other: Mapping[str, Any]):
        """Update the settings in place."""
        self._values.update(other)

    def for_plugin(self, plugin: str, default: Optional[Mapping[str, Any]] = None):
        """Retrieve settings for plugin."""
        return PluginSettings.for_plugin(self, plugin, default)
