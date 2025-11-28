"""Database store module for managing different database backends."""

import asyncio
import importlib
import inspect
import json

# anext is a builtin in Python 3.10+
import logging
import threading
from collections.abc import AsyncGenerator, AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Sequence

from .db_types import Entry, EntryList
from .error import DBStoreError, DBStoreErrorCode
from .interfaces import AbstractDatabaseSession, AbstractDatabaseStore, DatabaseBackend

# Logging setup
LOGGER = logging.getLogger(__name__)

# Registry for backends with thread safety
_backend_registry: dict[str, DatabaseBackend] = {}
_registry_lock = threading.Lock()
_BACKEND_REGISTRATION_IMPORT = ".databases.backends.backend_registration"


def register_backend(db_type: str, backend: DatabaseBackend):
    """Register a backend for a given database type."""
    LOGGER.debug(f"Registering backend for db_type={db_type}")
    _backend_registry[db_type] = backend


class Scan(AsyncIterator):
    """Async iterator for database scanning."""

    def __init__(
        self,
        store: "DBStore",
        profile: Optional[str],
        category: str | bytes,
        tag_filter: str | dict = None,
        offset: int = None,
        limit: int = None,
        order_by: Optional[str] = None,
        descending: bool = False,
    ):
        """Initialize DBStoreScan with scan parameters."""
        self._store = store
        self._profile = profile
        self._category = category
        self._tag_filter = tag_filter
        self._offset = offset
        self._limit = limit
        self._order_by = order_by
        self._descending = descending
        self._generator = None
        # Create a ThreadPoolExecutor for running synchronous tasks
        self._executor = ThreadPoolExecutor(max_workers=1)
        # Check if the underlying scan method is async
        self._is_async = inspect.iscoroutinefunction(
            self._store._db.scan
        ) or inspect.isasyncgenfunction(self._store._db.scan)

    async def __anext__(self) -> Entry:
        """Get next item from async scan."""
        if self._generator is None:
            if self._is_async:
                # For async backends (e.g., PostgreSQL), get async generator
                self._generator = self._store._db.scan(
                    self._profile,
                    self._category,
                    self._tag_filter,
                    self._offset,
                    self._limit,
                    self._order_by,
                    self._descending,
                )
            else:
                # For sync backends (e.g., SQLite), run in executor
                def create_generator() -> AsyncIterator[Entry]:
                    return self._store._db.scan(
                        self._profile,
                        self._category,
                        self._tag_filter,
                        self._offset,
                        self._limit,
                        self._order_by,
                        self._descending,
                    )

                loop = asyncio.get_running_loop()
                self._generator = await loop.run_in_executor(
                    self._executor, create_generator
                )

        if self._is_async:
            # Handle async generators
            try:
                return await anext(self._generator)  # noqa: F821
            except StopAsyncIteration:
                LOGGER.error("StopAsyncIteration in __anext__")
                await self.aclose()
                raise
        else:
            # Handle sync generators using the executor
            def get_next() -> Entry | None:
                try:
                    return next(self._generator)
                except StopIteration:
                    return None

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(self._executor, get_next)
            if result is None:
                await self.aclose()
                raise StopAsyncIteration
            return result

    def __del__(self) -> None:
        """Clean up resources."""
        # Shut down the executor to clean up resources
        self._executor.shutdown(wait=False)

    async def aclose(self) -> None:
        """Close the underlying generator and release resources."""
        try:
            if self._generator:
                if self._is_async:
                    agen_aclose = getattr(self._generator, "aclose", None)
                    if agen_aclose:
                        await agen_aclose()
                else:
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(
                        self._executor,
                        lambda: getattr(self._generator, "close", lambda: None)(),
                    )
        finally:
            self._executor.shutdown(wait=False)


