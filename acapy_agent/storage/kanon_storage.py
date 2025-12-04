"""Kanon storage implementation for non-secrets storage."""

import asyncio
import inspect
import logging
from typing import Mapping, Optional, Sequence

from ..core.profile import Profile
from ..database_manager.dbstore import DBStoreError, DBStoreErrorCode, DBStoreSession
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

ERR_FETCH_SEARCH_RESULTS = "Error when fetching search results"


class KanonStorage(BaseStorage):
    """Kanon Non-Secrets interface."""

    def __init__(self, session: Profile):
        """Initialize KanonStorage with a profile session."""
        self._session = session

    @property
    def session(self) -> DBStoreSession:
        """Get the database session."""
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
            await self._call_handle_or_session(
                session, "insert", record.type, record.id, record.value, record.tags
            )
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
            item = await self._call_handle_or_session(
                session, "fetch", record_type, record_id, for_update=for_update
            )
        except DBStoreError as err:
            raise StorageError("Error when fetching storage record") from err
        if not item:
            raise StorageNotFoundError(f"Record not found: {record_type}/{record_id}")
        return StorageRecord(
            type=item.category,
            id=item.name,
            value=item.value,
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
            item = await self._call_handle_or_session(
                session, "fetch", record.type, record.id, for_update=True
            )
            if not item:
                raise StorageNotFoundError(f"Record not found: {record.type}/{record.id}")
            await self._call_handle_or_session(
                session, "replace", record.type, record.id, value, tags
            )
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
            await self._call_handle_or_session(session, "remove", record.type, record.id)
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
            results = await self._call_handle_or_session(
                session,
                "fetch_all",
                type_filter,
                tag_query,
                limit=2,
                for_update=for_update,
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
            value=row.value,
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
            "find_paginated_records: type=%s, tags=%s, limit=%s, "
            "offset=%s, order=%s, desc=%s",
            type_filter,
            tag_query,
            limit,
            offset,
            order_by,
            descending,
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
                    value=row.value,
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
            "find_paginated_records_keyset: type=%s, tags=%s, last_id=%s, "
            "limit=%s, order=%s, desc=%s",
            type_filter,
            tag_query,
            last_id,
            limit,
            order_by,
            descending,
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
                    value=row.value,
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
            for row in await self._call_handle_or_session(
                session,
                "fetch_all",
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
                        value=row.value,
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
            await self._call_handle_or_session(
                session, "remove_all", type_filter, tag_query
            )
        except DBStoreError as err:
            raise StorageError("Error when deleting records") from err

    async def _call_handle_or_session(self, session, method_name: str, *args, **kwargs):
        """Call a DB session method handling both sync handle.* and async session.*.

        If session.handle.<method> exists and is synchronous, call it directly.
        If it is asynchronous (coroutine or async generator),
        delegate to session.<method>.
        Otherwise, call/await session.<method> appropriately.
        """
        prefer_session_first = method_name in {"fetch_all", "remove_all"}

        if prefer_session_first:
            smethod = getattr(session, method_name, None)
            if smethod is not None and callable(smethod):
                try:
                    if inspect.iscoroutinefunction(smethod) or inspect.isasyncgenfunction(
                        smethod
                    ):
                        return await smethod(*args, **kwargs)
                    return smethod(*args, **kwargs)
                except TypeError:
                    handle = getattr(session, "handle", None)
                    if handle is not None and hasattr(handle, method_name):
                        hmethod = getattr(handle, method_name)
                        if inspect.iscoroutinefunction(hmethod):
                            return await hmethod(*args, **kwargs)
                        if inspect.isasyncgenfunction(hmethod):
                            results = []
                            async for item in hmethod(*args, **kwargs):
                                results.append(item)
                            return results
                        return hmethod(*args, **kwargs)
        else:
            handle = getattr(session, "handle", None)
            if handle is not None and hasattr(handle, method_name):
                hmethod = getattr(handle, method_name)
                if callable(hmethod):
                    if inspect.iscoroutinefunction(hmethod):
                        return await hmethod(*args, **kwargs)
                    if not inspect.isasyncgenfunction(hmethod):
                        return hmethod(*args, **kwargs)
            smethod = getattr(session, method_name, None)
            if smethod is not None and callable(smethod):
                if inspect.iscoroutinefunction(smethod) or inspect.isasyncgenfunction(
                    smethod
                ):
                    return await smethod(*args, **kwargs)
                return smethod(*args, **kwargs)

        handle = getattr(session, "handle", None)
        if handle is not None and hasattr(handle, method_name):
            hmethod = getattr(handle, method_name)
            if callable(hmethod):
                if inspect.iscoroutinefunction(hmethod):
                    return await hmethod(*args, **kwargs)
                if inspect.isasyncgenfunction(hmethod):
                    results = []
                    async for item in hmethod(*args, **kwargs):
                        results.append(item)
                    return results
                return hmethod(*args, **kwargs)
        raise AttributeError(f"Session does not provide method {method_name}")


class KanonStorageSearch(BaseStorageSearch):
    """Kanon storage search interface."""

    def __init__(self, profile: Profile):
        """Initialize KanonStorageSearch with a profile."""
        self._profile = profile

    def search_records(
        self,
        type_filter: str,
        tag_query: Optional[Mapping] = None,
        page_size: Optional[int] = None,
        options: Optional[Mapping] = None,
    ) -> "KanonStorageSearchSession":
        """Search for records."""
        return KanonStorageSearchSession(
            self._profile, type_filter, tag_query, page_size, options
        )


class KanonStorageSearchSession(BaseStorageSearchSession):
    """Kanon storage search session."""

    def __init__(
        self,
        profile,
        type_filter: str,
        tag_query: Mapping,
        page_size: Optional[int] = None,
        options: Optional[Mapping] = None,
    ):
        """Initialize search session with filter parameters."""
        self.tag_query = tag_query
        self.type_filter = type_filter
        self.page_size = page_size or DEFAULT_PAGE_SIZE
        self._done = False
        self._profile = profile
        self._scan = None
        self._timeout_task = None

    @property
    def opened(self) -> bool:
        """Check if search is opened."""
        return self._scan is not None

    @property
    def handle(self):
        """Get search handle."""
        return self._scan

    def __aiter__(self):
        """Return async iterator."""
        return self

    async def __anext__(self):
        """Get next item from search."""
        if self._done:
            raise StorageSearchError("Search query is complete")
        await self._open()
        try:
            if hasattr(self._scan, "__anext__"):
                row = await self._scan.__anext__()
            elif inspect.isawaitable(self._scan):
                # Awaitable scan: will raise DBStoreError per test, map to
                # StorageSearchError
                await self._scan
                await self.close()
                raise StopAsyncIteration
            else:
                # Synchronous iterator fallback
                row = next(self._scan)
            LOGGER.debug("Fetched row: category=%s, name=%s", row.category, row.name)
        except DBStoreError as err:
            await self.close()
            raise StorageSearchError(ERR_FETCH_SEARCH_RESULTS) from err
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
        """Fetch records."""
        if self._done:
            raise StorageSearchError("Search query is complete")
        limit = max_count or self.page_size
        await self._open(limit=limit, offset=offset)
        count = 0
        ret = []
        done = False
        if not hasattr(self._scan, "__anext__") and inspect.isawaitable(self._scan):
            try:
                await self._scan
            except DBStoreError as err:
                await self.close()
                raise StorageSearchError(ERR_FETCH_SEARCH_RESULTS) from err
            # No rows yielded
            await self.close()
            return ret
        while count < limit:
            try:
                if hasattr(self._scan, "__anext__"):
                    row = await self._scan.__anext__()
                else:
                    row = next(self._scan)
                LOGGER.debug("Fetched row: category=%s, name=%s", row.category, row.name)
                ret.append(
                    StorageRecord(
                        type=row.category,
                        id=row.name,
                        value=row.value,
                        tags=row.tags,
                    )
                )
                count += 1
            except DBStoreError as err:
                await self.close()
                raise StorageSearchError(ERR_FETCH_SEARCH_RESULTS) from err
            except StopAsyncIteration:
                done = True
                break
        if done or not ret:
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

            self._timeout_task = asyncio.create_task(self._timeout_close())
        except DBStoreError as err:
            raise StorageSearchError("Error opening search query") from err

    async def _timeout_close(self):
        """Close the scan after a timeout to prevent leaks."""
        await asyncio.sleep(30)
        if self._scan and not self._done:
            LOGGER.warning("Scan timeout reached, forcing closure")
            await self.close()

    async def close(self):
        """Close search session."""
        if self._timeout_task:
            self._timeout_task.cancel()
            self._timeout_task = None
        if self._scan:
            try:
                aclose = getattr(self._scan, "aclose", None)
                if aclose:
                    await aclose()
                else:
                    close = getattr(self._scan, "close", None)
                    if close:
                        res = close()
                        if inspect.iscoroutine(res):
                            await res
                LOGGER.debug("Closed KanonStorageSearchSession scan")
            except Exception:
                pass
            finally:
                self._scan = None
        self._done = True

    async def __aexit__(self, exc_type, exc, tb):
        """Exit async context manager."""
        await self.close()
        if exc_type:
            LOGGER.error("Exception in KanonStorageSearchSession: %s", exc)
        return False
