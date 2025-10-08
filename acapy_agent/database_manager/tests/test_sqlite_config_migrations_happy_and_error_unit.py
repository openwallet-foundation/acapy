import types

import pytest

from acapy_agent.database_manager.databases.errors import DatabaseError, DatabaseErrorCode
from acapy_agent.database_manager.databases.sqlite_normalized.config import SqliteConfig


class _FakeConn:
    def __init__(self):
        self.executed = []

    def cursor(self):
        return self

    def execute(self, sql):
        self.executed.append(sql)


@pytest.mark.asyncio
async def test_apply_migrations_success_and_missing(monkeypatch):
    cfg = SqliteConfig(schema_config="normalize")
    conn = _FakeConn()

    def fake_import(name):
        if "release_0_to_0_1" in name:
            mod = types.SimpleNamespace()

            def migrate_sqlite(c):
                c.execute("-- migrated")

            mod.migrate_sqlite = migrate_sqlite
            return mod
        elif "release_0_1_to_0_2" in name:
            raise ImportError("no module")
        raise AssertionError(f"unexpected import {name}")

    monkeypatch.setattr(
        "acapy_agent.database_manager.databases.sqlite_normalized.config.importlib.import_module",
        fake_import,
    )

    # Should not raise
    cfg._apply_migrations(conn, "release_0", "release_0_2", db_type="sqlite")
    assert "-- migrated" in "\n".join(conn.executed)


@pytest.mark.asyncio
async def test_apply_migrations_missing_migrate_func_warns(monkeypatch):
    cfg = SqliteConfig(schema_config="normalize")
    conn = _FakeConn()

    def fake_import(name):
        if "release_0_to_0_1" in name:
            return types.SimpleNamespace()
        raise ImportError("no module")

    monkeypatch.setattr(
        "acapy_agent.database_manager.databases.sqlite_normalized.config.importlib.import_module",
        fake_import,
    )

    # Should complete without raising
    cfg._apply_migrations(conn, "release_0", "release_0_1", db_type="sqlite")


@pytest.mark.asyncio
async def test_apply_migrations_raise_wrapped(monkeypatch):
    cfg = SqliteConfig(schema_config="normalize")
    conn = _FakeConn()

    def fake_import(name):
        if "release_0_to_0_1" in name:
            mod = types.SimpleNamespace()

            def migrate_sqlite(c):
                raise RuntimeError("boom")

            mod.migrate_sqlite = migrate_sqlite
            return mod
        raise AssertionError

    monkeypatch.setattr(
        "acapy_agent.database_manager.databases.sqlite_normalized.config.importlib.import_module",
        fake_import,
    )

    with pytest.raises(DatabaseError) as exc:
        cfg._apply_migrations(conn, "release_0", "release_0_1", db_type="sqlite")
    assert exc.value.code == DatabaseErrorCode.PROVISION_ERROR


def test_open_missing_db_file_raises_not_found(tmp_path):
    cfg = SqliteConfig(uri=f"sqlite://{tmp_path}/does_not_exist.db")
    with pytest.raises(DatabaseError) as exc:
        cfg.open()
    assert exc.value.code == DatabaseErrorCode.DATABASE_NOT_FOUND


def test_open_connection_pool_failure(monkeypatch, tmp_path):
    db_path = tmp_path / "db.sqlite"
    db_path.write_text("")
    cfg = SqliteConfig(uri=f"sqlite://{db_path}")

    class Boom(Exception):
        pass

    class _BadPool:
        def __init__(self, *a, **k):
            raise Boom("pool fail")

    monkeypatch.setattr(
        "acapy_agent.database_manager.databases.sqlite_normalized.config.ConnectionPool",
        _BadPool,
    )

    with pytest.raises(DatabaseError) as exc:
        cfg.open()
    assert exc.value.code == DatabaseErrorCode.CONNECTION_ERROR


def test_provision_connection_pool_failure(monkeypatch, tmp_path):
    cfg = SqliteConfig(uri=f"sqlite://{tmp_path}/prov.db")

    class _BadPool:
        def __init__(self, *a, **k):
            raise RuntimeError("pool boom")

    monkeypatch.setattr(
        "acapy_agent.database_manager.databases.sqlite_normalized.config.ConnectionPool",
        _BadPool,
    )

    with pytest.raises(DatabaseError) as exc:
        cfg.provision()
    assert exc.value.code == DatabaseErrorCode.CONNECTION_ERROR


def test_remove_general_exception_wrapped(monkeypatch, tmp_path):
    db_path = tmp_path / "to_remove.db"
    db_path.write_text("")
    cfg = SqliteConfig(uri=f"sqlite://{db_path}")

    def bad_remove(path):
        raise RuntimeError("rm boom")

    monkeypatch.setattr(
        "acapy_agent.database_manager.databases.sqlite_normalized.config.os.remove",
        bad_remove,
    )

    with pytest.raises(DatabaseError) as exc:
        cfg.remove()
    assert exc.value.code == DatabaseErrorCode.CONNECTION_ERROR
