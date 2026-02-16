import pytest

from acapy_agent.database_manager.dbstore import DBStore
from acapy_agent.database_manager.interfaces import (
    AbstractDatabaseSession,
    AbstractDatabaseStore,
)


class _CtxDB(AbstractDatabaseStore):
    def __init__(self):
        self._sess = _CtxSession()

    async def create_profile(self, name: str = None) -> str:
        return name or "p"

    async def get_profile_name(self) -> str:
        return "p"

    async def remove_profile(self, name: str) -> bool:
        return True

    async def rekey(self, key_method: str = None, pass_key: str = None):
        return None

    def scan(self, *args, **kwargs):
        return iter([])

    def scan_keyset(self, *args, **kwargs):
        return iter([])

    def session(self, profile: str = None, release_number: str = "release_0"):
        s = _CtxSession()
        s._is_txn = False
        return s

    def transaction(self, profile: str = None, release_number: str = "release_0"):
        s = _CtxSession()
        s._is_txn = True
        return s

    async def close(self, remove: bool = False) -> bool:
        return True


class _CtxSession(AbstractDatabaseSession):
    def __init__(self):
        self._is_txn = False
        self._closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def count(self, category: str, tag_filter: str | dict = None) -> int:
        return 0

    async def fetch(self, category: str, name: str, for_update: bool = False):
        return None

    async def fetch_all(self, *args, **kwargs):
        return []

    async def insert(self, *args, **kwargs):
        return None

    async def replace(self, *args, **kwargs):
        return None

    async def remove(self, *args, **kwargs):
        return None

    async def remove_all(self, *args, **kwargs) -> int:
        return 0

    async def commit(self):
        return None

    async def rollback(self):
        return None

    async def close(self):
        self._closed = True
        return None

    def translate_error(self, e):
        return e


@pytest.mark.asyncio
async def test_dbstore_async_context_manager_opens_and_closes():
    store = DBStore(_CtxDB(), uri="sqlite://:memory:")
    async with store as session:
        assert session.is_transaction is False
    # ensure the previous opener was cleared
    assert store._opener is None