class ScanKeyset(AsyncIterator):
    """Keyset-based scan iterator."""

    def __init__(
        self,
        store: "DBStore",
        profile: Optional[str],
        category: str | bytes,
        tag_filter: str | dict = None,
        last_id: Optional[int] = None,
        limit: int = None,
        order_by: Optional[str] = None,
        descending: bool = False,
    ):
        """Initialize the ScanKeyset iterator with filters and sorting."""
        LOGGER.debug(
            f"ScanKeyset initialized with store={store}, "
            f"profile={profile}, category={category}, "
            f"tag_filter={tag_filter}, last_id={last_id}, "
            f"limit={limit}, order_by={order_by}, "
            f"descending={descending}"
        )
        self._store = store
        self._profile = profile
        self._category = category if isinstance(category, str) else category.decode()
        self._tag_filter = tag_filter
        self._last_id = last_id
        self._limit = limit
        self._order_by = order_by
        self._descending = descending
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._generator = None
        # Check if scan_keyset is a coroutine or async generator
        self._is_async = inspect.iscoroutinefunction(
            self._store._db.scan_keyset
        ) or inspect.isasyncgenfunction(self._store._db.scan_keyset)

    async def __anext__(self) -> Entry:
        """Get next item from async keyset scan."""
        if self._generator is None:
            if self._is_async:
                # For async backends (e.g., PostgreSQL), get async generator
                self._generator = self._store._db.scan_keyset(
                    self._profile,
                    self._category,
                    self._tag_filter,
                    self._last_id,
                    self._limit,
                    self._order_by,
                    self._descending,
                )
            else:
                # For sync backends (e.g., SQLite), run scan_keyset in executor
                def create_generator() -> AsyncGenerator[Entry, None]:
                    return self._store._db.scan_keyset(
                        self._profile,
                        self._category,
                        self._tag_filter,
                        self._last_id,
                        self._limit,
                        self._order_by,
                        self._descending,
                    )

                loop = asyncio.get_running_loop()
                self._generator = await loop.run_in_executor(
                    self._executor, create_generator
                )

        if self._is_async:
            # Handle async generators
            try:
                return await anext(self._generator)  # noqa: F821
            except StopAsyncIteration:
                LOGGER.error("StopAsyncIteration in __anext__")
                await self.aclose()
                raise
        else:
            # Handle sync generators using the executor
            def get_next() -> Entry | None:
                try:
                    return next(self._generator)
                except StopIteration:
                    return None

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(self._executor, get_next)
            if result is None:
                await self.aclose()
                raise StopAsyncIteration
            return result

    def __del__(self) -> None:
        """Clean up resources."""
        self._executor.shutdown(wait=False)

    async def aclose(self) -> None:
        """Close the underlying generator and release resources."""
        try:
            if self._generator:
                if self._is_async:
                    agen_aclose = getattr(self._generator, "aclose", None)
                    if agen_aclose:
                        await agen_aclose()
                else:
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(
                        self._executor,
                        lambda: getattr(self._generator, "close", lambda: None)(),
                    )
        finally:
            self._executor.shutdown(wait=False)

    async def fetch_all(self) -> Sequence[Entry]:
        """Perform the action."""
        rows = []
        async for row in self:
            rows.append(row)
        return rows


