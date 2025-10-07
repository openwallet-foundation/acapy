"""Tests for database store scan with generic PostgreSQL."""

# poetry run python \
# acapy_agent/database_manager/test/test_db_store_scan_generic_postgresql.py

import asyncio
import json
import logging
import os

import pytest

from acapy_agent.database_manager.dbstore import DBStore

# Skip all tests in this file if POSTGRES_URL env var is not set
pytestmark = pytest.mark.postgres

# Configure logging
LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

# Define the PostgreSQL connection string
conn_str = os.environ.get(
    "POSTGRES_URL",
    "postgresql://myuser:mypass@localhost:5432/test_scan_normalize?sslmode=prefer",
)
profile_name = "test_profile"
config = {
    "min_connections": 4,
    "max_connections": 15,
    "connect_timeout": 30.0,
    "max_idle": 5.0,
    "max_lifetime": 3600.0,
    "max_sessions": 7,
}


async def setup_data(store: DBStore, num_records: int = 50):
    """Insert credential_record entries for testing."""
    print(f"Inserting {num_records} credential_record entries...")
    LOGGER.debug(
        f"[setup_data] Starting insertion of {num_records} credential_record entries"
    )
    inserted_names = []
    for i in range(num_records):
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
            LOGGER.debug(
                f"[setup_data] Attempting to insert record {name} "
                f"with expiry_ms={expiry_ms}"
            )
            print(f"Attempting to insert record {name} with expiry_ms={expiry_ms}")
            try:
                await session.insert(
                    category="credential_record",
                    name=name,
                    value=value,
                    tags=tags,
                    expiry_ms=expiry_ms,
                )
                inserted_names.append(name)
                LOGGER.debug(f"[setup_data] Successfully inserted record {name}")
                print(f"Successfully inserted record {name}")
            except Exception as e:
                LOGGER.error(f"[setup_data] Failed to insert record {name}: {str(e)}")
                print(f"Failed to insert record {name}: {str(e)}")
                raise
    async with store.session() as session:
        count = await session.count(category="credential_record")
        print(f"Inserted {count} non-expired credential_record entries: {inserted_names}")
        LOGGER.debug(
            f"[setup_data] Inserted {count} non-expired records: {inserted_names}"
        )
        expected_count = num_records - 5  # Expect 5 expired records
        assert count == expected_count, (
            f"Expected {expected_count} non-expired records, got {count}"
        )
        assert len(inserted_names) == num_records, (
            f"Expected {num_records} total insertions, got {len(inserted_names)}"
        )


async def test_scan_basic(store: DBStore):
    """Test basic scanning of credential_record entries without filters."""
    print("Testing basic scan (credential_record)...")
    LOGGER.debug("[test_scan_basic] Starting scan")
    scan = store.scan(category="credential_record", profile=profile_name)
    entries = [entry async for entry in scan]
    print(f"Found {len(entries)} credential_record entries")
    LOGGER.debug(f"[test_scan_basic] Found {len(entries)} records")
    for entry in entries[:5]:
        print(f" - {entry.name}: {json.loads(entry.value)}")
        LOGGER.debug(f"[test_scan_basic] Entry {entry.name}: {json.loads(entry.value)}")
    assert len(entries) == 45, "Expected 45 non-expired records"


async def test_scan_with_filter(store: DBStore):
    """Test scanning with a simple tag filter (status=active)."""
    print("Testing scan with simple tag filter (credential_record)...")
    LOGGER.debug("[test_scan_with_filter] Starting scan with filter")
    tag_filter = json.dumps({"status": "active"})
    scan = store.scan(
        category="credential_record", tag_filter=tag_filter, profile=profile_name
    )
    entries = [entry async for entry in scan]
    expected_count = 15  # 17 active records, 2 expired (indices 9, 39)
    print(f"Found {len(entries)} active credential_record entries")
    LOGGER.debug(
        f"[test_scan_with_filter] Found {len(entries)} records: "
        f"{[entry.name for entry in entries]}"
    )
    assert len(entries) == expected_count, (
        f"Expected {expected_count} active records, got {len(entries)}"
    )
    for entry in entries:
        assert json.loads(entry.value)["status"] == "active", (
            f"Entry {entry.name} should have status=active"
        )


