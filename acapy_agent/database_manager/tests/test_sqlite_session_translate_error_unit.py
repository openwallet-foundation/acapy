import pytest

from acapy_agent.database_manager.databases.errors import DatabaseError
from acapy_agent.database_manager.databases.sqlite_normalized.session import SqliteSession
from acapy_agent.database_manager.error import DBStoreErrorCode


class _FakePool:
    def get_connection(self, **kwargs):
        return object()

    def return_connection(self, conn):
        pass


class _FakeDb:
    def __init__(self, backend=None):
        self.pool = _FakePool()
        self.active_sessions = []
        self.backend = backend


@pytest.mark.asyncio
async def test_translate_error_mapping_and_fallbacks():
    sess = SqliteSession(
        _FakeDb(backend=None), profile="p", is_txn=False, release_number="release_0"
    )
    err = sess.translate_error(DatabaseError(code=None, message="x"))
    assert getattr(err, "code", None) == DBStoreErrorCode.UNEXPECTED

    err = sess.translate_error(Exception("UNIQUE constraint failed: items.name"))
    assert err.code == DBStoreErrorCode.DUPLICATE

    err = sess.translate_error(Exception("database is locked"))
    assert err.code == DBStoreErrorCode.UNEXPECTED

    err = sess.translate_error(Exception("other"))
    assert err.code == DBStoreErrorCode.UNEXPECTED
