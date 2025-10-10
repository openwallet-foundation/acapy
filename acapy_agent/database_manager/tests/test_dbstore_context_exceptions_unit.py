import pytest

from acapy_agent.database_manager.dbstore import DBStore
from acapy_agent.database_manager.error import DBStoreError, DBStoreErrorCode
from acapy_agent.database_manager.interfaces import (
    AbstractDatabaseSession,
    AbstractDatabaseStore,
)


class _TxSession(AbstractDatabaseSession):
    def __init__(self, is_txn: bool):
        self._is_txn = is_txn
        self.commit_called = False
        self.close_called = False

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
        self.commit_called = True

    async def rollback(self):
        return None

    async def close(self):
        self.close_called = True

    def translate_error(self, e):
        return e


class _CtxDB2(AbstractDatabaseStore):
    def __init__(self):
        self.last_session = None

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

    def session(self, profile: str = None, release_number: str = "release_0"):
        self.last_session = _TxSession(False)
        return self.last_session

    def transaction(self, profile: str = None, release_number: str = "release_0"):
        self.last_session = _TxSession(True)
        return self.last_session

    async def close(self, remove: bool = False) -> bool:
        return True


@pytest.mark.asyncio
async def test_dbstore_context_commit_and_exception_paths():
    db = _CtxDB2()
    store = DBStore(db, uri="sqlite://:memory:")

    async with store.transaction() as _s:
        pass
    assert db.last_session.commit_called is True
    assert db.last_session.close_called is True

    db2 = _CtxDB2()
    store2 = DBStore(db2, uri="sqlite://:memory:")
    with pytest.raises(RuntimeError):
        async with store2.transaction() as _s:
            raise RuntimeError("boom")
    assert db2.last_session.commit_called is False
    assert db2.last_session.close_called is True


class _CloseFailDB(_CtxDB2):
    async def close(self, remove: bool = False) -> bool:
        raise ValueError("fail close")


@pytest.mark.asyncio
async def test_dbstore_close_error_mapping():
    store = DBStore(_CloseFailDB(), uri="sqlite://:memory:")
    with pytest.raises(DBStoreError) as e:
        await store.close()
    assert e.value.code == DBStoreErrorCode.UNEXPECTED
