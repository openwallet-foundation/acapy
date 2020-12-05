"""Configuration base classes."""

from abc import ABC, abstractmethod
from typing import Mapping, Optional, Type, TypeVar

from ..core.error import BaseError

InjectType = TypeVar("Inject")


class ConfigError(BaseError):
    """A base exception for all configuration errors."""


class SettingsError(ConfigError):
    """The base exception raised by `BaseSettings` implementations."""


class BaseSettings(Mapping[str, object]):
    """Base settings class."""

    @abstractmethod
    def get_value(self, *var_names, default=None):
        """Fetch a setting.

        Args:
            var_names: A list of variable name alternatives
            default: The default value to return if none are defined

        Returns:
            The setting value, if defined, otherwise the default value

        """

    def get_bool(self, *var_names, default=None) -> bool:
        """Fetch a setting as a boolean value.

        Args:
            var_names: A list of variable name alternatives
            default: The default value to return if none are defined
        """
        value = self.get_value(*var_names, default)
        if value is not None:
            value = bool(value and value not in ("false", "False", "0"))
        return value

    def get_int(self, *var_names, default=None) -> int:
        """Fetch a setting as an integer value.

        Args:
            var_names: A list of variable name alternatives
            default: The default value to return if none are defined
        """
        value = self.get_value(*var_names, default)
        if value is not None:
            value = int(value)
        return value

    def get_str(self, *var_names, default=None) -> str:
        """Fetch a setting as a string value.

        Args:
            var_names: A list of variable name alternatives
            default: The default value to return if none are defined
        """
        value = self.get_value(*var_names, default=default)
        if value is not None:
            value = str(value)
        return value

    @abstractmethod
    def __iter__(self):
        """Iterate settings keys."""

    def __getitem__(self, index):
        """Fetch as an array index."""
        if not isinstance(index, str):
            raise TypeError(f"Index {index} must be a string")
        missing = object()
        result = self.get_value(index, default=missing)
        if result is missing:
            raise KeyError("Undefined index: {}".format(index))
        return result

    @abstractmethod
    def __len__(self):
        """Fetch the length of the mapping."""

    @abstractmethod
    def copy(self) -> "BaseSettings":
        """Produce a copy of the settings instance."""

    @abstractmethod
    def extend(self, other: Mapping[str, object]) -> "BaseSettings":
        """Merge another mapping to produce a new settings instance."""

    def __repr__(self) -> str:
        """Provide a human readable representation of this object."""
        items = ("{}={}".format(k, self[k]) for k in self)
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))


class InjectorError(ConfigError):
    """The base exception raised by `BaseInjector` implementations."""


class BaseInjector(ABC):
    """Base injector class."""

    @abstractmethod
    def inject(
        self,
        base_cls: Type[InjectType],
        settings: Mapping[str, object] = None,
        *,
        required: bool = True,
    ) -> Optional[InjectType]:
        """
        Get the provided instance of a given class identifier.

        Args:
            cls: The base class to retrieve an instance of
            settings: An optional mapping providing configuration to the provider

        Returns:
            An instance of the base class, or None

        """

    @abstractmethod
    def copy(self) -> "BaseInjector":
        """Produce a copy of the injector instance."""


class ProviderError(ConfigError):
    """The base exception raised by `BaseProvider` implementations."""


class BaseProvider(ABC):
    """Base provider class."""

    def provide(self, settings: BaseSettings, injector: BaseInjector):
        """Provide the object instance given a config and injector."""
