"""
Basic in-memory storage implementation (non-wallet)
"""

from collections import OrderedDict
from typing import Mapping, Sequence

from .base import BaseStorage, BaseStorageRecordSearch
from .error import StorageError, StorageNotFoundError, StorageSearchError
from .record import StorageRecord


class BasicStorage(BaseStorage):
    def __init__(self):
        self._records = OrderedDict()

    async def add_record(self, record: StorageRecord):
        """
        Add a new record to the store
        """
        if not record:
            raise StorageError("No record provided")
        if not record.id:
            raise StorageError("Record has no ID")
        self._records[record.id] = record

    async def get_record(self, record_type: str, record_id: str) -> StorageRecord:
        """
        Fetch a record from the store by ID
        """
        row = self._records.get(record_id)
        if row and row.type == record_type:
            return row
        if not row:
            raise StorageNotFoundError("Record not found: {}".format(record_id))

    async def update_record_value(self, record: StorageRecord, value: str):
        """
        Update an existing stored record's value
        """
        oldrec = self._records.get(record.id)
        if not oldrec:
            raise StorageNotFoundError("Record not found: {}".format(record.id))
        self._records[record.id] = oldrec._replace(value=value)

    async def update_record_tags(self, record: StorageRecord, tags: Mapping):
        """
        Update an existing stored record's tags
        """
        oldrec = self._records.get(record.id)
        if not oldrec:
            raise StorageNotFoundError("Record not found: {}".format(record.id))
        self._records[record.id] = oldrec._replace(tags=dict(tags or {}))

    async def delete_record_tags(self, record: StorageRecord, tags: (Sequence, Mapping)):
        """
        Update an existing stored record's tags
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
        if record.id not in self._records:
            raise StorageNotFoundError("Record not found: {}".format(record.id))
        del self._records[record.id]

    def search_records(self, type_filter: str, tag_query: Mapping = None, page_size: int = None) \
            -> 'BasicStorageRecordSearch':
        return BasicStorageRecordSearch(self, type_filter, tag_query, page_size)


class BasicStorageRecordSearch(BaseStorageRecordSearch):
    def __init__(self, store: BasicStorage,
                 type_filter: str, tag_query: Mapping,
                 page_size: int = None):
        super(BasicStorageRecordSearch, self).__init__(store, type_filter, tag_query, page_size)
        self._cache = None
        self._iter = None

    @property
    def opened(self) -> bool:
        """
        Accessor for open state
        """
        return self._cache is not None

    async def fetch(self, max_count: int) -> Sequence[StorageRecord]:
        """
        Fetch the next list of results from the store
        TODO: implement tag filtering
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
            if record.type == check_type:
                ret.append(record)
                i -= 1
        return ret

    async def open(self):
        """
        Start the search query
        """
        self._cache = self._store._records.copy()
        self._iter = iter(self._cache)

    async def close(self):
        """
        Dispose of the search query
        """
        self._cache = None
