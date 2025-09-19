"""Test SQLite database store with generic schema."""

import json
import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from acapy_agent.database_manager.dbstore import DBStore


@pytest_asyncio.fixture
async def test_db_path():
    """Create a temporary database path for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_dbstore.db"
        yield str(db_path)
        # Cleanup happens automatically when tmpdir is deleted


@pytest_asyncio.fixture
async def encrypted_store(test_db_path):
    """Create an encrypted database store for testing."""
    uri = f"sqlite://{test_db_path}"
    store = await DBStore.provision(
        uri=uri,
        pass_key="Strong_key",
        profile="test_profile",
        recreate=True,
        release_number="release_0",
        schema_config="generic",
    )
    yield store
    await store.close()


@pytest_asyncio.fixture
async def non_encrypted_store():
    """Create a non-encrypted database store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_dbstore_no_enc.db"
        uri = f"sqlite://{db_path}"
        store = await DBStore.provision(
            uri=uri,
            pass_key=None,
            profile="test_profile_no_enc",
            recreate=True,
            release_number="release_0",
            schema_config="generic",
        )
        yield store
        await store.close()


@pytest_asyncio.fixture
async def populated_store(encrypted_store):
    """Create a store with test data."""
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
        await session.insert(
            category="people",
            name="person4",
            value=json.dumps({"name": "David"}),
            tags={"attr::person.gender": "M", "attr::person.status": "active"},
        )
    return encrypted_store


class TestDBStoreGeneric:
    """Test suite for generic database store operations."""

    @pytest.mark.asyncio
    async def test_provision(self, test_db_path):
        """Test provisioning an encrypted database."""
        uri = f"sqlite://{test_db_path}"
        store = await DBStore.provision(
            uri=uri,
            pass_key="Strong_key",
            profile="test_profile",
            recreate=True,
            release_number="release_0",
            schema_config="generic",
        )
        assert os.path.exists(test_db_path), "Database file not created"
        await store.close()

    @pytest.mark.asyncio
    async def test_insert(self, encrypted_store):
        """Test inserting test data into the database."""
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
        """Test replacing existing entries."""
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
        """Test scanning with a complex tag filter."""
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
        # Expected: 2 active females + 1 inactive male = 3 total
        assert len(entries) == 3, "Expected 3 entries with complex filter"

    @pytest.mark.asyncio
    async def test_fetch_all(self, populated_store):
        """Test fetching all entries."""
        async with populated_store.session() as session:
            entries = await session.fetch_all(category="people")
            assert len(entries) == 4, "Expected 4 entries"

    @pytest.mark.asyncio
    async def test_remove_all(self, populated_store):
        """Test removing all entries."""
        async with populated_store.transaction() as session:
            deleted_count = await session.remove_all(category="people")
            assert deleted_count == 4, "Expected to delete 4 entries"

            # Verify all entries are deleted
            remaining = await session.fetch_all(category="people")
            assert len(remaining) == 0, "All entries should be deleted"

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
            release_number="release_0",
            schema_config="generic",
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
    async def test_rekey(self, test_db_path):
        """Test rekeying the database."""
        uri = f"sqlite://{test_db_path}"

        # Provision with initial key
        store = await DBStore.provision(
            uri=uri,
            pass_key="OldKey",
            profile="test_profile",
            recreate=True,
            release_number="release_0",
            schema_config="generic",
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
    async def test_non_encrypted(self, non_encrypted_store):
        """Test operations on non-encrypted database."""
        async with non_encrypted_store.transaction() as session:
            await session.insert(
                category="test",
                name="item1",
                value=json.dumps({"data": "unencrypted"}),
                tags={"encrypted": "false"},
            )

            entry = await session.fetch(category="test", name="item1")
            assert entry is not None
            assert json.loads(entry.value) == {"data": "unencrypted"}
