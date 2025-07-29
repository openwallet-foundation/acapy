from abc import ABC, abstractmethod
from typing import Optional, Sequence, Union, Generator

from .db_types import Entry

class DatabaseBackend(ABC):
    """Abstract base class for database backends."""
    @abstractmethod
    def provision(self, uri, key_method, pass_key, profile, recreate, release_number: str = "release_1"):
        """Provision a new database with the specified release number.

        Args:
            uri: The database URI.
            key_method: Optional key method for encryption.
            pass_key: Optional encryption key.
            profile: Optional profile name.
            recreate: If True, recreate the database.
            release_number: Release number to use (e.g., 'release_1'). Defaults to 'release_1'.
        """
        pass

    @abstractmethod
    def open(self, uri, key_method, pass_key, profile, release_number: str = "release_1"):
        """Open an existing database with the specified release number.

        Args:
            uri: The database URI.
            key_method: Optional key method for encryption.
            pass_key: Optional encryption key.
            profile: Optional profile name.
            release_number: Release number to use (e.g., 'release_1'). Defaults to 'release_1'.
        """
        pass

    @abstractmethod
    def remove(self, uri, release_number: str = "release_1"):
        """Remove the database.

        Args:
            uri: The database URI.
            release_number: Release number to use (e.g., 'release_1'). Defaults to 'release_1'.
        """
        pass

    @abstractmethod
    def translate_error(self, exception):
        """Translate backend-specific exceptions to DBStoreError."""
        pass

class AbstractDatabaseStore(ABC):
    """Abstract base class for database store implementations."""
    @abstractmethod
    async def create_profile(self, name: str = None) -> str:
        pass

    @abstractmethod
    async def get_profile_name(self) -> str:
        pass

    @abstractmethod
    async def remove_profile(self, name: str) -> bool:
        pass

    @abstractmethod
    async def rekey(self, key_method: str = None, pass_key: str = None):
        pass

    @abstractmethod
    def scan(self, profile: Optional[str], category: str, tag_filter: Union[str, dict] = None, 
             offset: int = None, limit: int = None) -> Generator[Entry, None, None]:
        pass

    @abstractmethod
    def session(self, profile: str = None, release_number: str = "release_1") -> 'AbstractDatabaseSession':
        """Create a new database session with the specified release number.

        Args:
            profile: Optional profile name.
            release_number: Release number to use (e.g., 'release_1'). Defaults to 'release_1'.

        Returns:
            AbstractDatabaseSession: The session instance.
        """
        pass

    @abstractmethod
    def transaction(self, profile: str = None, release_number: str = "release_1") -> 'AbstractDatabaseSession':
        """Create a new database transaction with the specified release number.

        Args:
            profile: Optional profile name.
            release_number: Release number to use (e.g., 'release_1'). Defaults to 'release_1'.

        Returns:
            AbstractDatabaseSession: The transaction instance.
        """
        pass

    @abstractmethod
    async def close(self, remove: bool = False) -> bool:
        pass

class AbstractDatabaseSession(ABC):
    """Abstract base class for database session implementations."""
    @abstractmethod
    async def count(self, category: str, tag_filter: Union[str, dict] = None) -> int:
        pass

    @abstractmethod
    async def fetch(self, category: str, name: str, for_update: bool = False) -> Optional[Entry]:
        pass

    @abstractmethod
    async def fetch_all(self, category: str, tag_filter: Union[str, dict] = None, 
                        limit: int = None, for_update: bool = False) -> Sequence[Entry]:
        pass

    @abstractmethod
    async def insert(self, category: str, name: str, value: Union[str, bytes] = None, 
                     tags: dict = None, expiry_ms: int = None, value_json=None):
        pass

    @abstractmethod
    async def replace(self, category: str, name: str, value: Union[str, bytes] = None, 
                      tags: dict = None, expiry_ms: int = None, value_json=None):
        pass

    @abstractmethod
    async def remove(self, category: str, name: str):
        pass

    @abstractmethod
    async def remove_all(self, category: str, tag_filter: Union[str, dict] = None) -> int:
        pass

    @abstractmethod
    async def commit(self):
        pass

    @abstractmethod
    async def rollback(self):
        pass

    @abstractmethod
    async def close(self):
        pass