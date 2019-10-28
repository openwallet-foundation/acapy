"""Basic in-memory storage implementation (non-wallet)."""

from collections import OrderedDict
from typing import Mapping, Sequence

from .base import BaseStorage, BaseStorageRecordSearch
from .error import (
    StorageError,
    StorageDuplicateError,
    StorageNotFoundError,
    StorageSearchError,
)
from .record import StorageRecord
from ..wallet.base import BaseWallet


class BasicStorage(BaseStorage):
    """Basic in-memory storage class."""

    def __init__(self, _wallet: BaseWallet = None):
        """
        Initialize a `BasicStorage` instance.

        Args:
            _wallet: The wallet implementation to use

        """
        self._records = OrderedDict()

    async def add_record(self, record: StorageRecord):
        """
        Add a new record to the store.

        Args:
            record: `StorageRecord` to be stored

        Raises:
            StorageError: If no record is provided
            StorageError: If the record has no ID

        """
        if not record:
            raise StorageError("No record provided")
        if not record.id:
            raise StorageError("Record has no ID")
        if record.id in self._records:
            raise StorageDuplicateError("Duplicate record")
        self._records[record.id] = record

    async def get_record(
        self, record_type: str, record_id: str, options: Mapping = None
    ) -> StorageRecord:
        """
        Fetch a record from the store by type and ID.

        Args:
            record_type: The record type
            record_id: The record id
            options: A dictionary of backend-specific options

        Returns:
            A `StorageRecord` instance

        Raises:
            StorageNotFoundError: If the record is not found

        """
        row = self._records.get(record_id)
        if row and row.type == record_type:
            return row
        if not row:
            raise StorageNotFoundError("Record not found: {}".format(record_id))

    async def update_record_value(self, record: StorageRecord, value: str):
        """
        Update an existing stored record's value.

        Args:
            record: `StorageRecord` to update
            value: The new value

        Raises:
            StorageNotFoundError: If record not found

        """
        oldrec = self._records.get(record.id)
        if not oldrec:
            raise StorageNotFoundError("Record not found: {}".format(record.id))
        self._records[record.id] = oldrec._replace(value=value)

    async def update_record_tags(self, record: StorageRecord, tags: Mapping):
        """
        Update an existing stored record's tags.

        Args:
            record: `StorageRecord` to update
            tags: New tags

        Raises:
            StorageNotFoundError: If record not found

        """
        oldrec = self._records.get(record.id)
        if not oldrec:
            raise StorageNotFoundError("Record not found: {}".format(record.id))
        self._records[record.id] = oldrec._replace(tags=dict(tags or {}))

    async def delete_record_tags(
        self, record: StorageRecord, tags: (Sequence, Mapping)
    ):
        """
        Update an existing stored record's tags.

        Args:
            record: `StorageRecord` to delete
            tags: Tags

        Raises:
            StorageNotFoundError: If record not found

        """
        oldrec = self._records.get(record.id)
        if not oldrec:
            raise StorageNotFoundError("Record not found: {}".format(record.id))
        newtags = dict(oldrec.tags or {})
        if tags:
            for tag in tags:
                if tag in newtags:
                    del newtags[tag]
        self._records[record.id] = oldrec._replace(tags=newtags)

    async def delete_record(self, record: StorageRecord):
        """
        Delete a record.

        Args:
            record: `StorageRecord` to delete

        Raises:
            StorageNotFoundError: If record not found

        """
        if record.id not in self._records:
            raise StorageNotFoundError("Record not found: {}".format(record.id))
        del self._records[record.id]

    def search_records(
        self,
        type_filter: str,
        tag_query: Mapping = None,
        page_size: int = None,
        options: Mapping = None,
    ) -> "BasicStorageRecordSearch":
        """
        Search stored records.

        Args:
            type_filter: Filter string
            tag_query: Tags to query
            page_size: Page size
            options: Dictionary of backend-specific options

        Returns:
            An instance of `BaseStorageRecordSearch`

        """
        return BasicStorageRecordSearch(
            self, type_filter, tag_query, page_size, options
        )


