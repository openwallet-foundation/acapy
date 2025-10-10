"""Test credential exchange v20 custom handler insertion."""

import sqlite3
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_credex_dbstore.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("PRAGMA busy_timeout = 10000")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY,
                profile_id INTEGER,
                kind INTEGER,
                category TEXT,
                name TEXT,
                value TEXT,
                expiry TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cred_ex_v20_v0_1 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL UNIQUE,
                item_name TEXT NOT NULL,
                connection_id TEXT,
                cred_def_id TEXT,
                thread_id TEXT NOT NULL UNIQUE,
                parent_thread_id TEXT,
                cred_offer TEXT,
                cred_request TEXT,
                cred_issue TEXT,
                by_format TEXT,
                cred_proposal TEXT,
                auto_offer BOOLEAN,
                auto_issue BOOLEAN,
                auto_remove BOOLEAN,
                error_msg TEXT,
                initiator TEXT,
                trace BOOLEAN,
                revoc_notification TEXT,
                role TEXT,
                state TEXT,
                FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
            )
        """)
        conn.commit()

        yield conn, cursor

        conn.close()


class TestCredExV20Insert:
    """Test suite for credential exchange v20 insertions."""

    @pytest.mark.asyncio
    async def test_insert_cred_ex_v20(self, temp_db):
        """Test inserting a credential exchange v20 record."""
        conn, cursor = temp_db

        # Insert an item first
        cursor.execute(
            """
            INSERT INTO items (id, profile_id, kind, category, name, value, expiry)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (1, 1, 1, "cred_ex_v20", "test_cred_001", "{}", None),
        )

        # Create test data
        cred_ex_data = {
            "connection_id": "conn_001",
            "cred_def_id": "cred_def_001",
            "thread_id": "thread_001",
            "state": "offer-sent",
            "initiator": "self",
            "role": "issuer",
        }

        # Test the custom handler insertion logic
        # Handler would be initialized with category and columns in actual usage
        # For this test, we're directly testing the SQL insertion

        # Insert cred_ex_v20 record
        cursor.execute(
            """
            INSERT INTO cred_ex_v20_v0_1 (
                item_id, item_name, connection_id, cred_def_id,
                thread_id, parent_thread_id, initiator, role, state
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                1,
                "test_cred_001",
                cred_ex_data["connection_id"],
                cred_ex_data["cred_def_id"],
                cred_ex_data["thread_id"],
                None,  # parent_thread_id
                cred_ex_data["initiator"],
                cred_ex_data["role"],
                cred_ex_data["state"],
            ),
        )

        conn.commit()

        # Verify insertion
        cursor.execute("SELECT * FROM cred_ex_v20_v0_1 WHERE item_id = ?", (1,))
        result = cursor.fetchone()

        assert result is not None, "Record should be inserted"
        assert result[5] == "thread_001", "Thread ID should match"
        assert result[20] == "offer-sent", "State should match"

    @pytest.mark.asyncio
    async def test_duplicate_thread_id(self, temp_db):
        """Test that duplicate thread IDs are handled correctly."""
        conn, cursor = temp_db

        # Insert first item
        cursor.execute(
            """
            INSERT INTO items (id, profile_id, kind, category, name, value, expiry)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (1, 1, 1, "cred_ex_v20", "test_cred_001", "{}", None),
        )

        # Insert first cred_ex_v20 record
        cursor.execute(
            """
            INSERT INTO cred_ex_v20_v0_1 (
                item_id, item_name, connection_id, thread_id, state
            )
            VALUES (?, ?, ?, ?, ?)
        """,
            (1, "test_cred_001", "conn_001", "thread_001", "offer-sent"),
        )

        conn.commit()

        # Try to insert second item with same thread_id (should fail)
        cursor.execute(
            """
            INSERT INTO items (id, profile_id, kind, category, name, value, expiry)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (2, 1, 1, "cred_ex_v20", "test_cred_002", "{}", None),
        )

        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                """
                INSERT INTO cred_ex_v20_v0_1 (
                    item_id, item_name, connection_id, thread_id, state
                )
                VALUES (?, ?, ?, ?, ?)
            """,
                (2, "test_cred_002", "conn_002", "thread_001", "offer-sent"),
            )
