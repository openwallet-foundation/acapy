"""
Abstract base classes for non-secrets storage
"""

from abc import ABC, abstractmethod
from typing import Mapping, Sequence

from .record import StorageRecord

DEFAULT_PAGE_SIZE = 100


class BaseStorage(ABC):
    """
    Abstract Non-Secrets interface
    """

    @abstractmethod
    async def add_record(self, record: StorageRecord):
        """
        Add a new record to the store
        """
        # indy_add_wallet_record
        pass

    @abstractmethod
    async def get_record(self, record_type: str, record_id: str) -> StorageRecord:
        """
        Fetch a record from the store by type and ID
        """
        pass

    @abstractmethod
    async def update_record_value(self, record: StorageRecord, value: str):
        """
        Update an existing stored record's value
        """
        # indy_update_wallet_record_value
        pass

    @abstractmethod
    async def update_record_tags(self, record: StorageRecord, tags: Mapping):
        """
        Update an existing stored record's tags
        """
        # indy_update_wallet_record_tags
        pass

    @abstractmethod
    async def delete_record_tags(
        self, record: StorageRecord, tags: (Sequence, Mapping)
    ):
        """
        Update an existing stored record's tags
        """
        # indy_delete_wallet_record_tags
        pass

    @abstractmethod
    async def delete_record(self, record: StorageRecord):
        # indy_delete_wallet_record
        pass

    @abstractmethod
    def search_records(
        self, type_filter: str, tag_query: Mapping = None, page_size: int = None
    ) -> "BaseStorageRecordSearch":
        pass

    def __repr__(self) -> str:
        return "<{}>".format(self.__class__.__name__)


class BaseStorageRecordSearch(ABC):
    """
    Represent an active stored records search
    """

    def __init__(
        self,
        store: BaseStorage,
        type_filter: str,
        tag_query: Mapping,
        page_size: int = None,
    ):
        self._buffer = None
        self._page_size = page_size
        self._store = store
        self._tag_query = tag_query
        self._type_filter = type_filter

    @property
    def handle(self):
        """
        Return handle to active storage search
        """
        return None

    @property
    @abstractmethod
    def opened(self) -> bool:
        """
        Accessor for open state
        """
        return False

    @property
    def page_size(self):
        """
        Return page size for this search query
        """
        return self._page_size or DEFAULT_PAGE_SIZE

    @property
    def store(self) -> BaseStorage:
        """
        Return reference to store
        """
        return self._store

    @property
    def tag_query(self):
        """
        Return the query to filter results according to tag values
        """
        return self._tag_query

    @property
    def type_filter(self):
        """
        Return the type value used to filter results
        """
        return self._type_filter

    @abstractmethod
    async def fetch(self, max_count: int) -> Sequence[StorageRecord]:
        """
        Fetch the next list of results from the store
        """
        pass

    @abstractmethod
    async def open(self):
        """
        Start the search query
        """
        pass

    @abstractmethod
    async def close(self):
        """
        Dispose of the search query
        """
        pass

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.opened:
            await self.open()
        if not self._buffer:
            self._buffer = await self.fetch(self.page_size)
            if not self._buffer:
                await self.close()
                raise StopAsyncIteration
        try:
            return self._buffer.pop(0)
        except IndexError:
            raise StopAsyncIteration

    def __repr__(self) -> str:
        return "<{}>".format(self.__class__.__name__)
