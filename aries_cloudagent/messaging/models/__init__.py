"""Common code for messaging models."""

'''
from collections import namedtuple
from typing import Mapping, Union

from .base import BaseModel

SerDe = namedtuple("SerDe", "ser de")


def to_serde(obj: Union[BaseModel, Mapping]) -> SerDe:
    """Serialize input object if need be."""
    print(f'\n\n>> to-serde: {obj}')
    return (
        SerDe(obj.serialize(), obj)
        if isinstance(obj, BaseModel)
        else None
        if obj is None
        else SerDe(obj, obj.__class__.deserialize(obj))
    )
'''
