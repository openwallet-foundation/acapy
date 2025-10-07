"""Test SQLite database store scan operations with normalized schema."""

import json
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from acapy_agent.database_manager.dbstore import DBStore

# Sample pres_ex_v20 JSON data
PRES_REQUEST_JSON = {
    "request_presentations~attach": [
        {
            "data": {
                "base64": json.dumps(
                    {"requested_attributes": [{"name": "attr1"}, {"name": "attr2"}]}
                )
            }
        }
    ]
}

PRES_JSON = {
    "presentation": {"identities": ["cred_id_123"], "proof": {"proof_type": "Ed25519"}}
}


@pytest_asyncio.fixture
async def test_db_path():
    """Create a temporary database path for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_scan_normalized.db"
        yield str(db_path)


@pytest_asyncio.fixture
async def populated_store(test_db_path):
    """Create a database store with test presentation exchange records."""
    uri = f"sqlite://{test_db_path}"
    store = await DBStore.provision(
        uri=uri,
        pass_key="",
        profile="test_profile",
        recreate=True,
        release_number="release_0_1",
        schema_config="normalize",
    )

    # Insert test presentation exchange records in a single transaction for speed
    async with store.transaction() as session:
        for i in range(50):
            if i % 3 == 0:
                state = "active"
            elif i % 3 == 1:
                state = "pending"
            else:
                state = "completed"
            connection_id = f"conn_{i:03d}"
            thread_id = f"thread_{i:03d}"
            name = f"pres_ex_{i:03d}"
            if i % 10 != 9:
                expiry_ms = 3600000
            else:
                expiry_ms = -1000  # 5 expired records
            value = json.dumps(
                {
                    "state": state,
                    "connection_id": connection_id,
                    "thread_id": thread_id,
                    "pres_request": PRES_REQUEST_JSON,
                    "pres": PRES_JSON,
                    "initiator": "self",
                    "role": "prover",
                    "verified": ("true" if i % 2 == 0 else "false"),
                    "verified_msgs": None,
                    "auto_present": "true",
                    "auto_verify": "false",
                    "auto_remove": "false",
                    "error_msg": None,
                    "trace": "false",
                }
            )
            tags = {
                "state": state,
                "connection_id": connection_id,
                "thread_id": thread_id,
                "verified": ("true" if i % 2 == 0 else "false"),
                "initiator": "self",
                "role": "prover",
                "verified_msgs": None,
            }
            await session.insert(
                category="pres_ex_v20",
                name=name,
                value=value,
                tags=tags,
                expiry_ms=expiry_ms,
            )

    yield store
    await store.close()


@pytest_asyncio.fixture
async def store_with_profiles(test_db_path):
    """Create a database store with multiple profiles."""
    uri = f"sqlite://{test_db_path}"
    store = await DBStore.provision(
        uri=uri,
        pass_key="",
        profile="test_profile",
        recreate=True,
        release_number="release_0_1",
        schema_config="normalize",
    )

    # Create additional profile
    await store.create_profile("other_profile")

    # Add data to other profile
    async with store.transaction(profile="other_profile") as session:
        await session.insert(
            category="pres_ex_v20",
            name="pres_ex_other",
            value=json.dumps(
                {
                    "state": "active",
                    "connection_id": "conn_other",
                    "thread_id": "thread_other",
                    "pres_request": PRES_REQUEST_JSON,
                    "pres": PRES_JSON,
                }
            ),
            tags={"state": "active", "connection_id": "conn_other"},
        )

    yield store
    await store.close()


class TestDBStoreScanNormalized:
    """Test suite for scan operations on normalized database store."""

    @pytest.mark.asyncio
    async def test_scan_basic(self, populated_store):
        """Test basic scanning of pres_ex_v20 records without filters."""
        scan = populated_store.scan(category="pres_ex_v20", profile="test_profile")
        entries = [entry async for entry in scan]
        # 50 total records - 5 expired = 45 non-expired records
        assert len(entries) == 45, f"Expected 45 non-expired records, got {len(entries)}"

    @pytest.mark.asyncio
    async def test_scan_with_filter(self, populated_store):
        """Test scanning with a simple tag filter (state=active)."""
        tag_filter = json.dumps({"state": "active"})
        scan = populated_store.scan(
            category="pres_ex_v20", tag_filter=tag_filter, profile="test_profile"
        )
        entries = [entry async for entry in scan]
        # 17 active records total, 2 expired (indices 9, 39) = 15 non-expired active
        expected_count = 15
        assert len(entries) == expected_count, (
            f"Expected {expected_count} active records, got {len(entries)}"
        )
        for entry in entries:
            value = json.loads(entry.value)
            assert value["state"] == "active", (
                f"Entry {entry.name} should have state=active"
            )

    @pytest.mark.asyncio
    async def test_scan_with_complex_filter(self, populated_store):
        """Test scanning with a complex WQL tag filter."""
        complex_tag_filter = json.dumps(
            {
                "$or": [
                    {"state": "active"},
                    {"$and": [{"state": "pending"}, {"verified": "true"}]},
                ]
            }
        )
        scan = populated_store.scan(
            category="pres_ex_v20", tag_filter=complex_tag_filter, profile="test_profile"
        )
        entries = [entry async for entry in scan]
        # 15 active + 8 pending & verified = 23 total
        expected_count = 23
        assert len(entries) == expected_count, (
            f"Expected {expected_count} records, got {len(entries)}"
        )
        for entry in entries:
            value = json.loads(entry.value)
            is_active = value["state"] == "active"
            is_pending_verified = (
                value["state"] == "pending" and value["verified"] == "true"
            )
            assert is_active or is_pending_verified, (
                f"Entry {entry.name} does not match complex filter"
            )

    @pytest.mark.asyncio
    async def test_scan_paginated(self, populated_store):
        """Test scanning with pagination (limit and offset)."""
        tag_filter = json.dumps({"state": "active"})
        limit = 5
        offset = 10
        scan = populated_store.scan(
            category="pres_ex_v20",
            tag_filter=tag_filter,
            limit=limit,
            offset=offset,
            profile="test_profile",
        )
        entries = [entry async for entry in scan]
        assert len(entries) == 5, f"Expected {limit} records, got {len(entries)}"
        for entry in entries:
            value = json.loads(entry.value)
            assert value["state"] == "active", (
                f"Entry {entry.name} should have state=active"
            )

    @pytest.mark.asyncio
    async def test_scan_sorted(self, populated_store):
        """Test scanning with sorting by thread_id and state."""
        # Sort by thread_id ascending
        scan = populated_store.scan(
            category="pres_ex_v20",
            profile="test_profile",
            order_by="thread_id",
            descending=False,
        )
        entries = [entry async for entry in scan]
        assert len(entries) == 45, "Expected 45 non-expired records"
        thread_ids = [json.loads(entry.value)["thread_id"] for entry in entries]
        assert thread_ids == sorted(thread_ids), (
            "Entries not sorted by thread_id ascending"
        )

        # Sort by state descending
        scan = populated_store.scan(
            category="pres_ex_v20",
            profile="test_profile",
            order_by="state",
            descending=True,
        )
        entries = [entry async for entry in scan]
        assert len(entries) == 45, "Expected 45 non-expired records"
        states = [json.loads(entry.value)["state"] for entry in entries]
        assert states == sorted(states, reverse=True), (
            "Entries not sorted by state descending"
        )

    @pytest.mark.asyncio
    async def test_scan_invalid_order_by(self, populated_store):
        """Test scanning with an invalid order_by column."""
        with pytest.raises(Exception) as exc_info:
            scan = populated_store.scan(
                category="pres_ex_v20", profile="test_profile", order_by="invalid_column"
            )
            # Consume the scan to trigger the error
            _ = [entry async for entry in scan]
        assert "Invalid order_by column" in str(exc_info.value), (
            "Expected error for invalid order_by column"
        )

    @pytest.mark.asyncio
    async def test_scan_keyset_basic(self, populated_store):
        """Test basic keyset pagination."""
        # Get starting point
        async with populated_store.session() as session:
            entries = await session.fetch_all(category="pres_ex_v20", limit=1)
            assert len(entries) == 1, "Expected 1 entry to get last_id"
            count = await session.count(category="pres_ex_v20")
            first_id = count - len(entries) + 1

        scan = populated_store.scan_keyset(
            category="pres_ex_v20", last_id=first_id, limit=10, profile="test_profile"
        )
        entries = [entry async for entry in scan]
        assert len(entries) <= 10, f"Expected up to 10 records, got {len(entries)}"

        # Verify ordering
        for i in range(1, len(entries)):
            prev_thread_id = json.loads(entries[i - 1].value)["thread_id"]
            curr_thread_id = json.loads(entries[i].value)["thread_id"]
            assert curr_thread_id > prev_thread_id, "Entries not in order"

    @pytest.mark.asyncio
    async def test_scan_keyset_with_filter(self, populated_store):
        """Test scan_keyset with a tag filter."""
        tag_filter = json.dumps({"state": "pending"})

        # Get starting point for pending records
        async with populated_store.session() as session:
            pending_entries = await session.fetch_all(
                category="pres_ex_v20", tag_filter=tag_filter, limit=1
            )
            assert len(pending_entries) == 1, "Expected 1 pending entry"
            count = await session.count(category="pres_ex_v20")
            first_id = count - len(pending_entries) + 1

        scan = populated_store.scan_keyset(
            category="pres_ex_v20",
            tag_filter=tag_filter,
            last_id=first_id,
            limit=5,
            profile="test_profile",
        )
        entries = [entry async for entry in scan]
        assert len(entries) <= 5, f"Expected up to 5 records, got {len(entries)}"

        for entry in entries:
            value = json.loads(entry.value)
            assert value["state"] == "pending", (
                f"Entry {entry.name} should have state=pending"
            )

    @pytest.mark.asyncio
    async def test_scan_keyset_sorted(self, populated_store):
        """Test scan_keyset with sorting by connection_id."""
        # Get starting point
        async with populated_store.session() as session:
            entries = await session.fetch_all(category="pres_ex_v20", limit=1)
            count = await session.count(category="pres_ex_v20")
            first_id = count - len(entries) + 1

        # Sort ascending
        scan = populated_store.scan_keyset(
            category="pres_ex_v20",
            last_id=first_id,
            limit=5,
            order_by="connection_id",
            descending=False,
            profile="test_profile",
        )
        entries = [entry async for entry in scan]
        assert len(entries) <= 5, f"Expected up to 5 records, got {len(entries)}"
        conn_ids = [json.loads(entry.value)["connection_id"] for entry in entries]
        assert conn_ids == sorted(conn_ids), (
            "Entries not sorted by connection_id ascending"
        )

        # Sort descending
        scan = populated_store.scan_keyset(
            category="pres_ex_v20",
            last_id=first_id,
            limit=5,
            order_by="connection_id",
            descending=True,
            profile="test_profile",
        )
        entries = [entry async for entry in scan]
        assert len(entries) <= 5, f"Expected up to 5 records, got {len(entries)}"
        conn_ids = [json.loads(entry.value)["connection_id"] for entry in entries]
        assert conn_ids == sorted(conn_ids, reverse=True), (
            "Entries not sorted by connection_id descending"
        )

    @pytest.mark.asyncio
    async def test_scan_keyset_invalid_order_by(self, populated_store):
        """Test scan_keyset with an invalid order_by column."""
        with pytest.raises(Exception) as exc_info:
            scan = populated_store.scan_keyset(
                category="pres_ex_v20",
                last_id=1,
                limit=5,
                order_by="invalid_column",
                profile="test_profile",
            )
            # Consume the scan to trigger the error
            _ = [entry async for entry in scan]
        assert "Invalid order_by column" in str(exc_info.value), (
            "Expected error for invalid order_by column"
        )

    @pytest.mark.asyncio
    async def test_scan_expired_records(self, populated_store):
        """Test scanning excludes expired records."""
        scan = populated_store.scan(category="pres_ex_v20", profile="test_profile")
        entries = [entry async for entry in scan]
        # Should have 45 non-expired records (50 total - 5 expired)
        assert len(entries) == 45, f"Expected 45 non-expired records, got {len(entries)}"

        # Verify no expired records (indices 9, 19, 29, 39, 49)
        expired_names = {f"pres_ex_{i:03d}" for i in range(50) if i % 10 == 9}
        found_names = {entry.name for entry in entries}
        assert len(expired_names & found_names) == 0, (
            "Expired records should not be in scan results"
        )

    @pytest.mark.asyncio
    async def test_scan_profile_isolation(self, store_with_profiles):
        """Test scanning with different profiles shows isolation."""
        # Scan default profile - should be empty
        scan = store_with_profiles.scan(category="pres_ex_v20", profile="test_profile")
        entries = [entry async for entry in scan]
        assert len(entries) == 0, "Expected 0 records in test_profile"

        # Scan other profile - should have 1 record
        scan = store_with_profiles.scan(category="pres_ex_v20", profile="other_profile")
        entries = [entry async for entry in scan]
        assert len(entries) == 1, "Expected 1 record in other_profile"
        assert entries[0].name == "pres_ex_other", (
            "Expected pres_ex_other in other_profile"
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
    async def test_scan_keyset_fetch_all(self, populated_store):
        """Test scan_keyset's fetch_all method."""
        scan = populated_store.scan_keyset(
            category="pres_ex_v20", limit=10, profile="test_profile"
        )
        entries = await scan.fetch_all()
        assert len(entries) == 10, f"Expected 10 entries, got {len(entries)}"
        assert all(hasattr(entry, "name") for entry in entries), (
            "All entries should have name attribute"
        )