async def test_scan_keyset_basic(store: DBStore):
    """Test basic keyset pagination."""
    print("Testing basic scan_keyset (credential_record)...")
    LOGGER.debug("[test_scan_keyset_basic] Starting keyset scan")
    async with store.session() as session:
        entries = await session.fetch_all(category="credential_record", limit=1)
        assert len(entries) == 1, "Expected 1 entry to get last_id"
        first_id = (
            (await session.count(category="credential_record")) - len(entries) + 1
        )  # Should be 45
    scan = store.scan_keyset(
        category="credential_record", last_id=first_id, limit=10, profile=profile_name
    )
    entries = [entry async for entry in scan]
    print(f"Found {len(entries)} records with scan_keyset, last_id={first_id}, limit=10")
    LOGGER.debug(f"[test_scan_keyset_basic] Found {len(entries)} records")
    assert len(entries) <= 10, f"Expected up to 10 records, got {len(entries)}"
    assert len(entries) == 4, (
        f"Expected 4 records (cred_045 to cred_048), got {len(entries)}"
    )  # Non-expired records after ID 45
    expected_names = [f"cred_{i:03d}" for i in range(45, 49)]
    found_names = [entry.name for entry in entries]
    assert found_names == expected_names, (
        f"Expected names {expected_names}, got {found_names}"
    )
    for i, entry in enumerate(entries[1:], 1):
        assert (
            json.loads(entry.value)["credential_id"]
            > json.loads(entries[i - 1].value)["credential_id"]
        ), "Entries not in order"


async def test_scan_keyset_with_filter(store: DBStore):
    """Test scan_keyset with a tag filter (status=active)."""
    print("Testing scan_keyset with tag filter (credential_record)...")
    LOGGER.debug("[test_scan_keyset_with_filter] Starting keyset scan with filter")
    tag_filter = json.dumps({"status": "active"})
    async with store.session() as session:
        entries = await session.fetch_all(
            category="credential_record", tag_filter=tag_filter, limit=1
        )
        assert len(entries) == 1, "Expected 1 active entry to get last_id"
        first_id = (
            (await session.count(category="credential_record", tag_filter=tag_filter))
            - len(entries)
            + 1
        )  # Should be 15
    scan = store.scan_keyset(
        category="credential_record",
        tag_filter=tag_filter,
        last_id=first_id,
        limit=5,
        profile=profile_name,
    )
    entries = [entry async for entry in scan]
    expected_count = 5  # Up to 5 active records after ID 15
    print(f"Found {len(entries)} active records with scan_keyset")
    LOGGER.debug(
        f"[test_scan_keyset_with_filter] Found {len(entries)} records: "
        f"{[entry.name for entry in entries]}"
    )
    assert len(entries) <= expected_count, (
        f"Expected up to {expected_count} records, got {len(entries)}"
    )
    for entry in entries:
        assert json.loads(entry.value)["status"] == "active", (
            f"Entry {entry.name} should have status=active"
        )


async def main():
    """Main test function for generic_handler scan functions."""
    print("Starting scan and scan_keyset test program for credential_record...")
    LOGGER.debug("[main] Starting test program")

    store = await DBStore.provision(
        uri=conn_str,
        pass_key=None,  # postgres module will ignore this
        profile=profile_name,
        recreate=True,
        release_number="release_0",
        schema_config="generic",
        config=config,
    )
    print(f"Database provisioned at {conn_str}")
    LOGGER.debug(f"[main] Database provisioned at {conn_str}")

    await setup_data(store, num_records=50)
    await test_scan_basic(store)
    await test_scan_with_filter(store)
    await test_scan_keyset_basic(store)
    await test_scan_keyset_with_filter(store)

    await store.close()
    await DBStore.remove(conn_str)
    print("Database removed")
    LOGGER.debug("[main] Database removed")

    print("All scan and scan_keyset tests passed successfully!")
    LOGGER.debug("[main] All tests passed")


if __name__ == "__main__":
    asyncio.run(main())
