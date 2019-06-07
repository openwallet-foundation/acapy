"""Classes for managing a collection of decorators."""

from collections import OrderedDict
from typing import Mapping, Type

from ...error import BaseError

from ..models.base import BaseModel


DECORATOR_PREFIX = "~"


class DecoratorError(BaseError):
    """Base error for decorator issues."""


class DecoratorSet(OrderedDict):
    """Collection of decorators."""

    def __init__(self, models: dict = None):
        """Initialize a decorator set."""
        self._models: Mapping[str, Type[BaseModel]] = models.copy() if models else {}
        self._prefix = DECORATOR_PREFIX

    @property
    def models(self) -> dict:
        """Accessor for the models dictionary."""
        return self._models.copy()

    @property
    def prefix(self) -> str:
        """Accessor for the decorator prefix."""
        return self._prefix

    def add_model(self, key: str, model: Type[BaseModel]):
        """Add a registered decorator model."""
        self._models[key] = model

    def remove_model(self, key: str):
        """Remove a registered decorator model."""
        del self._models[key]

    def __setitem__(self, key, value):
        """Add a decorator."""
        if not isinstance(value, (str, dict, BaseModel)):
            raise ValueError(f"Unsupported decorator value: {value}")
        super().__setitem__(key, value)

    def load_decorator(self, key: str, value):
        """Convert a decorator value to its loaded representation."""
        if key in self._models and isinstance(value, dict):
            value = self._models[key].deserialize(value)
        if value is not None:
            self[key] = value

    def extract_decorators(self, message: Mapping) -> OrderedDict:
        """Extract decorators and return the remaining properties."""
        remain = OrderedDict()
        if message:
            pfx_len = len(self._prefix)
            for key, value in message.items():
                if key.startswith(self._prefix):
                    key = key[pfx_len:]
                    self.load_decorator(key, value)
                else:
                    remain[key] = value
        return remain

    def to_dict(self) -> dict:
        """Convert to a dictionary (serialize)."""
        result = {}
        for k in self:
            value = self[k]
            if isinstance(value, BaseModel):
                value = value.serialize()
            result[self._prefix + k] = value
        return result

    def __repr__(self) -> str:
        """Create a string representation of the decorator set."""
        items = ("{}: {}".format(k, repr(v)) for k, v in self.to_dict().items())
        return "<{}{{{}}}>".format(self.__class__.__name__, ", ".join(items))
