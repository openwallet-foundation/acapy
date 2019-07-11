"""Decorator set for Aries#0036 v1.0 issue-credential protocol messages."""

from collections import OrderedDict
from typing import Mapping

from ....decorators.default import DecoratorSet


class V10IssueCredentialDecoratorSet(DecoratorSet):
    """Decorator set for Aries#0036 v1.0 issue-credential protocol messages."""

    def load_decorator(self, key: str, value, serialized=False):
        """Convert a decorator value to its loaded representation."""
        if key in self._models:
            if isinstance(value, (dict, OrderedDict)):
                if serialized:
                    value = self._models[key].deserialize(value)
                else:
                    value = self._models[key](**value)
        if value is not None:
            OrderedDict.__setitem__(self, key, value)
        elif key in self:
            del self[key]

    def extract_decorators(self, message: Mapping, serialized=True) -> OrderedDict:
        """Extract decorators of interest and return the remaining properties."""
        remain = OrderedDict()
        if message:
            pfx_len = len(self._prefix)
            for key, value in message.items():
                key_split = key.split(self._prefix, 1)
                if len(key_split) == 2 and key_split[1] in self._models:
                    if key.startswith(self._prefix):
                        key = key[pfx_len:]
                        self.load_decorator(key, value, serialized)
                    elif self._prefix in key:
                        field, key = key.split(self._prefix, 1)
                        self.field(field).load_decorator(key, value, serialized)
                    else:
                        remain[key] = value
                else:
                    remain[key] = value
        return remain
