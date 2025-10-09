"""Module docstring."""

import sqlite3
from abc import ABC, abstractmethod
from typing import Any, Generator, List, Optional, Sequence, Tuple

from ....db_types import Entry  # Assuming Entry is defined in a types module
from ....wql_normalized.tags import (
    TagQuery,
)  # Assuming TagQuery is defined in a tags module


class BaseHandler(ABC):
    """Abstract base class for handlers managing CRUD/query operations for a category."""

    def __init__(self, category: str):
        """Initialize the handler with a specific category."""
        self.category = category

    @abstractmethod
    def insert(
        self,
        cursor: sqlite3.Cursor,
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
    def replace(
        self,
        cursor: sqlite3.Cursor,
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
    def fetch(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        name: str,
        tag_filter: str | dict,
        for_update: bool,
    ) -> Optional[Entry]:
        """Fetch a single entry by its name."""
        pass

    @abstractmethod
    def fetch_all(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        tag_filter: str | dict,
        limit: int,
        for_update: bool,
    ) -> Sequence[Entry]:
        """Fetch all entries matching the specified criteria."""
        pass

    @abstractmethod
    def count(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        tag_filter: str | dict,
    ) -> int:
        """Count the number of entries matching the specified criteria."""
        pass

    @abstractmethod
    def remove(
        self, cursor: sqlite3.Cursor, profile_id: int, category: str, name: str
    ) -> None:
        """Remove an entry identified by its name."""
        pass

    @abstractmethod
    def remove_all(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        tag_filter: str | dict,
    ) -> int:
        """Remove all entries matching the specified criteria."""
        pass

    @abstractmethod
    def scan(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        tag_query: Optional[TagQuery],
        offset: int,
        limit: int,
    ) -> Generator[Entry, None, None]:
        """Scan the database for entries matching the criteria."""
        pass

    @abstractmethod
    def get_sql_clause(self, tag_query: TagQuery) -> Tuple[str, List[Any]]:
        """Translate a TagQuery into an SQL clause and corresponding parameters."""
        pass