def basic_tag_value_match(value: str, match: dict) -> bool:
    """Match a single tag against a tag subquery.

    TODO: What type coercion is needed? (support int or float values?)
    """
    if len(match) != 1:
        raise StorageSearchError("Unsupported subquery: {}".format(match))
    if value is None:
        return False
    op = match.keys()[0]
    cmp_val = match[op]
    if op == "$in":
        if not isinstance(cmp_val, list):
            raise StorageSearchError("Expected list for $in value")
        chk = cmp_val in op
    else:
        if not isinstance(cmp_val, str):
            raise StorageSearchError("Expected string for filter value")
        if op == "$neq":
            chk = value != cmp_val
        elif op == "$gt":
            chk = value > cmp_val
        elif op == "$gte":
            chk = value >= cmp_val
        elif op == "$lt":
            chk = value < cmp_val
        elif op == "$lte":
            chk = value <= cmp_val
        # elif op == "$like":  NYI
        else:
            raise StorageSearchError("Unsupported match operator: ".format(op))
    return chk


def basic_tag_query_match(tags: dict, tag_query: dict) -> bool:
    """Match simple tag filters (string values)."""
    result = True
    if not tags:
        tags = {}
    if tag_query:
        for k, v in tag_query.items():
            if k == "$or":
                if not isinstance(v, list):
                    raise StorageSearchError("Expected list for $or filter value")
                chk = False
                for opt in v:
                    if basic_tag_query_match(tags, opt):
                        chk = True
                        break
            elif k == "$not":
                if not isinstance(v, dict):
                    raise StorageSearchError("Expected dict for $not filter value")
                chk = not basic_tag_query_match(tags, v)
            elif k[0] == "$":
                raise StorageSearchError("Unexpected filter operator: {}".format(k))
            elif isinstance(v, str):
                chk = tags.get(k) == v
            elif isinstance(v, dict):
                chk = basic_tag_value_match(tags.get(k), v)
            else:
                raise StorageSearchError(
                    "Expected string or dict for filter value, got {}".format(v)
                )
            if not chk:
                result = False
                break
    return result


class BasicStorageRecordSearch(BaseStorageRecordSearch):
    """Represent an active stored records search."""

    def __init__(
        self,
        store: BasicStorage,
        type_filter: str,
        tag_query: Mapping,
        page_size: int = None,
        options: Mapping = None,
    ):
        """
        Initialize a `BasicStorageRecordSearch` instance.

        Args:
            store: `BaseStorage` to search
            type_filter: Filter string
            tag_query: Tags to search
            page_size: Size of page to return
            options: Dictionary of backend-specific options

        """
        super(BasicStorageRecordSearch, self).__init__(
            store, type_filter, tag_query, page_size, options
        )
        self._cache = None
        self._iter = None

    @property
    def opened(self) -> bool:
        """
        Accessor for open state.

        Returns:
            True if opened, else False

        """
        return self._cache is not None

    async def fetch(self, max_count: int) -> Sequence[StorageRecord]:
        """
        Fetch the next list of results from the store.

        Args:
            max_count: Max number of records to return

        Returns:
            A list of `StorageRecord`

        Raises:
            StorageSearchError: If the search query has not been opened

        """
        if not self.opened:
            raise StorageSearchError("Search query has not been opened")
        ret = []
        check_type = self.type_filter
        i = max_count
        while i > 0:
            try:
                id = next(self._iter)
            except StopIteration:
                break
            record = self._cache[id]
            if record.type == check_type and basic_tag_query_match(
                record.tags, self.tag_query
            ):
                ret.append(record)
                i -= 1
        return ret

    async def open(self):
        """Start the search query."""
        self._cache = self._store._records.copy()
        self._iter = iter(self._cache)

    async def close(self):
        """Dispose of the search query."""
        self._cache = None
