import pytest

from acapy_agent.database_manager.databases.errors import DatabaseError, DatabaseErrorCode
from acapy_agent.database_manager.databases.sqlite_normalized.config import SqliteConfig


@pytest.mark.asyncio
async def test_sqlite_config_apply_migrations_invalid_path(monkeypatch, tmp_path):
    db_path = tmp_path / "mig.db"
    cfg = SqliteConfig(uri=f"sqlite://{db_path}", schema_config="normalize")
    pool, profile, path, rel = cfg.provision(
        profile="p", recreate=True, release_number="release_0_1"
    )
    conn = pool.get_connection()

    from acapy_agent.database_manager.databases.sqlite_normalized import config as cfg_mod

    monkeypatch.setattr(cfg_mod, "RELEASE_ORDER", ["release_0_1"])

    with pytest.raises(DatabaseError) as e:
        cfg._apply_migrations(
            conn, current_release="release_0_1", target_release="release_0_2"
        )
    assert e.value.code == DatabaseErrorCode.UNSUPPORTED_VERSION

    pool.return_connection(conn)
