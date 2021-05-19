"""Record instance stored and searchable by BaseStorage implementation."""

import json

from collections import namedtuple
from uuid import uuid4


class StorageRecord(namedtuple("StorageRecord", "type value tags id")):
    """Storage record class."""

    __slots__ = ()

    def __new__(cls, type, value, tags: dict = None, id: str = None):
        """Initialize some defaults on record."""
        if not id:
            id = uuid4().hex
        if not tags:
            tags = {}
        if value and not isinstance(value, dict):
            
        return super(cls, StorageRecord).__new__(
            cls,
            type,
            (
                None
                if value is None  # formally OK for deletion case
                else value if isinstance(value, dict)
                else value.serialize()
            ),
            tags,
            id,
        )
