"""Basic in-memory storage implementation (non-wallet)."""

from typing import Mapping, Sequence

from ..core.in_memory import InMemoryProfile

from .base import (
    DEFAULT_PAGE_SIZE,
    BaseStorage,
    BaseStorageRecordSearch,
    validate_record,
)
from .error import (
    StorageDuplicateError,
    StorageNotFoundError,
    StorageSearchError,
)
from .record import StorageRecord


class InMemoryStorage(BaseStorage):
    """Basic in-memory storage class."""

    def __init__(self, profile: InMemoryProfile):
        """
        Initialize a `InMemoryStorage` instance.

        Args:
            profile: The in-memory profile instance

        """
        self.profile = profile

    async def add_record(self, record: StorageRecord):
        """
        Add a new record to the store.

        Args:
            record: `StorageRecord` to be stored

        Raises:
            StorageError: If no record is provided
            StorageError: If the record has no ID

        """
        validate_record(record)
        if record.id in self.profile.records:
            raise StorageDuplicateError("Duplicate record")
        self.profile.records[record.id] = record

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
        row = self.profile.records.get(record_id)
        if row and row.type == record_type:
            return row
        if not row:
            raise StorageNotFoundError("Record not found: {}".format(record_id))

    async def update_record(self, record: StorageRecord, value: str, tags: Mapping):
        """
        Update an existing stored record's value.

        Args:
            record: `StorageRecord` to update
            value: The new value
            tags: The new tags

        Raises:
            StorageNotFoundError: If record not found

        """
        validate_record(record)
        oldrec = self.profile.records.get(record.id)
        if not oldrec:
            raise StorageNotFoundError("Record not found: {}".format(record.id))
        self.profile.records[record.id] = oldrec._replace(value=value, tags=tags)

    async def delete_record(self, record: StorageRecord):
        """
        Delete a record.

        Args:
            record: `StorageRecord` to delete

        Raises:
            StorageNotFoundError: If record not found

        """
        validate_record(record, delete=True)
        if record.id not in self.profile.records:
            raise StorageNotFoundError("Record not found: {}".format(record.id))
        del self.profile.records[record.id]

    def search_records(
        self,
        type_filter: str,
        tag_query: Mapping = None,
        page_size: int = None,
        options: Mapping = None,
    ) -> "InMemoryStorageRecordSearch":
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
        return InMemoryStorageRecordSearch(
            self.profile, type_filter, tag_query, page_size, options
        )


def tag_value_match(value: str, match: dict) -> bool:
    """Match a single tag against a tag subquery.

    TODO: What type coercion is needed? (support int or float values?)
    """
    if len(match) != 1:
        raise StorageSearchError("Unsupported subquery: {}".format(match))
    if value is None:
        return False
    op = list(match.keys())[0]
    cmp_val = match[op]
    if op == "$in":
        if not isinstance(cmp_val, list):
            raise StorageSearchError("Expected list for $in value")
        chk = value in cmp_val
    else:
        if not isinstance(cmp_val, str):
            raise StorageSearchError("Expected string for filter value")
        if op == "$neq":
            chk = value != cmp_val
        elif op == "$gt":
            chk = float(value) > float(cmp_val)
        elif op == "$gte":
            chk = float(value) >= float(cmp_val)
        elif op == "$lt":
            chk = float(value) < float(cmp_val)
        elif op == "$lte":
            chk = float(value) <= float(cmp_val)
        # elif op == "$like":  NYI
        else:
            raise StorageSearchError(f"Unsupported match operator: {op}")
    return chk


def tag_query_match(tags: dict, tag_query: dict) -> bool:
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
                    if tag_query_match(tags, opt):
                        chk = True
                        break
            elif k == "$not":
                if not isinstance(v, dict):
                    raise StorageSearchError("Expected dict for $not filter value")
                chk = not tag_query_match(tags, v)
            elif k[0] == "$":
                raise StorageSearchError("Unexpected filter operator: {}".format(k))
            elif isinstance(v, str):
                chk = tags.get(k) == v
            elif isinstance(v, dict):
                chk = tag_value_match(tags.get(k), v)
            else:
                raise StorageSearchError(
                    "Expected string or dict for filter value, got {}".format(v)
                )
            if not chk:
                result = False
                break
    return result


class InMemoryStorageRecordSearch(BaseStorageRecordSearch):
    """Represent an active stored records search."""

    def __init__(
        self,
        profile: InMemoryProfile,
        type_filter: str,
        tag_query: Mapping,
        page_size: int = None,
        options: Mapping = None,
    ):
        """
        Initialize a `InMemoryStorageRecordSearch` instance.

        Args:
            store: `BaseStorage` to search
            type_filter: Filter string
            tag_query: Tags to search
            page_size: Size of page to return
            options: Dictionary of backend-specific options

        """
        self._cache = profile.records.copy()
        self._iter = iter(self._cache)
        self.page_size = page_size or DEFAULT_PAGE_SIZE
        self.tag_query = tag_query
        self.type_filter = type_filter

    async def fetch(self, max_count: int = None) -> Sequence[StorageRecord]:
        """
        Fetch the next list of results from the store.

        Args:
            max_count: Max number of records to return. If not provided,
              defaults to the backend's preferred page size

        Returns:
            A list of `StorageRecord` instances

        Raises:
            StorageSearchError: If the search query has not been opened

        """
        if self._cache is None:
            raise StorageSearchError("Search query is complete")

        ret = []
        check_type = self.type_filter
        i = max_count or self.page_size

        while i > 0:
            try:
                id = next(self._iter)
            except StopIteration:
                break
            record = self._cache[id]
            if record.type == check_type and tag_query_match(
                record.tags, self.tag_query
            ):
                ret.append(record)
                i -= 1

        if not ret:
            self._cache = None

        return ret

    async def close(self):
        """Dispose of the search query."""
        self._cache = None
