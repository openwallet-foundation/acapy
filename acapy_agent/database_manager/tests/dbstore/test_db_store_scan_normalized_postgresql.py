"""Tests for database store scan with normalized PostgreSQL."""

# poetry run python \
# acapy_agent/database_manager/test/test_db_store_scan_normalized_postgresql.py

import asyncio
import json
import logging
import os

import pytest

from acapy_agent.database_manager.databases.errors import DatabaseError
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
    "postgres://myuser:mypass@localhost:5432/test_scan_normalize?sslmode=prefer",
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


async def setup_data(store: DBStore, num_records: int = 50):
    """Insert a large number of pres_ex_v20 records for testing."""
    print(f"Inserting {num_records} pres_ex_v20 records...")
    LOGGER.debug(f"[setup_data] Starting insertion of {num_records} pres_ex_v20 records")
    inserted_names = []
    for i in range(num_records):
        async with store.transaction() as session:
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
                expiry_ms = -1000
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
            LOGGER.debug(
                f"[setup_data] Attempting to insert record {name} "
                f"with expiry_ms={expiry_ms}"
            )
            print(f"Attempting to insert record {name} with expiry_ms={expiry_ms}")
            try:
                await session.insert(
                    category="pres_ex_v20",
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
        count = await session.count(category="pres_ex_v20")
        print(f"Inserted {count} pres_ex_v20 records: {inserted_names}")
        LOGGER.debug(
            f"[setup_data] Inserted {count} non-expired records: {inserted_names}"
        )
        expected_count = num_records - 5  # Expect 5 expired records to be filtered out
        assert count == expected_count, (
            f"Expected {expected_count} non-expired records, got {count}"
        )
        assert len(inserted_names) == num_records, (
            f"Expected {num_records} total insertions, got {len(inserted_names)}"
        )


async def execute_custom_query(store: DBStore):
    """Debug: Print expiry values for pres_ex_v20 records."""
    print("Debugging: Printing expiry values for pres_ex_v20 records...")
    LOGGER.debug("[execute_custom_query] Fetching expiry values for pres_ex_v20 records")
    async with store.session():
        rows = await store._db.execute_query("""
            SELECT name, expiry FROM items
            WHERE category = 'pres_ex_v20' ORDER BY name
        """)
        for row in rows:
            name, expiry = row
            print(f" - {name}: expiry={expiry}")
            LOGGER.debug(f"[execute_custom_query] {name}: expiry={expiry}")
        print(f"Total records: {len(rows)}")
        LOGGER.debug(f"[execute_custom_query] Total records: {len(rows)}")
        return len(rows)


async def test_scan_basic(store: DBStore):
    """Test basic scanning of pres_ex_v20 records without filters."""
    print("Testing basic scan (pres_ex_v20)...")
    LOGGER.debug("[test_scan_basic] Starting scan")
    scan = store.scan(category="pres_ex_v20", profile=profile_name)
    entries = [entry async for entry in scan]
    print(f"Found {len(entries)} pres_ex_v20 records")
    LOGGER.debug(f"[test_scan_basic] Found {len(entries)} records")
    for entry in entries[:5]:
        print(f" - {entry.name}: {json.loads(entry.value)}")
        LOGGER.debug(f"[test_scan_basic] Entry {entry.name}: {json.loads(entry.value)}")
    assert len(entries) == 45, "Expected 45 non-expired records"


async def test_scan_with_filter(store: DBStore):
    """Test scanning with a simple tag filter (state=active)."""
    print("Testing scan with simple tag filter (pres_ex_v20)...")
    LOGGER.debug("[test_scan_with_filter] Starting scan with filter")
    tag_filter = json.dumps({"state": "active"})
    scan = store.scan(category="pres_ex_v20", tag_filter=tag_filter, profile=profile_name)
    entries = [entry async for entry in scan]
    expected_count = 15  # 17 active records, 2 expired (indices 9, 39)
    print(f"Found {len(entries)} active pres_ex_v20 records")
    LOGGER.debug(
        f"[test_scan_with_filter] Found {len(entries)} records: "
        f"{[entry.name for entry in entries]}"
    )
    assert len(entries) == expected_count, (
        f"Expected {expected_count} active records, got {len(entries)}"
    )
    for entry in entries:
        assert json.loads(entry.value)["state"] == "active", (
            f"Entry {entry.name} should have state=active"
        )


async def test_scan_with_complex_filter(store: DBStore):
    """Test scanning with a complex WQL tag filter."""
    print("Testing scan with complex WQL filter (pres_ex_v20)...")
    LOGGER.debug("[test_scan_with_complex_filter] Starting scan with complex filter")
    complex_tag_filter = json.dumps(
        {
            "$or": [
                {"state": "active"},
                {"$and": [{"state": "pending"}, {"verified": "true"}]},
            ]
        }
    )
    scan = store.scan(
        category="pres_ex_v20", tag_filter=complex_tag_filter, profile=profile_name
    )
    entries = [entry async for entry in scan]
    expected_count = 15 + 8  # 15 active + 8 pending & verified
    print(f"Found {len(entries)} records with complex filter")
    LOGGER.debug(f"[test_scan_with_complex_filter] Found {len(entries)} records")
    for entry in entries[:5]:
        print(f" - {entry.name}: {json.loads(entry.value)}")
        LOGGER.debug(
            f"[test_scan_with_complex_filter] Entry {entry.name}: "
            f"{json.loads(entry.value)}"
        )
    assert len(entries) == expected_count, (
        f"Expected {expected_count} records, got {len(entries)}"
    )
    for entry in entries:
        value = json.loads(entry.value)
        assert value["state"] == "active" or (
            value["state"] == "pending" and value["verified"] == "true"
        ), f"Entry {entry.name} does not match filter"


async def test_scan_paginated(store: DBStore):
    """Test scanning with pagination (limit and offset)."""
    print("Testing paginated scan (pres_ex_v20)...")
    LOGGER.debug("[test_scan_paginated] Starting paginated scan")
    tag_filter = json.dumps({"state": "active"})
    limit = 5
    offset = 10
    scan = store.scan(
        category="pres_ex_v20",
        tag_filter=tag_filter,
        limit=limit,
        offset=offset,
        profile=profile_name,
    )
    entries = [entry async for entry in scan]
    print(f"Found {len(entries)} active records with limit={limit}, offset={offset}")
    LOGGER.debug(f"[test_scan_paginated] Found {len(entries)} records")
    assert len(entries) == 5, f"Expected 5 records, got {len(entries)}"
    for entry in entries:
        assert json.loads(entry.value)["state"] == "active", (
            f"Entry {entry.name} should have state=active"
        )


async def test_scan_sorted(store: DBStore):
    """Test scanning with sorting by thread_id and state."""
    print("Testing sorted scan (pres_ex_v20)...")
    LOGGER.debug("[test_scan_sorted] Starting sorted scan")
    scan = store.scan(
        category="pres_ex_v20",
        profile=profile_name,
        order_by="thread_id",
        descending=False,
    )
    entries = [entry async for entry in scan]
    print(f"Found {len(entries)} records sorted by thread_id ascending")
    LOGGER.debug(f"[test_scan_sorted] Found {len(entries)} records by thread_id")
    assert len(entries) == 45, "Expected 45 non-expired records"
    thread_ids = [json.loads(entry.value)["thread_id"] for entry in entries]
    assert thread_ids == sorted(thread_ids), "Entries not sorted by thread_id ascending"

    scan = store.scan(
        category="pres_ex_v20", profile=profile_name, order_by="state", descending=True
    )
    entries = [entry async for entry in scan]
    print(f"Found {len(entries)} records sorted by state descending")
    LOGGER.debug(f"[test_scan_sorted] Found {len(entries)} records by state")
    assert len(entries) == 45, "Expected 45 non-expired records"
    states = [json.loads(entry.value)["state"] for entry in entries]
    assert states == sorted(states, reverse=True), (
        "Entries not sorted by state descending"
    )


async def test_scan_invalid_order_by(store: DBStore):
    """Test scanning with an invalid order_by column."""
    print("Testing scan with invalid order_by (pres_ex_v20)...")
    LOGGER.debug("[test_scan_invalid_order_by] Starting scan with invalid order_by")
    try:
        scan = store.scan(
            category="pres_ex_v20", profile=profile_name, order_by="invalid_column"
        )
        async for _ in scan:
            pass
        assert False, "Should raise DatabaseError for invalid order_by"
    except Exception as e:
        print(f"Correctly raised error for invalid order_by: {e}")
        LOGGER.debug(f"[test_scan_invalid_order_by] Caught error: {str(e)}")
        assert "Invalid order_by column" in str(e), (
            "Expected DatabaseError for invalid order_by"
        )


async def test_scan_keyset_basic(store: DBStore):
    """Test basic keyset pagination."""
    print("Testing basic scan_keyset (pres_ex_v20)...")
    LOGGER.debug("[test_scan_keyset_basic] Starting keyset scan")
    async with store.session() as session:
        entries = await session.fetch_all(category="pres_ex_v20", limit=1)
        assert len(entries) == 1, "Expected 1 entry to get last_id"
        first_id = (await session.count(category="pres_ex_v20")) - len(entries) + 1

    scan = store.scan_keyset(
        category="pres_ex_v20", last_id=first_id, limit=10, profile=profile_name
    )
    entries = [entry async for entry in scan]
    print(f"Found {len(entries)} records with scan_keyset, last_id={first_id}, limit=10")
    LOGGER.debug(f"[test_scan_keyset_basic] Found {len(entries)} records")
    assert len(entries) <= 10, f"Expected up to 10 records, got {len(entries)}"
    for i, entry in enumerate(entries[1:], 1):
        assert (
            json.loads(entry.value)["thread_id"]
            > json.loads(entries[i - 1].value)["thread_id"]
        ), "Entries not in order"


async def test_scan_keyset_with_filter(store: DBStore):
    """Test scan_keyset with a tag filter."""
    print("Testing scan_keyset with tag filter (pres_ex_v20)...")
    LOGGER.debug("[test_scan_keyset_with_filter] Starting keyset scan with filter")
    tag_filter = json.dumps({"state": "pending"})
    async with store.session() as session:
        entries = await session.fetch_all(
            category="pres_ex_v20", tag_filter=tag_filter, limit=1
        )
        assert len(entries) == 1, "Expected 1 pending entry to get last_id"
        first_id = (await session.count(category="pres_ex_v20")) - len(entries) + 1

    scan = store.scan_keyset(
        category="pres_ex_v20",
        tag_filter=tag_filter,
        last_id=first_id,
        limit=5,
        profile=profile_name,
    )
    entries = [entry async for entry in scan]
    expected_count = 5
    print(f"Found {len(entries)} pending records with scan_keyset")
    LOGGER.debug(f"[test_scan_keyset_with_filter] Found {len(entries)} records")
    assert len(entries) <= expected_count, (
        f"Expected up to {expected_count} records, got {len(entries)}"
    )
    for entry in entries:
        assert json.loads(entry.value)["state"] == "pending", (
            f"Entry {entry.name} should have state=pending"
        )


async def test_scan_keyset_sorted(store: DBStore):
    """Test scan_keyset with sorting by connection_id."""
    print("Testing scan_keyset sorted by connection_id (pres_ex_v20)...")
    LOGGER.debug("[test_scan_keyset_sorted] Starting keyset scan with sort")
    async with store.session() as session:
        entries = await session.fetch_all(category="pres_ex_v20", limit=1)
        assert len(entries) == 1, "Expected 1 entry to get last_id"
        first_id = (await session.count(category="pres_ex_v20")) - len(entries) + 1

    scan = store.scan_keyset(
        category="pres_ex_v20",
        last_id=first_id,
        limit=5,
        order_by="connection_id",
        descending=False,
        profile=profile_name,
    )
    entries = [entry async for entry in scan]
    print(f"Found {len(entries)} records sorted by connection_id ascending")
    LOGGER.debug(f"[test_scan_keyset_sorted] Found {len(entries)} records ascending")
    assert len(entries) <= 5, f"Expected up to 5 records, got {len(entries)}"
    conn_ids = [json.loads(entry.value)["connection_id"] for entry in entries]
    assert conn_ids == sorted(conn_ids), "Entries not sorted by connection_id ascending"

    scan = store.scan_keyset(
        category="pres_ex_v20",
        last_id=first_id,
        limit=5,
        order_by="connection_id",
        descending=True,
        profile=profile_name,
    )
    entries = [entry async for entry in scan]
    print(f"Found {len(entries)} records sorted by connection_id descending")
    LOGGER.debug(f"[test_scan_keyset_sorted] Found {len(entries)} records descending")
    assert len(entries) <= 5, f"Expected up to 5 records, got {len(entries)}"
    conn_ids = [json.loads(entry.value)["connection_id"] for entry in entries]
    assert conn_ids == sorted(conn_ids, reverse=True), (
        "Entries not sorted by connection_id descending"
    )


async def test_scan_keyset_invalid_order_by(store: DBStore):
    """Test scan_keyset with an invalid order_by column."""
    print("Testing scan_keyset with invalid order_by (pres_ex_v20)...")
    LOGGER.debug(
        "[test_scan_keyset_invalid_order_by] Starting keyset scan with invalid order_by"
    )
    try:
        scan = store.scan_keyset(
            category="pres_ex_v20",
            last_id=1,
            limit=5,
            order_by="invalid_column",
            profile=profile_name,
        )
        async for _ in scan:
            pass
        assert False, "Should raise DatabaseError for invalid order_by"
    except Exception as e:
        print(f"Correctly raised error for invalid order_by: {e}")
        LOGGER.debug(f"[test_scan_keyset_invalid_order_by] Caught error: {str(e)}")
        assert "Invalid order_by column" in str(e), (
            "Expected DatabaseError for invalid order_by"
        )


async def test_scan_expired_records(store: DBStore):
    """Test scanning excludes expired records."""
    print("Testing scan excludes expired records (pres_ex_v20)...")
    LOGGER.debug("[test_scan_expired_records] Starting scan for expired records")
    scan = store.scan(category="pres_ex_v20", profile=profile_name)
    entries = [entry async for entry in scan]
    print(f"Found {len(entries)} non-expired records")
    LOGGER.debug(f"[test_scan_expired_records] Found {len(entries)} records")
    assert len(entries) == 45, "Expected 45 non-expired records (5 expired)"
    for entry in entries:
        assert "expiry" not in json.loads(entry.value), (
            "Expired records should not be returned"
        )


async def test_scan_profile_isolation(store: DBStore):
    """Test scanning with a different profile."""
    print("Testing scan with different profile (pres_ex_v20)...")
    LOGGER.debug("[test_scan_profile_isolation] Starting profile isolation scan")
    new_profile = "other_profile"
    await store.create_profile(new_profile)
    async with store.transaction(profile=new_profile) as session:
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
    scan = store.scan(category="pres_ex_v20", profile=new_profile)
    entries = [entry async for entry in scan]
    print(f"Found {len(entries)} records in profile {new_profile}")
    LOGGER.debug(f"[test_scan_profile_isolation] Found {len(entries)} records")
    assert len(entries) == 1, "Expected 1 record in new profile"
    assert entries[0].name == "pres_ex_other", "Expected pres_ex_other in new profile"


async def main():
    """Main test function executing all test scenarios for scan and scan_keyset."""
    print("=== Starting PostgreSQL Scan and Scan_Keyset Test Program for pres_ex_v20 ===")
    LOGGER.debug("[main] Starting test program")

    store = None
    try:
        store = await DBStore.provision(
            uri=conn_str,
            key_method=None,
            pass_key=None,
            profile=profile_name,
            recreate=True,
            release_number="release_0_1",
            schema_config="normalize",
            config=config,
        )
        await store.initialize()
        print(f"Database provisioned at {conn_str}")
        LOGGER.debug(f"[main] Database provisioned at {conn_str}")
    except DatabaseError as e:
        LOGGER.error("Failed to initialize database: %s", str(e))
        print(f"Oops! Failed to initialize database: {e}")
        raise
    except Exception as e:
        LOGGER.error("Unexpected error during store initialization: %s", str(e))
        print(f"Oops! Unexpected error during store initialization: {e}")
        raise

    try:
        await setup_data(store, num_records=50)
        # await execute_custom_query(store)

        await test_scan_basic(store)
        await test_scan_with_filter(store)
        await test_scan_with_complex_filter(store)
        await test_scan_paginated(store)
        await test_scan_sorted(store)
        await test_scan_invalid_order_by(store)
        await test_scan_keyset_basic(store)
        await test_scan_keyset_with_filter(store)
        await test_scan_keyset_sorted(store)
        await test_scan_keyset_invalid_order_by(store)
        await test_scan_expired_records(store)
        await test_scan_profile_isolation(store)

        print("=== All Tests Completed Successfully ===")
    except Exception as e:
        LOGGER.error("Error in test execution: %s", str(e))
        print(f"Error in test execution: {e}")
        raise
    finally:
        if store:
            try:
                # await store.close(remove=True)
                print("Database closed and removed successfully.")
                LOGGER.debug("[main] Database closed and removed")
            except Exception as e:
                LOGGER.error("Failed to close database: %s", str(e))
                print(f"Failed to close database: {e}")
                raise


if __name__ == "__main__":
    asyncio.run(main())
