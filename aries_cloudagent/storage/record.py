"""Record instance stored and searchable by BaseStorage implementation."""

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
        return super(cls, StorageRecord).__new__(cls, type, value, tags, id)
