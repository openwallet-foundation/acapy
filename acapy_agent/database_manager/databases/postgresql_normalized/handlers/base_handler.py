"""Module docstring."""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, List, Optional, Sequence, Tuple

from psycopg import AsyncCursor

from acapy_agent.database_manager.db_types import Entry
from acapy_agent.database_manager.wql_normalized.tags import TagQuery


class BaseHandler(ABC):
    """Abstract base class for handlers managing CRUD operations.

    Handles CRUD and query operations for a specific category.
    """

    def __init__(self, category: str):
        """Initialize the handler with a specific category."""
        self.category = category

    @abstractmethod
    async def insert(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        name: str,
        value: str | bytes,
        tags: dict,
        expiry_ms: int,
    ) -> None:
        """Insert a new entry into the database."""
        pass

    @abstractmethod
    async def replace(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        name: str,
        value: str | bytes,
        tags: dict,
        expiry_ms: int,
    ) -> None:
        """Replace an existing entry in the database."""
        pass

    @abstractmethod
    async def fetch(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        name: str,
        tag_filter: str | dict,
        for_update: bool,
    ) -> Optional[Entry]:
        """Fetch a single entry by its name."""
        pass

    @abstractmethod
    async def fetch_all(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        tag_filter: str | dict,
        limit: int,
        for_update: bool,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> Sequence[Entry]:
        """Fetch all entries matching the specified criteria."""
        pass

    @abstractmethod
    async def count(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        tag_filter: str | dict,
    ) -> int:
        """Count the number of entries matching the specified criteria."""
        pass

    @abstractmethod
    async def remove(
        self, cursor: AsyncCursor, profile_id: int, category: str, name: str
    ) -> None:
        """Remove an entry identified by its name."""
        pass

    @abstractmethod
    async def remove_all(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        tag_filter: str | dict,
    ) -> int:
        """Remove all entries matching the specified criteria."""
        pass

    @abstractmethod
    async def scan(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        tag_query: Optional[TagQuery],
        offset: int,
        limit: int,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> AsyncGenerator[Entry, None]:
        """Scan the database for entries matching the criteria."""
        pass

    @abstractmethod
    async def scan_keyset(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        tag_query: Optional[TagQuery],
        last_id: Optional[int],
        limit: int,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> AsyncGenerator[Entry, None]:
        """Scan the database using keyset pagination."""
        pass

    @abstractmethod
    def get_sql_clause(self, tag_query: TagQuery) -> Tuple[str, List[Any]]:
        """Translate a TagQuery into an SQL clause and corresponding parameters."""
        pass
