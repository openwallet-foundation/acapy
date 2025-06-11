"""Aries-Askar implementation of BaseStorage interface."""

import logging
from typing import Mapping, Optional, Sequence

from aries_askar import AskarError, AskarErrorCode, Session

from ..askar.profile import AskarProfile, AskarProfileSession
from .base import (
    DEFAULT_PAGE_SIZE,
    BaseStorage,
    BaseStorageSearch,
    BaseStorageSearchSession,
    validate_record,
)
from .error import (
    StorageDuplicateError,
    StorageError,
    StorageNotFoundError,
    StorageSearchError,
)
from .record import StorageRecord

LOGGER = logging.getLogger(__name__)


class AskarStorage(BaseStorage):
    """Aries-Askar Non-Secrets interface."""

    def __init__(self, session: AskarProfileSession):
        """Initialize an `AskarStorage` instance.

        Args:
            session: The Askar profile session to use
        """
        self._session = session

    @property
    def session(self) -> Session:
        """Accessor for Askar profile session instance."""
        return self._session

    async def add_record(self, record: StorageRecord):
        """Add a new record to the store.

        Args:
            record: `StorageRecord` to be stored

        """
        LOGGER.debug("Adding record %s", record.id)
        validate_record(record)
        try:
            await self._session.handle.insert(
                record.type, record.id, record.value, record.tags
            )
        except AskarError as err:
            if err.code == AskarErrorCode.DUPLICATE:
                LOGGER.info("Duplicate record: %s/%s", record.type, record.id)
                raise StorageDuplicateError(
                    f"Duplicate record: {record.type}/{record.id}"
                ) from None

            LOGGER.error("Error when adding storage record: %s", err)
            raise StorageError("Error when adding storage record") from err

    async def get_record(
        self, record_type: str, record_id: str, options: Optional[Mapping] = None
    ) -> StorageRecord:
        """Fetch a record from the store by type and ID.

        Args:
            record_type: The record type
            record_id: The record id
            options: A dictionary of backend-specific options

        Returns:
            A `StorageRecord` instance

        Raises:
            StorageError: If the record is not provided
            StorageError: If the record ID not provided
            StorageNotFoundError: If the record is not found
            StorageError: If record not found

        """
        if not record_type:
            raise StorageError("Record type not provided")
        if not record_id:
            raise StorageError("Record ID not provided")

        LOGGER.debug("Fetching record %s", record_id)
        for_update = bool(options and options.get("forUpdate"))
        try:
            item = await self._session.handle.fetch(
                record_type, record_id, for_update=for_update
            )
        except AskarError as err:
            LOGGER.error("Error when fetching storage record: %s", err)
            raise StorageError("Error when fetching storage record") from err

        if not item:
            LOGGER.debug("Record not found for type/id: %s/%s", record_type, record_id)
            raise StorageNotFoundError(f"Record not found: {record_type}/{record_id}")

        return StorageRecord(
            type=item.category,
            id=item.name,
            value=None if item.value is None else item.value.decode("utf-8"),
            tags=item.tags or {},
        )

    async def update_record(self, record: StorageRecord, value: str, tags: Mapping):
        """Update an existing stored record's value.

        Args:
            record: `StorageRecord` to update
            value: The new value
            tags: The new tags

        Raises:
            StorageNotFoundError: If record not found
            StorageError: If a libindy error occurs

        """
        LOGGER.debug("Updating record %s", record.id)
        validate_record(record)
        try:
            await self._session.handle.replace(record.type, record.id, value, tags)
        except AskarError as err:
            if err.code == AskarErrorCode.NOT_FOUND:
                LOGGER.info("Record not found for update: %s/%s", record.type, record.id)
                raise StorageNotFoundError("Record not found") from None

            LOGGER.error("Error when updating storage record: %s", err)
            raise StorageError("Error when updating storage record value") from err

    async def delete_record(self, record: StorageRecord):
        """Delete a record.

        Args:
            record: `StorageRecord` to delete

        Raises:
            StorageNotFoundError: If record not found
            StorageError: If a libindy error occurs

        """
        LOGGER.debug("Deleting record %s", record.id)
        validate_record(record, delete=True)
        try:
            await self._session.handle.remove(record.type, record.id)
        except AskarError as err:
            if err.code == AskarErrorCode.NOT_FOUND:
                LOGGER.info(
                    "Record not found for deletion: %s/%s", record.type, record.id
                )
                raise StorageNotFoundError(
                    f"Record not found: {record.type}/{record.id}"
                ) from None

            LOGGER.error("Error when deleting storage record: %s", err)
            raise StorageError("Error when removing storage record") from err

    async def find_record(
        self, type_filter: str, tag_query: Mapping, options: Optional[Mapping] = None
    ) -> StorageRecord:
        """Find a record using a unique tag filter.

        Args:
            type_filter: Filter string
            tag_query: Tags to query
            options: Dictionary of backend-specific options
        """
        LOGGER.debug("Finding record %s with tag query %s", type_filter, tag_query)
        for_update = bool(options and options.get("forUpdate"))
        try:
            results = await self._session.handle.fetch_all(
                type_filter, tag_query, limit=2, for_update=for_update
            )
        except AskarError as err:
            LOGGER.info("Error when finding storage record: %s", err)
            raise StorageError("Error when finding storage record") from err

        if len(results) > 1:
            LOGGER.info("Duplicate records found: %s", results)
            raise StorageDuplicateError("Duplicate records found")

        if not results:
            LOGGER.debug(
                "Record not found with filter / tag query: %s / %s",
                type_filter,
                tag_query,
            )
            raise StorageNotFoundError("Record not found")

        row = results[0]
        return StorageRecord(
            type=row.category,
            id=row.name,
            value=None if row.value is None else row.value.decode("utf-8"),
            tags=row.tags,
        )

    async def find_paginated_records(
        self,
        type_filter: str,
        tag_query: Optional[Mapping] = None,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> Sequence[StorageRecord]:
        """Retrieve a page of records matching a particular type filter and tag query.

        Args:
            type_filter: The type of records to filter by
            tag_query: An optional dictionary of tag filter clauses
            limit: The maximum number of records to retrieve
            offset: The offset to start retrieving records from
            order_by: An optional field by which to order the records.
            descending: Whether to order the records in descending order.

        Returns:
            A sequence of StorageRecord matching the filter and query parameters.
        """
        results = []

        LOGGER.debug(
            "Scanning records (paginated: limit=%d, offset=%d) for %s with tag query %s",
            limit,
            offset,
            type_filter,
            tag_query,
        )
        async for row in self._session.store.scan(
            category=type_filter,
            tag_filter=tag_query,
            limit=limit,
            offset=offset,
            order_by=order_by,
            descending=descending,
            profile=self._session.profile.settings.get("wallet.askar_profile"),
        ):
            results += (
                StorageRecord(
                    type=row.category,
                    id=row.name,
                    value=None if row.value is None else row.value.decode("utf-8"),
                    tags=row.tags,
                ),
            )
        return results

    async def find_all_records(
        self,
        type_filter: str,
        tag_query: Optional[Mapping] = None,
        order_by: Optional[str] = None,
        descending: bool = False,
        options: Optional[Mapping] = None,
    ):
        """Retrieve all records matching a particular type filter and tag query."""
        LOGGER.debug(
            "Fetching all records for %s with tag query %s", type_filter, tag_query
        )
        for_update = bool(options and options.get("forUpdate"))
        results = []
        for row in await self._session.handle.fetch_all(
            category=type_filter,
            tag_filter=tag_query,
            order_by=order_by,
            descending=descending,
            for_update=for_update,
        ):
            results.append(
                StorageRecord(
                    type=row.category,
                    id=row.name,
                    value=None if row.value is None else row.value.decode("utf-8"),
                    tags=row.tags,
                )
            )
        return results

    async def delete_all_records(
        self,
        type_filter: str,
        tag_query: Optional[Mapping] = None,
    ):
        """Remove all records matching a particular type filter and tag query."""
        LOGGER.debug(
            "Deleting all records for %s with tag query %s", type_filter, tag_query
        )
        await self._session.handle.remove_all(type_filter, tag_query)


class AskarStorageSearch(BaseStorageSearch):
    """Active instance of an Askar storage search query."""

    def __init__(self, profile: AskarProfile):
        """Initialize an `AskarStorageSearch` instance.

        Args:
            profile: The Askar profile instance to use
        """
        self._profile = profile

    def search_records(
        self,
        type_filter: str,
        tag_query: Optional[Mapping] = None,
        page_size: Optional[int] = None,
        options: Optional[Mapping] = None,
    ) -> "AskarStorageSearchSession":
        """Search stored records.

        Args:
            type_filter: Filter string
            tag_query: Tags to query
            page_size: Page size
            options: Dictionary of backend-specific options

        Returns:
            An instance of `AskarStorageSearchSession`

        """
        return AskarStorageSearchSession(
            self._profile, type_filter, tag_query, page_size, options
        )


class AskarStorageSearchSession(BaseStorageSearchSession):
    """Represent an active stored records search."""

    def __init__(
        self,
        profile: AskarProfile,
        type_filter: str,
        tag_query: Mapping,
        page_size: Optional[int] = None,
        options: Optional[Mapping] = None,
    ):
        """Initialize a `AskarStorageSearchSession` instance.

        Args:
            profile: Askar profile instance to search
            type_filter: Filter string
            tag_query: Tags to search
            page_size: Size of page to return
            options: Dictionary of backend-specific options

        """
        self.tag_query = tag_query
        self.type_filter = type_filter
        self.page_size = page_size or DEFAULT_PAGE_SIZE
        self._done = False
        self._profile = profile
        self._scan = None

    @property
    def opened(self) -> bool:
        """Accessor for open state.

        Returns:
            True if opened, else False

        """
        return self._scan is not None

    @property
    def handle(self):
        """Accessor for search handle.

        Returns:
            The handle

        """
        return self._scan

    def __aiter__(self):
        """Async iterator magic method."""
        return self

    async def __anext__(self):
        """Async iterator magic method."""
        if self._done:
            raise StorageSearchError("Search query is complete")
        await self._open()

        try:
            row = await self._scan.__anext__()
        except AskarError as err:
            raise StorageSearchError("Error when fetching search results") from err
        except StopAsyncIteration:
            self._done = True
            self._scan = None
            raise
        return StorageRecord(
            type=row.category,
            id=row.name,
            value=None if row.value is None else row.value.decode("utf-8"),
            tags=row.tags,
        )

    async def fetch(
        self, max_count: Optional[int] = None, offset: Optional[int] = None
    ) -> Sequence[StorageRecord]:
        """Fetch the next list of results from the store.

        Args:
            max_count: Max number of records to return
            offset: The offset to start retrieving records from

        Returns:
            A list of `StorageRecord` instances

        Raises:
            StorageSearchError: If the search query has not been opened

        """
        if self._done:
            raise StorageSearchError("Search query is complete")

        limit = max_count or self.page_size
        LOGGER.debug("Fetching records (limit=%d, offset=%d)", limit, offset or 0)
        await self._open(limit=limit, offset=offset)

        count = 0
        ret = []

        while count < limit:
            try:
                row = await self._scan.__anext__()
            except AskarError as err:
                raise StorageSearchError("Error when fetching search results") from err
            except StopAsyncIteration:
                break

            ret.append(
                StorageRecord(
                    type=row.category,
                    id=row.name,
                    value=None if row.value is None else row.value.decode("utf-8"),
                    tags=row.tags,
                )
            )
            count += 1

        LOGGER.debug("Fetched %d records", len(ret))
        if not ret:
            self._done = True
            self._scan = None

        return ret

    async def _open(self, offset: Optional[int] = None, limit: Optional[int] = None):
        """Start the search query."""
        if self._scan:
            return
        try:
            self._scan = self._profile.store.scan(
                category=self.type_filter,
                tag_filter=self.tag_query,
                offset=offset,
                limit=limit,
                profile=self._profile.settings.get("wallet.askar_profile"),
            )
        except AskarError as err:
            raise StorageSearchError("Error opening search query") from err

    async def close(self):
        """Dispose of the search query."""
        self._done = True
        self._scan = None
