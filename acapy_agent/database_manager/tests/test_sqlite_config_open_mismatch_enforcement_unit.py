import pytest

from acapy_agent.database_manager.databases.errors import DatabaseError, DatabaseErrorCode
from acapy_agent.database_manager.databases.sqlite_normalized.config import SqliteConfig


@pytest.mark.asyncio
async def test_sqlite_open_target_release_mismatch(tmp_path):
    db_path = tmp_path / "rel.db"
    cfg = SqliteConfig(uri=f"sqlite://{db_path}", schema_config="normalize")
    pool, profile, path, rel = cfg.provision(
        profile="p", recreate=True, release_number="release_0_1"
    )
    pool.close()

    cfg2 = SqliteConfig(uri=f"sqlite://{db_path}")
    with pytest.raises(DatabaseError) as e:
        cfg2.open(
            profile="p", schema_migration=None, target_schema_release_number="release_0_2"
        )
    assert e.value.code in {
        DatabaseErrorCode.UNSUPPORTED_VERSION,
        DatabaseErrorCode.QUERY_ERROR,
    }
