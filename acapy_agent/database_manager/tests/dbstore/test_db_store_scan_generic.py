"""Test SQLite database store scan operations with generic schema."""

import json
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from acapy_agent.database_manager.dbstore import DBStore


@pytest_asyncio.fixture
async def test_db_path():
    """Create a temporary database path for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_scan_generic.db"
        yield str(db_path)


@pytest_asyncio.fixture
async def populated_store(test_db_path):
    """Create a database store with test credential records."""
    uri = f"sqlite://{test_db_path}"
    store = await DBStore.provision(
        uri=uri,
        pass_key="test_key",
        profile="test_profile",
        recreate=True,
        release_number="release_0",
        schema_config="generic",
    )

    # Insert test credential records
    for i in range(50):
        async with store.transaction() as session:
            if i % 3 == 0:
                status = "active"
            elif i % 3 == 1:
                status = "pending"
            else:
                status = "revoked"
            connection_id = f"conn_{i:03d}"
            name = f"cred_{i:03d}"
            if i % 10 != 9:
                expiry_ms = 3600000
            else:
                expiry_ms = -1000  # 5 expired records
            value = json.dumps(
                {
                    "status": status,
                    "connection_id": connection_id,
                    "credential_id": f"cred_id_{i:03d}",
                    "schema_id": "schema:1.0",
                    "issuer_did": "did:example:issuer",
                    "issued_at": "2025-06-23T12:00:00Z",
                }
            )
            tags = {
                "status": status,
                "connection_id": connection_id,
                "issuer_did": "did:example:issuer",
            }
            await session.insert(
                category="credential_record",
                name=name,
                value=value,
                tags=tags,
                expiry_ms=expiry_ms,
            )

    yield store
    await store.close()


class TestDBStoreScanGeneric:
    """Test suite for scan operations on generic database store."""

    @pytest.mark.asyncio
    async def test_scan_basic(self, populated_store):
        """Test basic scanning of credential_record entries without filters."""
        scan = populated_store.scan(category="credential_record", profile="test_profile")
        entries = [entry async for entry in scan]
        # 50 total records - 5 expired = 45 non-expired records
        assert len(entries) == 45, f"Expected 45 non-expired records, got {len(entries)}"

    @pytest.mark.asyncio
    async def test_scan_with_filter(self, populated_store):
        """Test scanning with a simple tag filter (status=active)."""
        tag_filter = json.dumps({"status": "active"})
        scan = populated_store.scan(
            category="credential_record", tag_filter=tag_filter, profile="test_profile"
        )
        entries = [entry async for entry in scan]
        # 17 active records total, 2 expired (indices 9, 39) = 15 non-expired active
        expected_count = 15
        assert len(entries) == expected_count, (
            f"Expected {expected_count} active records, got {len(entries)}"
        )
        for entry in entries:
            value = json.loads(entry.value)
            assert value["status"] == "active", (
                f"Entry {entry.name} should have status=active"
            )

    @pytest.mark.asyncio
    async def test_scan_with_pagination(self, populated_store):
        """Test scanning with limit and offset for pagination."""
        # First page
        scan1 = populated_store.scan(
            category="credential_record", profile="test_profile", limit=10, offset=0
        )
        entries1 = [entry async for entry in scan1]
        assert len(entries1) == 10, "Expected 10 entries in first page"

        # Second page
        scan2 = populated_store.scan(
            category="credential_record", profile="test_profile", limit=10, offset=10
        )
        entries2 = [entry async for entry in scan2]
        assert len(entries2) == 10, "Expected 10 entries in second page"

        # Ensure no overlap
        names1 = {entry.name for entry in entries1}
        names2 = {entry.name for entry in entries2}
        assert len(names1 & names2) == 0, "Pages should not overlap"

    @pytest.mark.asyncio
    async def test_scan_keyset_basic(self, populated_store):
        """Test basic keyset pagination."""
        # Get the first entry to establish starting point
        async with populated_store.session() as session:
            all_entries = await session.fetch_all(category="credential_record", limit=1)
            assert len(all_entries) == 1, "Expected 1 entry"

            # Calculate first_id based on total count
            total_count = await session.count(category="credential_record")
            first_id = total_count - len(all_entries) + 1  # Should be 45

        # Use keyset scan starting after first_id
        scan = populated_store.scan_keyset(
            category="credential_record",
            last_id=first_id,
            limit=10,
            profile="test_profile",
        )
        entries = [entry async for entry in scan]

        # Should get remaining records after ID 45 (cred_045 to cred_048, non-expired)
        assert len(entries) == 4, (
            f"Expected 4 records after ID {first_id}, got {len(entries)}"
        )

        expected_names = [f"cred_{i:03d}" for i in range(45, 49)]
        found_names = [entry.name for entry in entries]
        assert found_names == expected_names, (
            f"Expected names {expected_names}, got {found_names}"
        )

    @pytest.mark.asyncio
    async def test_scan_keyset_with_filter(self, populated_store):
        """Test scan_keyset with a tag filter (status=active)."""
        tag_filter = json.dumps({"status": "active"})

        # Get starting point for active records
        async with populated_store.session() as session:
            active_entries = await session.fetch_all(
                category="credential_record", tag_filter=tag_filter, limit=1
            )
            assert len(active_entries) == 1, "Expected 1 active entry"

            active_count = await session.count(
                category="credential_record", tag_filter=tag_filter
            )
            first_id = active_count - len(active_entries) + 1  # Should be 15

        # Use keyset scan with filter
        scan = populated_store.scan_keyset(
            category="credential_record",
            tag_filter=tag_filter,
            last_id=first_id,
            limit=5,
            profile="test_profile",
        )
        entries = [entry async for entry in scan]

        # Should get up to 5 active records after the starting ID
        assert len(entries) <= 5, f"Expected up to 5 records, got {len(entries)}"

        for entry in entries:
            value = json.loads(entry.value)
            assert value["status"] == "active", (
                f"Entry {entry.name} should have status=active"
            )

    @pytest.mark.asyncio
    async def test_scan_keyset_ordering(self, populated_store):
        """Test that scan_keyset returns entries in correct order."""
        scan = populated_store.scan_keyset(
            category="credential_record", limit=20, profile="test_profile"
        )
        entries = [entry async for entry in scan]

        # Verify entries are ordered by credential_id
        for i in range(1, len(entries)):
            prev_cred_id = json.loads(entries[i - 1].value)["credential_id"]
            curr_cred_id = json.loads(entries[i].value)["credential_id"]
            assert curr_cred_id > prev_cred_id, (
                f"Entries not in order: {prev_cred_id} should come before {curr_cred_id}"
            )

    @pytest.mark.asyncio
    async def test_scan_complex_filter(self, populated_store):
        """Test scanning with complex WQL filter."""
        # Complex filter: (active OR pending) AND connection_id starts with conn_0
        complex_filter = json.dumps(
            {
                "$and": [
                    {"$or": [{"status": "active"}, {"status": "pending"}]},
                    {"connection_id": {"$like": "conn_0%"}},
                ]
            }
        )

        scan = populated_store.scan(
            category="credential_record",
            tag_filter=complex_filter,
            profile="test_profile",
        )
        entries = [entry async for entry in scan]

        # Verify all entries match the complex filter
        for entry in entries:
            value = json.loads(entry.value)
            status_ok = value["status"] in ["active", "pending"]
            conn_ok = value["connection_id"].startswith("conn_0")
            assert status_ok and conn_ok, (
                f"Entry {entry.name} doesn't match complex filter"
            )

    @pytest.mark.asyncio
    async def test_scan_empty_category(self, populated_store):
        """Test scanning an empty category returns no results."""
        scan = populated_store.scan(
            category="non_existent_category", profile="test_profile"
        )
        entries = [entry async for entry in scan]
        assert len(entries) == 0, "Expected no entries for non-existent category"

    @pytest.mark.asyncio
    async def test_expired_records_excluded(self, populated_store):
        """Test that expired records are excluded from scan results."""
        # Count all records
        async with populated_store.session() as session:
            count = await session.count(category="credential_record")

        # Should be 45 non-expired records (50 total - 5 expired)
        assert count == 45, f"Expected 45 non-expired records, got {count}"

        # Verify scan also excludes expired records
        scan = populated_store.scan(category="credential_record", profile="test_profile")
        entries = [entry async for entry in scan]
        assert len(entries) == 45, f"Expected 45 entries from scan, got {len(entries)}"

        # Verify none of the returned entries are cred_009, cred_019, etc. (expired)
        expired_names = {f"cred_{i:03d}" for i in range(50) if i % 10 == 9}
        found_names = {entry.name for entry in entries}
        assert len(expired_names & found_names) == 0, (
            "Expired records should not be in scan results"
        )
