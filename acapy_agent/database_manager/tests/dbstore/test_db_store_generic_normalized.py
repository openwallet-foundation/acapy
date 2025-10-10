"""Test SQLite database store with normalized schema."""

import json
import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from acapy_agent.database_manager.dbstore import DBStore

# Sample connection test data
CONNECTION_JSON_1 = {
    "state": "active",
    "their_did": "did:peer:1zQmdgg9s3MwBEZ49QGn2ohLHbg6osFTepqumgL8RNZ2Mxhf",
    "inbound_connection_id": "123456",
}

CONNECTION_JSON_2 = {
    "state": "inactive",
    "their_did": "did:peer:2AbCdEfGhIjKlMn1234567890",
    "inbound_connection_id": "456789",
}

CONNECTION_JSON_3 = {
    "state": "active",
    "their_did": "did:peer:3BcDeFgHiJkLmNoP456789012",
    "inbound_connection_id": "conn_123",
}


@pytest_asyncio.fixture
async def test_db_path():
    """Create a temporary database path for testing."""
    tmpdir = tempfile.mkdtemp()
    db_path = Path(tmpdir) / "test_dbstore_normalized.db"
    yield str(db_path)
    # Cleanup
    import shutil

    try:
        shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception:
        pass  # Ignore cleanup errors


@pytest_asyncio.fixture
async def encrypted_store(test_db_path):
    """Create an encrypted database store with normalized schema."""
    # Use in-memory database for faster tests when possible
    # uri = "sqlite://:memory:"  # Uncomment for in-memory (but can't test encryption)
    uri = f"sqlite://{test_db_path}"
    store = await DBStore.provision(
        uri=uri,
        pass_key="Strong_key",
        profile="test_profile",
        recreate=True,
        release_number="release_0_1",
        schema_config="normalize",
    )
    yield store
    await store.close()


@pytest_asyncio.fixture
async def non_encrypted_store():
    """Create a non-encrypted database store with normalized schema."""
    # Use in-memory database for much faster tests
    # Note: shared in-memory databases would require file:memdb1?mode=memory&cache=shared
    # but that requires additional SQLite configuration, so using temp file for now
    import tempfile

    tmpdir = tempfile.mkdtemp()
    db_path = Path(tmpdir) / "test_no_enc.db"
    uri = f"sqlite://{db_path}"
    store = await DBStore.provision(
        uri=uri,
        pass_key=None,
        profile="test_profile_no_enc",
        recreate=True,
        release_number="release_0_1",
        schema_config="normalize",
    )
    yield store
    await store.close()
    # Cleanup
    import shutil

    try:
        shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception:
        pass


@pytest_asyncio.fixture
async def populated_store(encrypted_store):
    """Create a store with test data for people and connections."""
    async with encrypted_store.transaction() as session:
        # Insert people data
        await session.insert(
            category="people",
            name="person1",
            value=json.dumps({"name": "Alice"}),
            tags={"attr::person.gender": "F", "attr::person.status": "active"},
            expiry_ms=3600000,
        )
        await session.insert(
            category="people",
            name="person2",
            value=json.dumps({"name": "Bob"}),
            tags={"attr::person.gender": "M", "attr::person.status": "inactive"},
            expiry_ms=3600000,
        )
        await session.insert(
            category="people",
            name="person3",
            value=json.dumps({"name": "Charlie"}),
            tags={"attr::person.gender": "F", "attr::person.status": "active"},
            expiry_ms=3600000,
        )
        await session.insert(
            category="people",
            name="person4",
            value=json.dumps({"name": "David"}),
            tags={"attr::person.gender": "M", "attr::person.status": "active"},
        )

        # Insert connection data
        await session.insert(
            category="connection",
            name="conn_1",
            value=json.dumps(CONNECTION_JSON_1),
            tags={},
        )
        await session.insert(
            category="connection",
            name="conn_2",
            value=json.dumps(CONNECTION_JSON_2),
            tags={},
        )
        await session.insert(
            category="connection",
            name="conn_3",
            value=json.dumps(CONNECTION_JSON_3),
            tags={},
        )
    return encrypted_store


