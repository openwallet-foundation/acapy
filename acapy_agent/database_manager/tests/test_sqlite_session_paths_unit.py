import pytest

from acapy_agent.database_manager.databases.errors import DatabaseError, DatabaseErrorCode
from acapy_agent.database_manager.databases.sqlite_normalized.session import SqliteSession
from acapy_agent.database_manager.error import DBStoreError, DBStoreErrorCode


class _FakePool:
    def get_connection(self, timeout: float = None):
        return _FakeConn()

    def return_connection(self, conn):
        pass


class _FakeConn:
    def __init__(self):
        self._cursor = _FakeCursor()

    def cursor(self):
        return self._cursor

    def commit(self):
        return None

    def rollback(self):
        return None

    def execute(self, *_args, **_kwargs):
        return None


class _FakeDb:
    def __init__(self):
        self.pool = _FakePool()
        self.active_sessions = []
        self.backend = None


class _HandlerRaising:
    def count(self, *args, **kwargs):
        raise RuntimeError("boom count")

    def insert(self, *args, **kwargs):
        raise RuntimeError("boom insert")

    def replace(self, *args, **kwargs):
        raise RuntimeError("boom replace")

    def remove(self, *args, **kwargs):
        raise RuntimeError("boom remove")

    def remove_all(self, *args, **kwargs):
        raise RuntimeError("boom remove_all")


class _FakeCursor:
    def execute(self, *_args, **_kwargs):
        return None


@pytest.mark.asyncio
async def test_sqlite_session_op_error_paths(monkeypatch):
    from acapy_agent.database_manager import category_registry as cr

    def _fake_get_release(release_number: str, db_type: str):
        return ({"default": _HandlerRaising(), "people": _HandlerRaising()}, {}, {})

    monkeypatch.setattr(cr, "get_release", _fake_get_release)

    sess = SqliteSession(
        _FakeDb(), profile="p", is_txn=False, release_number="release_0_1"
    )
    sess.conn = _FakeConn()
    sess.profile_id = 1

    for op in (
        lambda: sess.count("people"),
        lambda: sess.fetch("people", "n1"),
        lambda: sess.fetch_all("people"),
        lambda: sess.insert("people", "n1", value="{}"),
        lambda: sess.replace("people", "n1", value="{}"),
        lambda: sess.remove("people", "n1"),
        lambda: sess.remove_all("people"),
    ):
        with pytest.raises(DatabaseError) as e:
            await op()
        assert e.value.code in {
            DatabaseErrorCode.QUERY_ERROR,
            DatabaseErrorCode.PROFILE_NOT_FOUND,
        }


@pytest.mark.asyncio
async def test_sqlite_session_commit_rollback_guards():
    sess = SqliteSession(
        _FakeDb(), profile="p", is_txn=False, release_number="release_0_1"
    )
    with pytest.raises(DBStoreError) as e:
        await sess.commit()
    assert e.value.code == DBStoreErrorCode.WRAPPER
    with pytest.raises(DBStoreError) as e2:
        await sess.rollback()
    assert e2.value.code == DBStoreErrorCode.WRAPPER
