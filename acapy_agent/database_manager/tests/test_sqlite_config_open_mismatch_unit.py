import pytest

from acapy_agent.database_manager.databases.errors import DatabaseError, DatabaseErrorCode
from acapy_agent.database_manager.databases.sqlite_normalized.config import SqliteConfig


@pytest.mark.asyncio
async def test_sqlite_config_open_generic_mismatch(tmp_path):
    db_path = tmp_path / "mismatch.db"
    cfg = SqliteConfig(uri=f"sqlite://{db_path}", schema_config="normalize")
    pool, profile, path, rel = cfg.provision(
        profile="p", recreate=True, release_number="release_0_1"
    )
    pool.close()

    cfg2 = SqliteConfig(uri=f"sqlite://{db_path}", schema_config="generic")
    pool2, profile2, path2, rel2 = cfg2.open(profile="p")
    assert profile2 == "p"
    assert rel2 == "release_0_1"


@pytest.mark.asyncio
async def test_sqlite_config_open_profile_missing(tmp_path):
    db_path = tmp_path / "profile.db"
    cfg = SqliteConfig(uri=f"sqlite://{db_path}", schema_config="generic")
    pool, profile, path, rel = cfg.provision(
        profile="p", recreate=True, release_number="release_0"
    )
    pool.close()
    with pytest.raises(DatabaseError) as e:
        cfg.open(profile="other")
    assert e.value.code in {
        DatabaseErrorCode.PROFILE_NOT_FOUND,
        DatabaseErrorCode.QUERY_ERROR,
    }
