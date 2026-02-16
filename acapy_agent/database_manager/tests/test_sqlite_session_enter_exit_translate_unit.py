import pytest

from acapy_agent.database_manager.databases.errors import DatabaseError, DatabaseErrorCode
from acapy_agent.database_manager.databases.sqlite_normalized.session import SqliteSession
from acapy_agent.database_manager.error import DBStoreError, DBStoreErrorCode


class _Pool:
    def __init__(self, valid=True):
        self.valid = valid

    def get_connection(self, timeout: float = None):
        if not self.valid:
            raise RuntimeError("pool broken")
        return _Conn(valid=self.valid)

    def return_connection(self, conn):
        pass


class _Conn:
    def __init__(self, valid=True):
        self.valid = valid
        self._cursor = _Cursor(valid=valid)
        self._committed = False
        self._rolled = False

    def cursor(self):
        if not self.valid:
            raise RuntimeError("cursor fail")
        return self._cursor

    def execute(self, *_a, **_k):
        return None

    def commit(self):
        self._committed = True

    def rollback(self):
        self._rolled = True


class _Cursor:
    def __init__(self, valid=True):
        self.valid = valid

    def execute(self, sql, *a):
        if "SELECT 1" in sql and not self.valid:
            raise RuntimeError("bad conn")
        return None


class _DB:
    def __init__(self, pool):
        self.pool = pool
        self.active_sessions = []
        self.backend = None


@pytest.mark.asyncio
async def test_enter_exit_commit_and_rollback_paths(monkeypatch):
    db = _DB(_Pool(valid=True))
    sess = SqliteSession(db, profile="p", is_txn=True, release_number="release_0_1")
    sess.profile_id = 1
    s = await sess.__aenter__()
    assert s is sess
    await sess.__aexit__(None, None, None)

    sess2 = SqliteSession(db, profile="p", is_txn=True, release_number="release_0_1")
    sess2.profile_id = 1
    await sess2.__aenter__()
    await sess2.__aexit__(Exception, Exception("boom"), None)


@pytest.mark.asyncio
async def test_enter_invalid_connection_then_retry(monkeypatch):
    calls = {"n": 0}

    class _FlakyPool(_Pool):
        def get_connection(self, timeout: float = None):
            calls["n"] += 1
            if calls["n"] == 1:
                return _Conn(valid=False)
            return _Conn(valid=True)

    db = _DB(_FlakyPool())
    sess = SqliteSession(db, profile="p", is_txn=False, release_number="release_0_1")
    sess.profile_id = 1
    s = await sess.__aenter__()
    assert s is sess
    await sess.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_get_profile_id_paths(monkeypatch):
    class _PoolLocal(_Pool):
        def get_connection(self, timeout: float = None):
            return _Conn()

    class _ConnLocal(_Conn):
        def __init__(self):
            super().__init__()
            self._local_cursor = _CursorLocal()

        def cursor(self):
            return self._local_cursor

    class _CursorLocal:
        def __init__(self):
            self.calls = 0

        def execute(self, *_a, **_k):
            self.calls += 1

        def fetchone(self):
            if self.calls == 1:
                return None
            return (5,)

    db = _DB(_PoolLocal())
    sess = SqliteSession(db, profile="px", is_txn=False, release_number="release_0_1")

    _single_conn = _ConnLocal()

    def get_conn(_: float = None):
        return _single_conn

    db.pool.get_connection = get_conn

    with pytest.raises(DatabaseError) as exc:
        sess._get_profile_id("missing")
    assert exc.value.code in {
        DatabaseErrorCode.PROFILE_NOT_FOUND,
        DatabaseErrorCode.QUERY_ERROR,
    }

    pid = sess._get_profile_id("present")
    assert pid == 5


def test_translate_error_paths():
    db = _DB(_Pool())
    sess = SqliteSession(db, profile="p", is_txn=False, release_number="release_0_1")
    err = sess.translate_error(
        DatabaseError(code=DatabaseErrorCode.QUERY_ERROR, message="m")
    )
    assert isinstance(err, DBStoreError)
    assert err.code == DBStoreErrorCode.UNEXPECTED
    dup = sess.translate_error(Exception("UNIQUE constraint failed: items"))
    assert dup.code == DBStoreErrorCode.DUPLICATE
    locked = sess.translate_error(Exception("database is locked"))
    assert locked.code == DBStoreErrorCode.UNEXPECTED
    other = sess.translate_error(Exception("x"))
    assert other.code == DBStoreErrorCode.UNEXPECTED