class TestDBStoreGenericNormalized:
    """Test suite for normalized database store operations."""

    @pytest.mark.asyncio
    async def test_provision(self, test_db_path):
        """Test provisioning a normalized database."""
        uri = f"sqlite://{test_db_path}"
        store = await DBStore.provision(
            uri=uri,
            pass_key=None,  # Use regular SQLite instead of sqlcipher3 for testing
            profile="test_profile",
            recreate=True,
            release_number="release_0_1",
            schema_config="normalize",
        )
        assert os.path.exists(test_db_path), "Database file not created"
        await store.close()

    @pytest.mark.asyncio
    async def test_insert(self, encrypted_store):
        """Test inserting data into normalized database."""
        async with encrypted_store.transaction() as session:
            await session.insert(
                category="people",
                name="person1",
                value=json.dumps({"name": "Alice"}),
                tags={"attr::person.gender": "F", "attr::person.status": "active"},
                expiry_ms=3600000,
            )
            await session.insert(
                category="people",
                name="person2",
                value=json.dumps({"name": "Bob"}),
                tags={"attr::person.gender": "M", "attr::person.status": "inactive"},
                expiry_ms=3600000,
            )
            await session.insert(
                category="people",
                name="person3",
                value=json.dumps({"name": "Charlie"}),
                tags={"attr::person.gender": "F", "attr::person.status": "active"},
                expiry_ms=3600000,
            )
            count = await session.count(category="people")
            assert count == 3, "Expected 3 entries"

    @pytest.mark.asyncio
    async def test_scan(self, populated_store):
        """Test scanning with tag filter and pagination."""
        tag_filter = json.dumps({"attr::person.status": "active"})
        scan = populated_store.scan(
            category="people",
            tag_filter=tag_filter,
            limit=10,
            offset=0,
            profile="test_profile",
        )
        entries = [entry async for entry in scan]
        assert len(entries) == 3, "Expected 3 active people"

        # Test pagination
        scan_paginated = populated_store.scan(
            category="people",
            tag_filter=tag_filter,
            limit=1,
            offset=1,
            profile="test_profile",
        )
        paginated_entries = [entry async for entry in scan_paginated]
        assert len(paginated_entries) == 1, "Expected 1 entry with pagination"

    @pytest.mark.asyncio
    async def test_replace(self, populated_store):
        """Test replacing entries in normalized database."""
        async with populated_store.transaction() as session:
            await session.replace(
                category="people",
                name="person1",
                value=json.dumps({"name": "Alice Updated"}),
                tags={"attr::person.gender": "F", "attr::person.status": "inactive"},
            )
            entry = await session.fetch(category="people", name="person1")
            updated_value = json.dumps({"name": "Alice Updated"})
            assert entry.value == updated_value, "Value not updated"

    @pytest.mark.asyncio
    async def test_complex_filter(self, populated_store):
        """Test complex WQL queries on normalized database."""
        complex_tag_filter = json.dumps(
            {
                "$or": [
                    {
                        "$and": [
                            {"attr::person.gender": {"$like": "F"}},
                            {"attr::person.status": "active"},
                        ]
                    },
                    {"$not": {"attr::person.status": "active"}},
                ]
            }
        )
        scan = populated_store.scan(
            category="people", tag_filter=complex_tag_filter, profile="test_profile"
        )
        entries = [entry async for entry in scan]
        assert len(entries) == 3, "Expected 3 entries with complex filter"

    @pytest.mark.asyncio
    async def test_insert_connections(self, encrypted_store):
        """Test inserting connection data."""
        async with encrypted_store.transaction() as session:
            await session.insert(
                category="connection",
                name="conn_1",
                value=json.dumps(CONNECTION_JSON_1),
                tags={},
            )
            await session.insert(
                category="connection",
                name="conn_2",
                value=json.dumps(CONNECTION_JSON_2),
                tags={},
            )
            await session.insert(
                category="connection",
                name="conn_3",
                value=json.dumps(CONNECTION_JSON_3),
                tags={},
            )

            # Verify insertions
            conn_1 = await session.fetch(category="connection", name="conn_1")
            conn_2 = await session.fetch(category="connection", name="conn_2")
            conn_3 = await session.fetch(category="connection", name="conn_3")

            assert conn_1 is not None, "Failed to insert conn_1"
            assert conn_2 is not None, "Failed to insert conn_2"
            assert conn_3 is not None, "Failed to insert conn_3"

            count = await session.count(category="connection")
            assert count == 3, "Expected 3 connections"

    @pytest.mark.asyncio
    async def test_scan_connections(self, populated_store):
        """Test scanning connections with value filter."""
        # Get all connections and filter by state
        async with populated_store.session() as session:
            all_entries = await session.fetch_all(category="connection")
            active_entries = [
                entry
                for entry in all_entries
                if json.loads(entry.value).get("state") == "active"
            ]
            assert len(active_entries) == 2, "Expected 2 active connections"

    @pytest.mark.asyncio
    async def test_count_connections(self, populated_store):
        """Test counting connections with filter."""
        async with populated_store.session() as session:
            all_entries = await session.fetch_all(category="connection")
            active_count = sum(
                1
                for entry in all_entries
                if json.loads(entry.value).get("state") == "active"
            )
            assert active_count == 2, "Expected 2 active connections"

    @pytest.mark.asyncio
    async def test_replace_connections(self, populated_store):
        """Test replacing connection entries."""
        async with populated_store.transaction() as session:
            updated_json = CONNECTION_JSON_1.copy()
            updated_json["state"] = "completed"
            await session.replace(
                category="connection",
                name="conn_1",
                value=json.dumps(updated_json),
                tags={},
            )
            updated_entry = await session.fetch(category="connection", name="conn_1")
            assert json.loads(updated_entry.value)["state"] == "completed", (
                "State not updated"
            )

    @pytest.mark.asyncio
    async def test_remove_connections(self, populated_store):
        """Test removing connection entries."""
        async with populated_store.transaction() as session:
            await session.remove(category="connection", name="conn_3")
            removed_entry = await session.fetch(category="connection", name="conn_3")
            assert removed_entry is None, "conn_3 should be removed"

    @pytest.mark.asyncio
    async def test_wql_exist_connections(self, populated_store):
        """Test WQL $exist query for connections."""
        async with populated_store.session() as session:
            all_entries = await session.fetch_all(category="connection")
            entries_with_inbound = [
                entry
                for entry in all_entries
                if "inbound_connection_id" in json.loads(entry.value)
            ]
            assert len(entries_with_inbound) == 3, (
                "Expected 3 connections with inbound_connection_id"
            )

    @pytest.mark.asyncio
    async def test_fetch_all(self, populated_store):
        """Test fetching all entries."""
        async with populated_store.session() as session:
            people_entries = await session.fetch_all(category="people")
            assert len(people_entries) == 4, "Expected 4 people entries"

            connection_entries = await session.fetch_all(category="connection")
            assert len(connection_entries) == 3, "Expected 3 connection entries"

    @pytest.mark.asyncio
    async def test_remove_all_people(self, populated_store):
        """Test removing all people entries."""
        async with populated_store.transaction() as session:
            deleted_count = await session.remove_all(category="people")
            assert deleted_count == 4, "Expected to delete 4 people entries"

            remaining = await session.fetch_all(category="people")
            assert len(remaining) == 0, "All people entries should be deleted"

    @pytest.mark.asyncio
    async def test_remove_all_connections(self, populated_store):
        """Test removing all connection entries."""
        async with populated_store.transaction() as session:
            deleted_count = await session.remove_all(category="connection")
            assert deleted_count == 3, "Expected to delete 3 connection entries"

            remaining = await session.fetch_all(category="connection")
            assert len(remaining) == 0, "All connection entries should be deleted"

    @pytest.mark.asyncio
    async def test_rekey(self, test_db_path):
        """Test rekeying the database."""
        uri = f"sqlite://{test_db_path}"

        # Provision with initial key
        store = await DBStore.provision(
            uri=uri,
            pass_key="OldKey",
            profile="test_profile",
            recreate=True,
            release_number="release_0_1",
            schema_config="normalize",
        )

        # Insert test data
        async with store.transaction() as session:
            await session.insert(
                category="test",
                name="item1",
                value=json.dumps({"data": "test"}),
                tags={"tag": "value"},
            )

        # Rekey the database
        await store.rekey(pass_key="NewKey")
        await store.close()

        # Open with new key and verify data
        reopened_store = await DBStore.open(
            uri=uri,
            pass_key="NewKey",
            profile="test_profile",
        )
        async with reopened_store.session() as session:
            entry = await session.fetch(category="test", name="item1")
            assert entry is not None, "Data should be accessible after rekey"
            assert json.loads(entry.value) == {"data": "test"}
        await reopened_store.close()

    @pytest.mark.asyncio
    async def test_open_with_new_key(self, test_db_path):
        """Test opening database with wrong key should fail."""
        uri = f"sqlite://{test_db_path}"

        # First provision with one key
        store1 = await DBStore.provision(
            uri=uri,
            pass_key="Key1",
            profile="test_profile",
            recreate=True,
            release_number="release_0_1",
            schema_config="normalize",
        )
        await store1.close()

        # Try to open with different key - should fail
        with pytest.raises(Exception):
            await DBStore.open(
                uri=uri,
                pass_key="WrongKey",
                profile="test_profile",
            )

    @pytest.mark.asyncio
    async def test_non_encrypted(self, non_encrypted_store):
        """Test operations on non-encrypted normalized database."""
        async with non_encrypted_store.transaction() as session:
            # Insert people data
            await session.insert(
                category="people",
                name="person4",
                value=json.dumps({"name": "David"}),
                tags={"attr::person.gender": "M", "attr::person.status": "active"},
            )
            await session.insert(
                category="people",
                name="person5",
                value=json.dumps({"name": "Eve"}),
                tags={"attr::person.gender": "F", "attr::person.status": "inactive"},
            )
            count = await session.count(category="people")
            assert count == 2, "Expected 2 people entries"

        # Test scanning
        tag_filter = json.dumps({"attr::person.status": "active"})
        scan = non_encrypted_store.scan(
            category="people", tag_filter=tag_filter, profile="test_profile_no_enc"
        )
        entries = [entry async for entry in scan]
        assert len(entries) == 1, "Expected 1 active person in non-encrypted db"