class DBStore:
    """Database store class."""

    def __init__(
        self, db: AbstractDatabaseStore, uri: str, release_number: str = "release_0"
    ):
        """Initialize DBStore."""
        LOGGER.debug("Store initialized (release_number=%s)", release_number)
        self._db = db
        self._uri = uri
        self._release_number = release_number
        self._opener: Optional[DBOpenSession] = None

    @classmethod
    def generate_raw_key(cls, seed: str | bytes | None = None) -> str:
        """Perform the action."""
        LOGGER.debug("generate_raw_key called (seed_provided=%s)", bool(seed))
        from . import bindings

        return bindings.generate_raw_key(seed)

    @property
    def handle(self):
        """Perform the action."""
        return id(self)

    @property
    def uri(self) -> str:
        """Perform the action."""
        return self._uri

    @property
    def release_number(self) -> str:
        """Perform the action."""
        return self._release_number

    @classmethod
    async def provision(
        cls,
        uri: str,
        key_method: str = None,
        pass_key: str = None,
        *,
        profile: str = None,
        recreate: bool = False,
        release_number: str = "release_0",
        schema_config: Optional[str] = None,
        config: Optional[dict] = None,
    ) -> "DBStore":
        """Provision a new database store with specified release and schema."""
        LOGGER.debug(
            "provision called (recreate=%s, release_number=%s)",
            recreate,
            release_number,
        )
        # Thread-safe backend registration
        with _registry_lock:
            if not _backend_registry:  # Register backends if not already done
                backend_registration = importlib.import_module(
                    _BACKEND_REGISTRATION_IMPORT, package=__package__
                )
                backend_registration.register_backends()
        db_type = uri.split(":")[0]
        backend = _backend_registry.get(db_type)
        if not backend:
            raise DBStoreError(
                DBStoreErrorCode.BACKEND, f"Unsupported database type: {db_type}"
            )
        try:
            if inspect.iscoroutinefunction(backend.provision):
                db = await backend.provision(
                    uri,
                    key_method,
                    pass_key,
                    profile,
                    recreate,
                    release_number,
                    schema_config,
                    config=config,
                )
            else:
                db = await asyncio.to_thread(
                    backend.provision,
                    uri,
                    key_method,
                    pass_key,
                    profile,
                    recreate,
                    release_number,
                    schema_config,
                    config=config,
                )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            LOGGER.error("provision error: %s", type(e).__name__)
            raise backend.translate_error(e)
        return cls(db, uri, release_number)

    @classmethod
    async def open(
        cls,
        uri: str,
        key_method: str = None,
        pass_key: str = None,
        *,
        profile: str = None,
        schema_migration: Optional[bool] = None,
        target_schema_release_number: Optional[str] = None,
        config: Optional[dict] = None,
    ) -> "DBStore":
        """Perform the action."""
        LOGGER.debug(
            "open called (schema_migration=%s, target_schema_release_number=%s)",
            schema_migration,
            target_schema_release_number,
        )
        # Thread-safe backend registration
        with _registry_lock:
            if not _backend_registry:  # Register backends if not already done
                backend_registration = importlib.import_module(
                    _BACKEND_REGISTRATION_IMPORT, package=__package__
                )
                backend_registration.register_backends()
        db_type = uri.split(":")[0]
        backend = _backend_registry.get(db_type)
        if not backend:
            raise DBStoreError(
                DBStoreErrorCode.BACKEND, f"Unsupported database type: {db_type}"
            )
        try:
            if inspect.iscoroutinefunction(backend.open):
                db = await backend.open(
                    uri,
                    key_method,
                    pass_key,
                    profile,
                    schema_migration,
                    target_schema_release_number,
                    config=config,
                )
            else:
                db = await asyncio.to_thread(
                    backend.open,
                    uri,
                    key_method,
                    pass_key,
                    profile,
                    schema_migration,
                    target_schema_release_number,
                    config=config,
                )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            LOGGER.error("open error: %s", type(e).__name__)
            raise backend.translate_error(e)
        return cls(db, uri, db.release_number)

    @classmethod
    async def remove(
        cls, uri: str, release_number: str = "release_0", config: Optional[dict] = None
    ) -> bool:
        """Remove the database store."""
        LOGGER.debug("remove called (release_number=%s)", release_number)
        # Thread-safe backend registration
        with _registry_lock:
            if not _backend_registry:  # Register backends if not already done
                backend_registration = importlib.import_module(
                    _BACKEND_REGISTRATION_IMPORT, package=__package__
                )
                backend_registration.register_backends()
        db_type = uri.split(":")[0]
        backend = _backend_registry.get(db_type)
        if not backend:
            raise DBStoreError(
                DBStoreErrorCode.BACKEND, f"Unsupported database type: {db_type}"
            )
        try:
            if inspect.iscoroutinefunction(backend.remove):
                return await backend.remove(uri, config=config)
            else:
                return await asyncio.to_thread(backend.remove, uri, config=config)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            LOGGER.error("remove error: %s", type(e).__name__)
            raise backend.translate_error(e)

    async def initialize(self) -> None:
        """Initialize the database store."""
        LOGGER.debug("initialize called")
        try:
            if inspect.iscoroutinefunction(self._db.initialize):
                await self._db.initialize()
            else:
                await asyncio.to_thread(self._db.initialize)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            LOGGER.error("initialize error: %s", type(e).__name__)
            raise self._db.translate_error(e)

    async def create_profile(self, name: str = None) -> str:
        """Perform the action."""
        LOGGER.debug(f"create_profile called with name={name}")
        try:
            return await self._db.create_profile(name)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            LOGGER.error("create_profile error: %s", str(e))
            raise self._db.translate_error(e)

    async def get_profile_name(self) -> str:
        """Perform the action."""
        LOGGER.debug("get_profile_name called")
        try:
            return await self._db.get_profile_name()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            LOGGER.error("get_profile_name error: %s", str(e))
            raise self._db.translate_error(e)

    async def remove_profile(self, name: str) -> bool:
        """Perform the action."""
        LOGGER.debug(f"remove_profile called with name={name}")
        try:
            return await self._db.remove_profile(name)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            LOGGER.error("remove_profile error: %s", str(e))
            raise self._db.translate_error(e)

    async def rekey(self, key_method: str = None, pass_key: str = None) -> None:
        """Perform the action."""
        LOGGER.debug(f"rekey called with key_method={key_method}, pass_key=***")
        try:
            await self._db.rekey(key_method, pass_key)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            LOGGER.error("rekey error: %s", str(e))
            raise self._db.translate_error(e)

    def scan(
        self,
        category: str,
        tag_filter: str | dict = None,
        offset: int = None,
        limit: int = None,
        profile: str = None,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> Scan:
        """Scan the database for entries matching the criteria."""
        LOGGER.debug(
            f"scan called with category={category}, tag_filter={tag_filter}, "
            f"offset={offset}, "
            f"limit={limit}, profile={profile}, order_by={order_by}, "
            f"descending={descending}"
        )
        return Scan(
            self, profile, category, tag_filter, offset, limit, order_by, descending
        )

    def scan_keyset(
        self,
        category: str,
        tag_filter: str | dict = None,
        last_id: Optional[int] = None,
        limit: int = None,
        profile: str = None,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> ScanKeyset:
        """Scan the database using keyset pagination."""
        LOGGER.debug(
            f"scan_keyset called with category={category}, "
            f"tag_filter={tag_filter}, last_id={last_id}, "
            f"limit={limit}, profile={profile}, order_by={order_by}, "
            f"descending={descending}"
        )
        return ScanKeyset(
            self, profile, category, tag_filter, last_id, limit, order_by, descending
        )

    def session(self, profile: str = None) -> "DBOpenSession":
        """Perform the action."""
        LOGGER.debug(f"session called with profile={profile}")
        return DBOpenSession(self._db, profile, False, self._release_number)

    def transaction(self, profile: str = None) -> "DBOpenSession":
        """Perform the action."""
        LOGGER.debug(f"transaction called with profile={profile}")
        return DBOpenSession(self._db, profile, True, self._release_number)

    async def close(self, *, remove: bool = False) -> bool:
        """Perform the action."""
        LOGGER.debug(f"close called with remove={remove}")
        try:
            if self._db:
                if inspect.iscoroutinefunction(self._db.close):
                    await self._db.close(remove=remove)
                else:
                    await asyncio.to_thread(self._db.close, remove=remove)
                self._db = None
            LOGGER.debug("close completed")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            LOGGER.error("close failed: %s", str(e))
            raise DBStoreError(DBStoreErrorCode.UNEXPECTED, str(e)) from e

    async def __aenter__(self) -> "DBStoreSession":
        """Enter async context manager."""
        LOGGER.debug("__aenter__ called")
        if not self._opener:
            self._opener = DBOpenSession(self._db, None, False, self._release_number)
        return await self._opener.__aenter__()

    async def __aexit__(self, exc_type, exc, tb):
        """Exit async context manager."""
        LOGGER.debug(f"__aexit__ called with exc_type={exc_type}, exc={exc}, tb={tb}")
        opener = self._opener
        self._opener = None
        return await opener.__aexit__(exc_type, exc, tb)

    def __repr__(self) -> str:
        """Magic method description."""
        return f"<Store(handle={self.handle})>"


class DBStoreSession:
    """Database store session class."""

    def __init__(self, db_session: AbstractDatabaseSession, is_txn: bool):
        """Initialize DBStoreSession."""
        LOGGER.debug(f"Session initialized with db_session={db_session}, is_txn={is_txn}")
        self._db_session = db_session
        self._is_txn = is_txn

    @property
    def is_transaction(self) -> bool:
        """Check if the session is a transaction."""
        return self._is_txn

    @property
    def handle(self):
        """Get a unique identifier for the session."""
        return id(self)

    async def count(self, category: str, tag_filter: str | dict = None) -> int:
        """Perform the action."""
        LOGGER.debug(f"count called with category={category}, tag_filter={tag_filter}")
        try:
            return await self._db_session.count(category, tag_filter)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            LOGGER.error("count error: %s", str(e))
            raise self._db_session.translate_error(e)

    async def fetch(
        self, category: str, name: str, *, for_update: bool = False
    ) -> Optional[Entry]:
        """Perform the action."""
        LOGGER.debug(
            f"fetch called with category={category}, name={name}, for_update={for_update}"
        )
        try:
            return await self._db_session.fetch(
                category, name, tag_filter=None, for_update=for_update
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            LOGGER.error("fetch error: %s", str(e))
            raise self._db_session.translate_error(e)

    async def fetch_all(
        self,
        category: str,
        tag_filter: str | dict = None,
        limit: int = None,
        for_update: bool = False,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> EntryList:
        """Perform the action."""
        LOGGER.debug(
            f"fetch_all called with category={category}, "
            f"tag_filter={tag_filter}, limit={limit}, "
            f"for_update={for_update}, order_by={order_by}, "
            f"descending={descending}"
        )
        try:
            entries = await self._db_session.fetch_all(
                category, tag_filter, limit, for_update, order_by, descending
            )
            return EntryList(entries)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            LOGGER.error("fetch_all error: %s", str(e))
            raise self._db_session.translate_error(e)

    async def insert(
        self,
        category: str,
        name: str,
        value: str | bytes = None,
        tags: dict = None,
        expiry_ms: int = None,
        value_json=None,
    ) -> None:
        """Perform the action."""
        LOGGER.debug(
            f"insert called with category={category}, name={name}, "
            f"value={value}, "
            f"tags={tags}, expiry_ms={expiry_ms}, value_json={value_json}"
        )
        try:
            if value is None and value_json is not None:
                value = json.dumps(value_json)
            await self._db_session.insert(category, name, value, tags, expiry_ms)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            LOGGER.error("insert error: %s", str(e))
            raise self._db_session.translate_error(e)

    async def replace(
        self,
        category: str,
        name: str,
        value: str | bytes = None,
        tags: dict = None,
        expiry_ms: int = None,
        value_json=None,
    ) -> None:
        """Perform the action."""
        LOGGER.debug(
            f"replace called with category={category}, name={name}, "
            f"value={value}, "
            f"tags={tags}, expiry_ms={expiry_ms}, value_json={value_json}"
        )
        try:
            if value is None and value_json is not None:
                value = json.dumps(value_json)
            await self._db_session.replace(category, name, value, tags, expiry_ms)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            LOGGER.error("replace error: %s", str(e))
            raise self._db_session.translate_error(e)

    async def remove(self, category: str, name: str) -> None:
        """Perform the action."""
        LOGGER.debug(f"remove called with category={category}, name={name}")
        try:
            await self._db_session.remove(category, name)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            LOGGER.error("remove error: %s", str(e))
            raise self._db_session.translate_error(e)

    async def remove_all(self, category: str, tag_filter: str | dict = None) -> int:
        """Perform the action."""
        LOGGER.debug(
            f"remove_all called with category={category}, tag_filter={tag_filter}"
        )
        try:
            return await self._db_session.remove_all(category, tag_filter)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            LOGGER.error("remove_all error: %s", str(e))
            raise self._db_session.translate_error(e)

    async def commit(self) -> None:
        """Perform the action."""
        LOGGER.debug("commit called")
        if not self._is_txn:
            raise DBStoreError(DBStoreErrorCode.WRAPPER, "Session is not a transaction")
        try:
            await self._db_session.commit()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            LOGGER.error("commit error: %s", str(e))
            raise self._db_session.translate_error(e)

    async def rollback(self) -> None:
        """Perform the action."""
        LOGGER.debug("rollback called")
        if not self._is_txn:
            raise DBStoreError(DBStoreErrorCode.WRAPPER, "Session is not a transaction")
        try:
            await self._db_session.rollback()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            LOGGER.error("rollback error: %s", str(e))
            raise self._db_session.translate_error(e)

    async def close(self) -> None:
        """Perform the action."""
        LOGGER.debug("close called")
        try:
            await self._db_session.close()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            LOGGER.error("close error: %s", str(e))
            raise self._db_session.translate_error(e)

    def __repr__(self) -> str:
        """Magic method description."""
        return f"<Session(handle={self.handle}, is_transaction={self._is_txn})>"


class DBOpenSession:
    """Database open session class."""

    def __init__(
        self,
        db: AbstractDatabaseStore,
        profile: Optional[str],
        is_txn: bool,
        release_number: str,
    ):
        """Initialize DBOpenSession."""
        LOGGER.debug(
            f"OpenSession initialized with db={db}, profile={profile}, "
            f"is_txn={is_txn}, release_number={release_number}"
        )
        self._db = db
        self._profile = profile
        self._is_txn = is_txn
        self._release_number = release_number
        self._session: Optional[DBStoreSession] = None

    @property
    def is_transaction(self) -> bool:
        """Perform the action."""
        return self._is_txn

    async def _open(self) -> DBStoreSession:
        """Perform the action."""
        import time

        start = time.perf_counter()
        LOGGER.debug(
            "DBOpenSession._open starting for profile=%s, is_txn=%s",
            self._profile,
            self._is_txn,
        )
        if self._session:
            raise DBStoreError(DBStoreErrorCode.WRAPPER, "Session already opened")
        method = self._db.transaction if self._is_txn else self._db.session
        LOGGER.debug("Calling db.%s...", "transaction" if self._is_txn else "session")
        self._db_session = (
            await method(self._profile)
            if inspect.iscoroutinefunction(method)
            else method(self._profile)
        )
        LOGGER.debug("Got db_session, calling __aenter__...")
        await self._db_session.__aenter__()
        self._session = DBStoreSession(self._db_session, self._is_txn)
        LOGGER.debug(
            "DBOpenSession._open completed in %.3fs for profile=%s",
            time.perf_counter() - start,
            self._profile,
        )
        return self._session

    def __await__(self) -> DBStoreSession:
        """Magic method description."""
        return self._open().__await__()

    async def __aenter__(self) -> DBStoreSession:
        """Magic method description."""
        LOGGER.debug("__aenter__ called")
        self._session = await self._open()
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        """Magic method description."""
        LOGGER.debug(f"__aexit__ called with exc_type={exc_type}, exc={exc}, tb={tb}")
        session = self._session
        self._session = None
        if self._is_txn and exc_type is None:
            await session.commit()
        await session.close()
