from typing import Mapping, Optional, Sequence

from ..database_manager.dbstore import DBStoreError, DBStoreErrorCode, DBStoreSession
from ..core.profile import Profile
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
import asyncio
import logging

LOGGER = logging.getLogger(__name__)


class KanonStorage(BaseStorage):
    """Kanon Non-Secrets interface."""

    def __init__(self, session: Profile):
        self._session = session

    @property
    def session(self) -> DBStoreSession:
        return self._session.dbstore_handle

    async def add_record(
        self, record: StorageRecord, session: Optional[DBStoreSession] = None
    ):
        """Add a new record to storage."""
        validate_record(record)
        if session is None:
            async with self._session.store.session() as temp_session:
                await self._add_record(record, temp_session)
        else:
            await self._add_record(record, session)

    async def _add_record(self, record: StorageRecord, session: DBStoreSession):
        try:
            await session.insert(record.type, record.id, record.value, record.tags)
        except DBStoreError as err:
            if err.code == DBStoreErrorCode.DUPLICATE:
                raise StorageDuplicateError(
                    f"Duplicate record: {record.type}/{record.id}"
                ) from None
            raise StorageError("Error when adding storage record") from err

    async def get_record(
        self,
        record_type: str,
        record_id: str,
        options: Optional[Mapping] = None,
        session: Optional[DBStoreSession] = None,
    ) -> StorageRecord:
        """Retrieve a single record by type and ID."""
        if not record_type:
            raise StorageError("Record type not provided")
        if not record_id:
            raise StorageError("Record ID not provided")
        for_update = bool(options and options.get("forUpdate"))
        if session is None:
            async with self._session.store.session() as temp_session:
                return await self._get_record(
                    record_type, record_id, for_update, temp_session
                )
        return await self._get_record(record_type, record_id, for_update, session)

    async def _get_record(
        self, record_type: str, record_id: str, for_update: bool, session: DBStoreSession
    ) -> StorageRecord:
        try:
            item = await session.fetch(record_type, record_id, for_update=for_update)
        except DBStoreError as err:
            raise StorageError("Error when fetching storage record") from err
        if not item:
            raise StorageNotFoundError(f"Record not found: {record_type}/{record_id}")
        return StorageRecord(
            type=item.category,
            id=item.name,
            value=item.value,  # Already a string from Entry.value
            tags=item.tags or {},
        )

    async def update_record(
        self,
        record: StorageRecord,
        value: str,
        tags: Mapping,
        session: Optional[DBStoreSession] = None,
    ):
        """Update an existing record's value and tags."""
        validate_record(record)
        if session is None:
            async with self._session.store.session() as temp_session:
                await self._update_record(record, value, tags, temp_session)
        else:
            await self._update_record(record, value, tags, session)

    async def _update_record(
        self, record: StorageRecord, value: str, tags: Mapping, session: DBStoreSession
    ):
        try:
            item = await session.fetch(record.type, record.id, for_update=True)
            if not item:
                raise StorageNotFoundError(f"Record not found: {record.type}/{record.id}")
            await session.replace(record.type, record.id, value, tags)
        except DBStoreError as err:
            if err.code == DBStoreErrorCode.NOT_FOUND:
                raise StorageNotFoundError(
                    f"Record not found: {record.type}/{record.id}"
                ) from None
            raise StorageError("Error when updating storage record value") from err

    async def delete_record(
        self, record: StorageRecord, session: Optional[DBStoreSession] = None
    ):
        """Delete a record from storage."""
        validate_record(record, delete=True)
        if session is None:
            async with self._session.store.session() as temp_session:
                await self._delete_record(record, temp_session)
        else:
            await self._delete_record(record, session)

    async def _delete_record(self, record: StorageRecord, session: DBStoreSession):
        try:
            await session.remove(record.type, record.id)
        except DBStoreError as err:
            if err.code == DBStoreErrorCode.NOT_FOUND:
                raise StorageNotFoundError(
                    f"Record not found: {record.type}/{record.id}"
                ) from None
            raise StorageError("Error when removing storage record") from err

    async def find_record(
        self,
        type_filter: str,
        tag_query: Mapping,
        options: Optional[Mapping] = None,
        session: Optional[DBStoreSession] = None,
    ) -> StorageRecord:
        """Find a single record matching the type and tag query."""
        for_update = bool(options and options.get("forUpdate"))
        if session is None:
            async with self._session.store.session() as temp_session:
                return await self._find_record(
                    type_filter, tag_query, for_update, temp_session
                )
        return await self._find_record(type_filter, tag_query, for_update, session)

    async def _find_record(
        self,
        type_filter: str,
        tag_query: Mapping,
        for_update: bool,
        session: DBStoreSession,
    ) -> StorageRecord:
        try:
            results = await session.fetch_all(
                type_filter, tag_query, limit=2, for_update=for_update
            )
        except DBStoreError as err:
            raise StorageError("Error when finding storage record") from err
        if len(results) > 1:
            raise StorageDuplicateError("Duplicate records found")
        if not results:
            raise StorageNotFoundError("Record not found")
        row = results[0]
        return StorageRecord(
            type=row.category,
            id=row.name,
            value=row.value,  # Already a string from Entry.value
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
        """Retrieve paginated records using DBStore.scan."""
        LOGGER.debug(
            f"KanonStorage.find_paginated_records called with type_filter={type_filter}, tag_query={tag_query}, limit={limit}, offset={offset}, order_by={order_by}, descending={descending}"
        )
        results = []
        scan = self._session.store.scan(
            category=type_filter,
            tag_filter=tag_query,
            limit=limit,
            offset=offset,
            profile=self._session.profile.name,
            order_by=order_by,
            descending=descending,
        )
        async for row in scan:
            results.append(
                StorageRecord(
                    type=row.category,
                    id=row.name,
                    value=row.value,  # Already a string from Entry.value
                    tags=row.tags,
                )
            )
        return results

    async def find_paginated_records_keyset(
        self,
        type_filter: str,
        tag_query: Optional[Mapping] = None,
        last_id: int = None,
        limit: int = DEFAULT_PAGE_SIZE,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> Sequence[StorageRecord]:
        """Retrieve paginated records using DBStore.scan_keyset."""
        LOGGER.debug(
            f"KanonStorage.find_paginated_records_keyset called with type_filter={type_filter}, tag_query={tag_query}, last_id={last_id}, limit={limit}, order_by={order_by}, descending={descending}"
        )
        results = []
        scan = self._session.store.scan_keyset(
            category=type_filter,
            tag_filter=tag_query,
            last_id=last_id,
            limit=limit,
            profile=self._session.profile.name,
            order_by=order_by,
            descending=descending,
        )
        async for row in scan:
            results.append(
                StorageRecord(
                    type=row.category,
                    id=row.name,
                    value=row.value,  # DBStore returns a string from Entry.value
                    tags=row.tags,
                )
            )
        return results

    async def find_all_records(
        self,
        type_filter: str,
        tag_query: Optional[Mapping] = None,
        order_by: Optional[str] = None,
        descending: bool = False,
        options: Optional[Mapping] = None,
        session: Optional[DBStoreSession] = None,
    ) -> Sequence[StorageRecord]:
        """Retrieve all records matching the type and tag query."""
        for_update = bool(options and options.get("forUpdate"))
        if session is None:
            async with self._session.store.session() as temp_session:
                return await self._find_all_records(
                    type_filter, tag_query, order_by, descending, for_update, temp_session
                )
        return await self._find_all_records(
            type_filter, tag_query, order_by, descending, for_update, session
        )

    async def _find_all_records(
        self,
        type_filter: str,
        tag_query: Optional[Mapping],
        order_by: Optional[str],
        descending: bool,
        for_update: bool,
        session: DBStoreSession,
    ) -> Sequence[StorageRecord]:
        results = []
        try:
            for row in await session.fetch_all(
                type_filter,
                tag_query,
                order_by=order_by,
                descending=descending,
                for_update=for_update,
            ):
                results.append(
                    StorageRecord(
                        type=row.category,
                        id=row.name,
                        value=row.value,  # DBStore returns a string from Entry.value
                        tags=row.tags,
                    )
                )
        except DBStoreError as err:
            raise StorageError("Failed to fetch records") from err
        return results

    async def delete_all_records(
        self,
        type_filter: str,
        tag_query: Optional[Mapping] = None,
        session: Optional[DBStoreSession] = None,
    ):
        """Delete all records matching the type and tag query."""
        if session is None:
            async with self._session.store.session() as temp_session:
                await self._delete_all_records(type_filter, tag_query, temp_session)
        else:
            await self._delete_all_records(type_filter, tag_query, session)

    async def _delete_all_records(
        self, type_filter: str, tag_query: Optional[Mapping], session: DBStoreSession
    ):
        try:
            await session.remove_all(type_filter, tag_query)
        except DBStoreError as err:
            raise StorageError("Error when deleting records") from err


class KanonStorageSearch(BaseStorageSearch):
    def __init__(self, profile: Profile):
        self._profile = profile

    def search_records(
        self,
        type_filter: str,
        tag_query: Optional[Mapping] = None,
        page_size: Optional[int] = None,
        options: Optional[Mapping] = None,
    ) -> "KanonStorageSearchSession":
        return KanonStorageSearchSession(
            self._profile, type_filter, tag_query, page_size, options
        )


class KanonStorageSearchSession(BaseStorageSearchSession):
    def __init__(
        self,
        profile,
        type_filter: str,
        tag_query: Mapping,
        page_size: Optional[int] = None,
        options: Optional[Mapping] = None,
    ):
        self.tag_query = tag_query
        self.type_filter = type_filter
        self.page_size = page_size or DEFAULT_PAGE_SIZE
        self._done = False
        self._profile = profile
        self._scan = None
        self._timeout_task = None

    @property
    def opened(self) -> bool:
        return self._scan is not None

    @property
    def handle(self):
        return self._scan

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._done:
            raise StorageSearchError("Search query is complete")
        await self._open()
        try:
            row = await self._scan.__anext__()
            LOGGER.debug("Fetched row: category=%s, name=%s", row.category, row.name)
        except DBStoreError as err:
            await self.close()
            raise StorageSearchError("Error when fetching search results") from err
        except StopAsyncIteration:
            await self.close()
            raise
        return StorageRecord(
            type=row.category,
            id=row.name,
            value=row.value,  # DBStore returns a string from Entry.value
            tags=row.tags,
        )

    async def fetch(
        self, max_count: Optional[int] = None, offset: Optional[int] = None
    ) -> Sequence[StorageRecord]:
        if self._done:
            raise StorageSearchError("Search query is complete")
        limit = max_count or self.page_size
        await self._open(limit=limit, offset=offset)
        count = 0
        ret = []
        while count < limit:
            try:
                row = await self._scan.__anext__()
                LOGGER.debug("Fetched row: category=%s, name=%s", row.category, row.name)
                ret.append(
                    StorageRecord(
                        type=row.category,
                        id=row.name,
                        value=row.value,  # DBStore returns a string from Entry.value
                        tags=row.tags,
                    )
                )
                count += 1
            except DBStoreError as err:
                await self.close()
                raise StorageSearchError("Error when fetching search results") from err
            except StopAsyncIteration:
                break
        if not ret:
            await self.close()
        return ret

    async def _open(self, offset: Optional[int] = None, limit: Optional[int] = None):
        if self._scan:
            return
        try:
            LOGGER.debug(
                "Opening scan for type_filter=%s, tag_query=%s, limit=%s, offset=%s",
                self.type_filter,
                self.tag_query,
                limit,
                offset,
            )
            self._scan = self._profile.opened.db_store.scan(
                category=self.type_filter,
                tag_filter=self.tag_query,
                offset=offset,
                limit=limit,
                profile=self._profile.name,
            )
            # Start a timeout task to ensure closure
            self._timeout_task = asyncio.create_task(self._timeout_close())
        except DBStoreError as err:
            raise StorageSearchError("Error opening search query") from err

    async def _timeout_close(self):
        """Close the scan after a timeout to prevent leaks."""
        await asyncio.sleep(30)  # 30-second timeout
        if self._scan and not self._done:
            LOGGER.warning("Scan timeout reached, forcing closure")
            await self.close()

    async def close(self):
        if self._timeout_task:
            self._timeout_task.cancel()
            self._timeout_task = None
        if self._scan:
            try:
                await self._scan.close()
                LOGGER.debug("Closed KanonStorageSearchSession scan")
            except Exception as e:
                LOGGER.error("Error closing scan: %s", e)
            finally:
                self._scan = None
        self._done = True

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()
        if exc_type:
            LOGGER.error("Exception in KanonStorageSearchSession: %s", exc)
        return False
