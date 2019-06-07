"""Classes for managing a collection of decorators."""

from collections import OrderedDict
from typing import Mapping

from ...error import BaseError

from ..models.base import BaseModel


DECORATOR_PREFIX = "~"


class DecoratorError(BaseError):
    """Base error for decorator issues."""


class DecoratorSet(OrderedDict):
    """Collection of decorators."""

    def __init__(self):
        """Initialize a decorator set."""
        self._prefix = DECORATOR_PREFIX

    def __setitem__(self, key, value):
        """Add a decorator."""

        if not isinstance(value, (str, dict, BaseModel)):
            raise ValueError(f"Unsupported decorator value: {value}")
        super().__setitem__(key, value)

    def extract_decorators(self, message: Mapping) -> OrderedDict:
        """Extract decorators and return the remaining properties."""
        remain = OrderedDict()
        if message:
            pfx_len = len(self._prefix)
            for key, value in message.items():
                if key.startswith(self._prefix):
                    self[key[pfx_len:]] = value
                else:
                    remain[key] = value
        return remain

    def to_dict(self) -> dict:
        """Convert to a dictionary (serialize)."""
        result = {}
        for k in self:
            result[self._prefix + k] = self[k]
        return result

    def __repr__(self) -> str:
        """Create a string representation of the decorator set."""
        items = ("{}={}".format(k, repr(v)) for k, v in self.to_dict())
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))
