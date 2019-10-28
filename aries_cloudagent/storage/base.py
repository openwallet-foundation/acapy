"""Abstract base classes for non-secrets storage."""

from abc import ABC, abstractmethod
from typing import Mapping, Sequence

from .error import StorageDuplicateError, StorageNotFoundError
from .record import StorageRecord


DEFAULT_PAGE_SIZE = 100


class BaseStorage(ABC):
    """Abstract Non-Secrets interface."""

    @abstractmethod
    async def add_record(self, record: StorageRecord):
        """
        Add a new record to the store.

        Args:
            record: `StorageRecord` to be stored

        """

    @abstractmethod
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

        """

    @abstractmethod
    async def update_record_value(self, record: StorageRecord, value: str):
        """
        Update an existing stored record's value.

        Args:
            record: `StorageRecord` to update
            value: The new value

        """

    @abstractmethod
    async def update_record_tags(self, record: StorageRecord, tags: Mapping):
        """
        Update an existing stored record's tags.

        Args:
            record: `StorageRecord` to update
            tags: New tags

        """

    @abstractmethod
    async def delete_record_tags(
        self, record: StorageRecord, tags: (Sequence, Mapping)
    ):
        """
        Update an existing stored record's tags.

        Args:
            record: `StorageRecord` to delete
            tags: Tags

        """

    @abstractmethod
    async def delete_record(self, record: StorageRecord):
        """
        Delete an existing record.

        Args:
            record: `StorageRecord` to delete

        """

    @abstractmethod
    def search_records(
        self,
        type_filter: str,
        tag_query: Mapping = None,
        page_size: int = None,
        options: Mapping = None,
    ) -> "BaseStorageRecordSearch":
        """
        Create a new record query.

        Args:
            type_filter: Filter string
            tag_query: Tags to query
            page_size: Page size
            options: Dictionary of backend-specific options

        Returns:
            An instance of `BaseStorageRecordSearch`

        """

    def __repr__(self) -> str:
        """Human readable representation of a `BaseStorage` implementation."""
        return "<{}>".format(self.__class__.__name__)


class BaseStorageRecordSearch(ABC):
    """Represent an active stored records search."""

    def __init__(
        self,
        store: BaseStorage,
        type_filter: str,
        tag_query: Mapping,
        page_size: int = None,
        options: Mapping = None,
    ):
        """
        Initialize a `BaseStorageRecordSearch` instance.

        Args:
            store: `BaseStorage` to search
            type_filter: Filter string
            tag_query: Tags to search
            page_size: Size of page to return
            options: Dictionary of backend-specific options

        """
        self._buffer = None
        self._page_size = page_size
        self._store = store
        self._tag_query = tag_query
        self._type_filter = type_filter
        self._options = options or {}

    @property
    def handle(self):
        """Handle a search request."""
        return None

    @property
    @abstractmethod
    def opened(self) -> bool:
        """
        Accessor for open state.

        Returns:
            True if opened, else False

        """
        return False

    @property
    def page_size(self) -> int:
        """
        Accessor for page size.

        Returns:
            The page size

        """
        return self._page_size or DEFAULT_PAGE_SIZE

    @property
    def store(self) -> BaseStorage:
        """
        `BaseStorage` backend for this implementation.

        Returns:
            The `BaseStorage` implementation being used

        """
        return self._store

    @property
    def tag_query(self) -> Mapping:
        """
        Accessor for tag query.

        Returns:
            The tag query

        """
        return self._tag_query

    @property
    def type_filter(self) -> str:
        """
        Accessor for type filter.

        Returns:
            The type filter

        """
        return self._type_filter

    @property
    def options(self) -> Mapping:
        """
        Accessor for the search options.

        Returns:
            The search options

        """
        return self._options

    def option(self, name: str, default=None):
        """
        Fetch a named search option, if defined.

        Return:
            The option value or default

        """
        return self._options.get(name, default)

    @abstractmethod
    async def fetch(self, max_count: int) -> Sequence[StorageRecord]:
        """
        Fetch the next list of results from the store.

        Args:
            max_count: Max number of records to return

        Returns:
            A list of `StorageRecord`

        """

    async def fetch_all(self) -> Sequence[StorageRecord]:
        """Fetch all records from the query."""
        results = []
        async for record in self:
            results.append(record)
        return results

    async def fetch_single(self) -> StorageRecord:
        """Fetch a single query result."""
        results = await self.fetch_all()
        if not results:
            raise StorageNotFoundError("Record not found")
        if len(results) > 1:
            raise StorageDuplicateError("Duplicate records found")
        return results[0]

    @abstractmethod
    async def open(self):
        """Start the search query."""

    @abstractmethod
    async def close(self):
        """Dispose of the search query."""

    async def __aenter__(self):
        """Context manager enter."""
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Context manager exit."""
        await self.close()

    def __aiter__(self):
        """Async iterator magic method."""
        return self

    async def __anext__(self):
        """Async iterator magic method."""
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
        """Human readable representation of `BaseStorageRecordSearch`."""
        return "<{}>".format(self.__class__.__name__)
