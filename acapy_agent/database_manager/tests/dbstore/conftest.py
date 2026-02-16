"""Pytest configuration for database manager tests.

These DBStore tests are skipped by default in the unit-test CI run to avoid
environment coupling. Set ENABLE_DBSTORE_TESTS=1 to run them locally.
"""

import os
import tempfile
from pathlib import Path

import pytest

# Skip entire directory unless explicitly enabled
if not os.getenv("ENABLE_DBSTORE_TESTS"):
    pytest.skip(
        "DBStore tests disabled by default; set ENABLE_DBSTORE_TESTS=1 to enable",
        allow_module_level=True,
    )

os.environ["SQLITE_KEEPALIVE_INTERVAL"] = "60"
os.environ["SQLITE_CLOSE_TIMEOUT"] = "0.5"


@pytest.fixture(scope="session")
def test_temp_dir():
    """Create a session-scoped temporary directory for all tests."""
    tmpdir = tempfile.mkdtemp(prefix="acapy_test_")
    yield tmpdir
    import shutil

    try:
        shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception:
        pass


@pytest.fixture(scope="function")
def fast_db_path(test_temp_dir):
    """Create a function-scoped database path."""
    import uuid

    db_name = f"test_{uuid.uuid4().hex[:8]}.db"
    db_path = Path(test_temp_dir) / db_name
    yield str(db_path)
    # Cleanup
    try:
        if db_path.exists():
            db_path.unlink()
    except Exception:
        pass


@pytest.fixture
async def fast_store(fast_db_path):
    """Create a fast non-encrypted database store for testing."""
    from acapy_agent.database_manager.dbstore import DBStore

    uri = f"sqlite://{fast_db_path}"
    store = await DBStore.provision(
        uri=uri,
        pass_key=None,  # No encryption for speed
        profile="test_profile",
        recreate=True,
        release_number="release_0_1",
        schema_config="normalize",
    )
    yield store
    await store.close()


@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    """Configure logging for tests."""
    import logging

    # Reduce logging verbosity for tests
    logging.getLogger("acapy_agent.database_manager").setLevel(logging.WARNING)
    logging.getLogger("sqlcipher3").setLevel(logging.WARNING)
    logging.getLogger("sqlite3").setLevel(logging.WARNING)
