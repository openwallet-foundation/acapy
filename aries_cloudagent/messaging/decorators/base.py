"""Classes for managing a collection of decorators."""

from collections import OrderedDict
from typing import Mapping, Sequence, Type

from marshmallow import Schema
from marshmallow.fields import Field

from ...core.error import BaseError

from ..models.base import BaseModel

DECORATOR_PREFIX = "~"


class DecoratorError(BaseError):
    """Base error for decorator issues."""


class BaseDecoratorSet(OrderedDict):
    """Collection of decorators."""

    def __init__(self, models: dict = None):
        """Initialize a decorator set."""
        self._fields = OrderedDict()
        self._models: Mapping[str, Type[BaseModel]] = models.copy() if models else {}
        self._prefix = DECORATOR_PREFIX

    def copy(self) -> "BaseDecoratorSet":
        """Return a copy of the decorator set."""
        result = super().copy()
        result._fields = OrderedDict(
            (name, field.copy()) for (name, field) in self._fields.items()
        )
        result._models = self._models.copy()
        result._prefix = self._prefix
        return result

    def __eq__(self, other: "BaseDecoratorSet") -> bool:
        """Comparison between base decorator sets."""
        return (
            self._fields == other._fields
            and self._models == other._models
            and self._prefix == other._prefix
            and super().__eq__(other)
        )

    def _init_field(self) -> "BaseDecoratorSet":
        """Create a nested decorator set for a named field."""
        return self.__class__(self._models)

    def field(self, name: str) -> "BaseDecoratorSet":
        """Access a named decorated field."""
        if name not in self._fields:
            self._fields[name] = self._init_field()
        return self._fields[name]

    def has_field(self, name: str) -> bool:
        """Check for the existence of a named decorator field."""
        return bool(self._fields.get(name))

    def remove_field(self, name: str):
        """Remove a named decorated field."""
        if name in self._fields:
            del self._fields[name]

    @property
    def fields(self) -> OrderedDict:
        """Acessor for the set of currently defined fields."""
        return OrderedDict(
            (name, field) for (name, field) in self._fields.items() if field
        )

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
        self.load_decorator(key, value)

    def load_decorator(self, key: str, value, serialized=False):
        """Convert a decorator value to its loaded representation."""
        if key in self._models and isinstance(value, (dict, OrderedDict)):
            if serialized:
                value = self._models[key].deserialize(value)
            else:
                value = self._models[key](**value)
        if value is not None:
            super().__setitem__(key, value)
        elif key in self:
            del self[key]

    def extract_decorators(
        self,
        message: Mapping,
        schema: Type[Schema] = None,
        serialized: bool = True,
        skip_attrs: Sequence[str] = None,
    ) -> OrderedDict:
        """Extract decorators and return the remaining properties."""
        remain = OrderedDict()
        skip_attrs = set(skip_attrs) if skip_attrs else set()
        if schema:
            for field_name, field_def in schema._declared_fields.items():
                if isinstance(field_def, Field) and field_def.data_key:
                    skip_attrs.add(field_def.data_key)
        if message:
            pfx_len = len(self._prefix)
            for key, value in message.items():
                if key in skip_attrs:
                    pass
                elif key.startswith(self._prefix):
                    key = key[pfx_len:]
                    self.load_decorator(key, value, serialized)
                    continue
                elif self._prefix in key:
                    field, key = key.split(self._prefix, 1)
                    self.field(field).load_decorator(key, value, serialized)
                    continue
                remain[key] = value
        return remain

    def to_dict(self, prefix: str = None) -> OrderedDict:
        """Convert to a dictionary (serialize).

        Raises:
            BaseModelError: on decorator validation errors

        """
        if prefix is None:
            prefix = self._prefix
        result = OrderedDict()
        for k in self:
            value = self[k]
            if isinstance(value, BaseModel):
                value = value.serialize()
            result[prefix + k] = value
        for k in self._fields:
            result.update(self._fields[k].to_dict(k + prefix))
        return result

    def __repr__(self) -> str:
        """Create a string representation of the decorator set."""
        items = ("{}: {}".format(self._prefix + k, repr(self[k])) for k in self)
        return "<{}{{{}}}>".format(self.__class__.__name__, ", ".join(items))
