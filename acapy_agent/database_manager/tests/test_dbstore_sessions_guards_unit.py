import pytest

from acapy_agent.database_manager.dbstore import DBStore
from acapy_agent.database_manager.interfaces import (
    AbstractDatabaseSession,
    AbstractDatabaseStore,
)


class _GuardSession(AbstractDatabaseSession):
    def __init__(self, is_txn: bool):
        self._is_txn = is_txn

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def count(self, *args, **kwargs):
        return 0

    async def fetch(self, *args, **kwargs):
        return None

    async def fetch_all(self, *args, **kwargs):
        return []

    async def insert(self, *args, **kwargs):
        return None

    async def replace(self, *args, **kwargs):
        return None

    async def remove(self, *args, **kwargs):
        return None

    async def remove_all(self, *args, **kwargs):
        return 0

    async def commit(self):
        return None

    async def rollback(self):
        return None

    async def close(self):
        return None

    def translate_error(self, e):
        return e


class _GuardDB(AbstractDatabaseStore):
    def session(self, profile: str = None, release_number: str = "release_0"):
        return _GuardSession(False)

    def transaction(self, profile: str = None, release_number: str = "release_0"):
        return _GuardSession(True)

    async def create_profile(self, name: str = None) -> str:
        return name or "p"

    async def get_profile_name(self) -> str:
        return "p"

    async def remove_profile(self, name: str) -> bool:
        return True

    async def rekey(self, key_method: str = None, pass_key: str = None):
        return None

    def scan(self, *args, **kwargs):
        return iter(())

    def scan_keyset(self, *args, **kwargs):
        return iter(())

    async def close(self, remove: bool = False) -> bool:
        return True


@pytest.mark.asyncio
async def test_dbstore_session_commit_rollback_guards():
    store = DBStore(_GuardDB(), uri="sqlite://:memory:")
    # Commit/rollback should raise guard errors when not transaction
    async with store.session() as session:
        with pytest.raises(Exception) as e:
            await session.commit()
        assert "Session is not a transaction" in str(e.value)
        with pytest.raises(Exception) as e2:
            await session.rollback()
        assert "Session is not a transaction" in str(e2.value)
