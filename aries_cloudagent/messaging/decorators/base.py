"""Classes for managing a collection of decorators."""

from collections import OrderedDict
from typing import List, Mapping, Type, Union

from ...error import BaseError

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

    def add_model(self, key: str, model: Union[Type[List[BaseModel]], Type[BaseModel]]):
        """Add a registered decorator model."""
        self._models[key] = model

    def remove_model(self, key: str):
        """Remove a registered decorator model."""
        del self._models[key]

    def __setitem__(self, key, value):
        """Add a decorator."""
        if not isinstance(
            value,
            (bool, int, str, float, list, dict, OrderedDict, BaseModel)
        ):
            raise ValueError(
                f"{key} decorator unsupported type {type(value).__name__}, "
                + f"value: {value}"
            )
        self.load_decorator(key, value)

    def load_decorator(self, key: str, value, serialized=False):
        """Convert a decorator value to its loaded representation."""
        # print(f'\n\n.. 1 ..base-deco load({key}, {value}, {serialized})')
        # print(f'\n\n.. 2 ..base-deco load({key}, {value}, {serialized})')
        # print(f'.. 3 ..models: {self._models}')
        if key in self._models:
            """
            if isinstance(value, list):  # TODO: revisit with deeper understanding
                '''
                if not isinstance(self._models[key], list):
                    raise DecoratorError(
                        f"{key} decorator value {value} is a scalar but model is a list"
                    )
                '''
                if serialized:
                    value = [self._models[key].deserialize(cell) for cell in value]
            """
            if isinstance(value, (dict, OrderedDict)):
                '''
                if isinstance(self._models[key], list):
                    raise DecoratorError(
                        f"{key} decorator value {value} is a list but model is scalar"
                    )
                '''
                if serialized:
                    value = self._models[key].deserialize(value)
                else:
                    value = self._models[key](**value)
        if value is not None:
            super().__setitem__(key, value)
        elif key in self:
            del self[key]
        # print(f'.. 4 .. base-deco load() set {key} deco to {value}')

    def extract_decorators(self, message: Mapping, serialized=True) -> OrderedDict:
        """Extract decorators and return the remaining properties."""
        remain = OrderedDict()
        if message:
            pfx_len = len(self._prefix)
            for key, value in message.items():
                """
                key_split = key.split(self._prefix, 1)
                if len(key_split) == 2 and key_split[1] in self._models:
                    if key.startswith(self._prefix):
                        key = key[pfx_len:]
                        self.load_decorator(key, value, serialized)
                    elif self._prefix in key:
                        field, key = key.split(self._prefix, 1)
                        self.field(field).load_decorator(key, value, serialized)
                        # THIS IS A WORKAROUND FOR ARIES#0036 (v1.0 issue-credential)
                        '''
                        if key == "attach":
                            remain[f'{field}{self._prefix}{key}'] = value
                        '''
                        # IT IS BAD AND NEEDS IMPROVEMENT - SOMEWHERE ELSE IN THE CODE?
                    else:
                        remain[key] = value
                else:
                    remain[key] = value
                """
                if key.startswith(self._prefix):
                    key = key[pfx_len:]
                    self.load_decorator(key, value, serialized)
                elif self._prefix in key:
                    field, key = key.split(self._prefix, 1)
                    self.field(field).load_decorator(key, value, serialized)
                else:
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
