"""Abstract base classes for non-secrets storage."""

from abc import ABC, abstractmethod
from typing import Mapping, Sequence

from .error import StorageError, StorageDuplicateError, StorageNotFoundError
from .record import StorageRecord


DEFAULT_PAGE_SIZE = 100


def validate_record(record: StorageRecord, *, delete=False):
    """Ensure that a record is ready to be saved/updated/deleted."""
    if not record:
        raise StorageError("No record provided")
    if not record.id:
        raise StorageError("Record has no ID")
    if not record.type:
        raise StorageError("Record has no type")
    if not record.value and not delete:
        raise StorageError("Record must have a non-empty value")


class BaseStorage(ABC):
    """Abstract stored records interface."""

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
    async def update_record(self, record: StorageRecord, value: str, tags: Mapping):
        """
        Update an existing stored record's value and tags.

        Args:
            record: `StorageRecord` to update
            value: The new value
            tags: The new tags

        """

    @abstractmethod
    async def delete_record(self, record: StorageRecord):
        """
        Delete an existing record.

        Args:
            record: `StorageRecord` to delete

        """

    async def find_record(
        self, type_filter: str, tag_query: Mapping = None, options: Mapping = None
    ) -> StorageRecord:
        """
        Find a record using a unique tag filter.

        Args:
            type_filter: Filter string
            tag_query: Tags to query
            options: Dictionary of backend-specific options
        """
        scan = self.search_records(type_filter, tag_query, options)
        results = await scan.fetch(2)
        await scan.close()
        if not results:
            raise StorageNotFoundError("Record not found")
        if len(results) > 1:
            raise StorageDuplicateError("Duplicate records found")
        return results[0]

    @abstractmethod
    async def find_all_records(
        self,
        type_filter: str,
        tag_query: Mapping = None,
        options: Mapping = None,
    ):
        """Retrieve all records matching a particular type filter and tag query."""

    @abstractmethod
    async def delete_all_records(
        self,
        type_filter: str,
        tag_query: Mapping = None,
    ):
        """Remove all records matching a particular type filter and tag query."""


class BaseStorageSearch(ABC):
    """Abstract stored records search interface."""

    @abstractmethod
    def search_records(
        self,
        type_filter: str,
        tag_query: Mapping = None,
        page_size: int = None,
        options: Mapping = None,
    ) -> "BaseStorageSearchSession":
        """
        Create a new record query.

        Args:
            type_filter: Filter string
            tag_query: Tags to query
            page_size: Page size
            options: Dictionary of backend-specific options

        Returns:
            An instance of `BaseStorageSearchSession`

        """

    def __repr__(self) -> str:
        """Human readable representation of a `BaseStorage` implementation."""
        return "<{}>".format(self.__class__.__name__)


class BaseStorageSearchSession(ABC):
    """Abstract stored records search session interface."""

    @abstractmethod
    async def fetch(self, max_count: int = None) -> Sequence[StorageRecord]:
        """
        Fetch the next list of results from the store.

        Args:
            max_count: Max number of records to return. If not provided,
              defaults to the backend's preferred page size

        Returns:
            A list of `StorageRecord` instances

        """

    async def close(self):
        """Dispose of the search query."""

    def __aiter__(self):
        """Async iterator magic method."""
        return IterSearch(self)

    def __repr__(self) -> str:
        """Human readable representation of this instance."""
        return "<{}>".format(self.__class__.__name__)


class IterSearch:
    """A generic record search async iterator."""

    def __init__(self, search: BaseStorageSearchSession, page_size: int = None):
        """Instantiate a new `IterSearch` instance."""
        self._buffer = None
        self._page_size = page_size
        self._search = search

    async def __anext__(self):
        """Async iterator magic method."""
        if not self._buffer:
            self._buffer = await self._search.fetch(self._page_size) or []
        try:
            return self._buffer.pop(0)
        except IndexError:
            raise StopAsyncIteration
