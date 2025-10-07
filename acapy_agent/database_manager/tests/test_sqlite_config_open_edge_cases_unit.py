import sqlite3

import pytest

from acapy_agent.database_manager.databases.errors import DatabaseError, DatabaseErrorCode
from acapy_agent.database_manager.databases.sqlite_normalized.config import SqliteConfig


@pytest.mark.asyncio
async def test_sqlite_open_missing_default_profile(tmp_path):
    db_path = tmp_path / "nodefault.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE config (name TEXT PRIMARY KEY, value TEXT)")
    cur.execute(
        "INSERT INTO config(name,value) VALUES('schema_release_number','release_0')"
    )
    conn.commit()
    conn.close()

    cfg = SqliteConfig(uri=f"sqlite://{db_path}")
    with pytest.raises(DatabaseError) as e:
        cfg.open(profile="p")
    assert e.value.code in {
        DatabaseErrorCode.DEFAULT_PROFILE_NOT_FOUND,
        DatabaseErrorCode.QUERY_ERROR,
    }
