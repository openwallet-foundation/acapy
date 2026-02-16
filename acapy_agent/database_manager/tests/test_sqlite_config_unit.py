import os
import tempfile

import pytest

from acapy_agent.database_manager.databases.errors import DatabaseError, DatabaseErrorCode
from acapy_agent.database_manager.databases.sqlite_normalized.config import SqliteConfig


@pytest.mark.asyncio
async def test_sqlite_config_provision_open_remove_generic():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "unit_generic.db")
        cfg = SqliteConfig(uri=f"sqlite://{db_path}", schema_config="generic")
        pool, profile, path, rel = cfg.provision(profile="p1", recreate=True)
        assert profile == "p1" or profile == "default_profile"
        assert path == db_path
        assert rel == "release_0"
        pool2, profile2, path2, rel2 = cfg.open(profile=profile)
        assert profile2 == profile
        assert path2 == path
        assert rel2 == rel
        assert cfg.remove() is True
        assert cfg.remove() is False


@pytest.mark.asyncio
async def test_sqlite_config_open_missing_file_raises():
    cfg = SqliteConfig(uri="sqlite:///does/not/exist.db")
    with pytest.raises(DatabaseError) as e:
        cfg.open(profile="p")
    assert e.value.code in {
        DatabaseErrorCode.DATABASE_NOT_FOUND,
        DatabaseErrorCode.QUERY_ERROR,
    }
