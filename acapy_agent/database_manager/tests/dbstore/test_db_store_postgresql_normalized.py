"""Test PostgreSQL database store with normalized schema."""
# Run: poetry run python <path>/test_db_store_postgresql_normalized.py

import asyncio
import json
import logging
import os

import pytest

from acapy_agent.database_manager.dbstore import DBStore

# Skip all tests in this file if POSTGRES_URL env var is not set
pytestmark = pytest.mark.postgres

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

# Define the PostgreSQL connection string
conn_str = os.environ.get(
    "POSTGRES_URL", "postgres://myuser:mypass@localhost:5432/test_normalize"
)
profile_name = "test_normalize"
config = {
    "min_connections": 4,
    "max_connections": 15,
    "connect_timeout": 30.0,
    "max_idle": 5.0,
    "max_lifetime": 3600.0,
    "max_sessions": 7,
}

# Sample connection JSON data
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


async def test_provision():
    """Test provisioning a PostgreSQL database."""
    print("Provisioning the PostgreSQL database...")
    store = await DBStore.provision(
        uri=conn_str,
        key_method=None,
        pass_key=None,
        profile=profile_name,
        recreate=True,  # Ensure fresh database
        release_number="release_0_1",
        schema_config="normalize",
        config=config,
    )
    print(f"Database provisioned at {conn_str}")
    return store


async def test_insert(store):
    """Test inserting test data into the database (people category)."""
    print("Inserting test data (people)...")
    async with store.transaction() as session:
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
        print(f"Inserted 3 people, total count: {count}")
        assert count == 3, "Expected 3 entries"


async def test_scan(store):
    """Test scanning with tag filter and pagination (people category)."""
    print("Testing scan with tag filter (people)...")
    tag_filter = json.dumps({"attr::person.status": "active"})
    scan = store.scan(
        category="people", tag_filter=tag_filter, limit=10, offset=0, profile=profile_name
    )
    entries = [entry async for entry in scan]
    print(f"Found {len(entries)} active people")
    assert len(entries) == 2, "Expected 2 active people"
    for entry in entries:
        try:
            value = json.loads(entry.value)
            print(f" - {entry.name}: {value}")
        except json.JSONDecodeError:
            print(f"Failed to parse JSON for {entry.name}: {entry.value}")
            raise

    print("Testing scan with limit and offset (people)...")
    scan_paginated = store.scan(
        category="people", tag_filter=tag_filter, limit=1, offset=1, profile=profile_name
    )
    paginated_entries = [entry async for entry in scan_paginated]
    print(f"Found {len(paginated_entries)} entries with limit=1, offset=1")
    assert len(paginated_entries) == 1, "Expected 1 entry"


async def test_replace(store):
    """Test replacing entries (people category)."""
    print("Testing replace (people)...")
    async with store.transaction() as session:
        await session.insert(
            category="people",
            name="person4",
            value=json.dumps({"name": "David"}),
            tags={"attr::person.gender": "M", "attr::person.status": "active"},
            expiry_ms=3600000,
        )
        await session.replace(
            category="people",
            name="person1",
            value=json.dumps({"name": "Alice Updated"}),
            tags={"attr::person.gender": "F", "attr::person.status": "inactive"},
        )
        entry = await session.fetch(category="people", name="person1")
        print(f"Updated entry: {entry}")
        assert entry.value == json.dumps({"name": "Alice Updated"}), "Value not updated"

        await session.replace(
            category="people",
            name="person4",
            value=json.dumps({"name": "David Updated"}),
            tags={"attr::person.gender": "M", "attr::person.status": "inactive"},
        )
        updated_entry = await session.fetch(category="people", name="person4")
        print(f"Updated entry: {updated_entry}")
        assert updated_entry.value == json.dumps({"name": "David Updated"}), (
            "Value not updated"
        )


async def test_complex_filter(store):
    """Test scanning with a complex tag filter (people category)."""
    print("Testing complex filter (people)...")
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
    scan = store.scan(
        category="people", tag_filter=complex_tag_filter, profile=profile_name
    )
    entries = [entry async for entry in scan]
    print(f"Found {len(entries)} entries with complex filter")
    assert len(entries) == 4, "Expected 4 entries"
    for entry in entries:
        value = json.loads(entry.value)
        print(f" - {entry.name}: {value}")


async def test_insert_connections(store):
    """Test inserting connection data."""
    print("Inserting connection data...")
    async with store.transaction() as session:
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
        conn_1 = await session.fetch(category="connection", name="conn_1")
        conn_2 = await session.fetch(category="connection", name="conn_2")
        conn_3 = await session.fetch(category="connection", name="conn_3")
        print(f"Inserted conn_1: {json.loads(conn_1.value)}")
        print(f"Inserted conn_2: {json.loads(conn_2.value)}")
        print(f"Inserted conn_3: {json.loads(conn_3.value)}")
        assert conn_1 is not None, "Failed to insert conn_1"
        assert conn_2 is not None, "Failed to insert conn_2"
        assert conn_3 is not None, "Failed to insert conn_3"
        count = await session.count(category="connection")
        print(f"Inserted 3 connections, total count: {count}")
        assert count == 3, "Expected 3 connections"


async def test_scan_connections(store):
    """Test scanning connections with value filter and pagination."""
    print("Testing scan with value filter (connections)...")
    entries = []
    async with store.session() as session:
        all_entries = await session.fetch_all(category="connection")
        for entry in all_entries:
            value = json.loads(entry.value)
            if value.get("state") == "active":
                entries.append(entry)
        print(f"Found {len(entries)} active connections")
        assert len(entries) == 2, "Expected 2 active connections"
        for entry in entries:
            print(f" - {entry.name}: {json.loads(entry.value)}")

    print("Testing scan with limit and offset (connections)...")
    entries_paginated = entries[1:2]  # Simulate offset=1, limit=1
    print(f"Found {len(entries_paginated)} entries with limit=1, offset=1")
    assert len(entries_paginated) == 1, "Expected 1 entry"


async def test_count_connections(store):
    """Test counting connections with a value filter."""
    print("Testing count with value filter (connections)...")
    async with store.session() as session:
        all_entries = await session.fetch_all(category="connection")
        count = sum(
            1 for entry in all_entries if json.loads(entry.value).get("state") == "active"
        )
        print(f"Counted {count} active connections")
        assert count == 2, "Expected 2 active connections"


async def test_replace_connections(store):
    """Test replacing connection entries."""
    print("Testing replace (connections)...")
    async with store.transaction() as session:
        updated_json = CONNECTION_JSON_1.copy()
        updated_json["state"] = "completed"
        await session.replace(
            category="connection", name="conn_1", value=json.dumps(updated_json), tags={}
        )
        updated_entry = await session.fetch(category="connection", name="conn_1")
        print(f"Updated conn_1: {json.loads(updated_entry.value)}")
        assert json.loads(updated_entry.value)["state"] == "completed", (
            "State not updated"
        )

        await session.insert(
            category="connection",
            name="conn_4",
            value=json.dumps(CONNECTION_JSON_1),
            tags={},
        )
        new_entry = await session.fetch(category="connection", name="conn_4")
        print(f"Inserted conn_4: {json.loads(new_entry.value)}")
        assert new_entry is not None, "Insert failed"

        updated_json_4 = CONNECTION_JSON_1.copy()
        updated_json_4["state"] = "inactive"
        await session.replace(
            category="connection",
            name="conn_4",
            value=json.dumps(updated_json_4),
            tags={},
        )
        updated_conn4 = await session.fetch(category="connection", name="conn_4")
        print(f"Updated conn_4: {json.loads(updated_conn4.value)}")
        assert json.loads(updated_conn4.value)["state"] == "inactive", "State not updated"


async def test_remove_connections(store):
    """Test removing connection entries."""
    print("Testing remove (connections)...")
    async with store.transaction() as session:
        await session.remove(category="connection", name="conn_3")
        removed_entry = await session.fetch(category="connection", name="conn_3")
        assert removed_entry is None, "conn_3 should be removed"


async def test_wql_exist_connections(store):
    """Test WQL $exist query for connections."""
    print("Testing WQL $exist query (connections)...")
    async with store.session() as session:
        all_entries = await session.fetch_all(category="connection")
        entries = [
            entry
            for entry in all_entries
            if "inbound_connection_id" in json.loads(entry.value)
        ]
        print(f"Found {len(entries)} connections with 'inbound_connection_id'")
        assert len(entries) == 3, "Expected 3 connections with 'inbound_connection_id'"
        for entry in entries:
            assert "inbound_connection_id" in json.loads(entry.value), (
                "inbound_connection_id should exist"
            )


async def test_fetch_all(store):
    """Test fetching all entries (people category)."""
    print("Fetching all entries (people)...")
    async with store.session() as session:
        entries = await session.fetch_all(category="people")
        print(f"Found {len(entries)} people")
        assert len(entries) == 4, "Expected 4 entries after replace"


async def test_remove_all_people(store):
    """Test removing all people entries."""
    print("Removing all people entries...")
    async with store.transaction() as session:
        deleted_count = await session.remove_all(category="people")
        print(f"Deleted {deleted_count} people entries")
        assert deleted_count == 4, "Expected to delete 4 entries"


async def test_remove_all_connections(store):
    """Test removing all connection entries."""
    print("Testing remove all connections...")
    async with store.transaction() as session:
        deleted_count = await session.remove_all(category="connection")
        print(f"Deleted {deleted_count} connection entries")
        assert deleted_count >= 3, "Expected to delete at least 3 entries"


async def test_non_encrypted():
    """Test provisioning and using a non-encrypted PostgreSQL database."""
    print("Provisioning non-encrypted PostgreSQL database...")
    non_enc_store = await DBStore.provision(
        uri=conn_str,
        key_method=None,
        pass_key=None,
        profile=profile_name,
        recreate=True,
        release_number="release_0_1",
        schema_config="normalize",
        config=config,
    )
    print(f"Non-encrypted database provisioned at {conn_str}")

    async with non_enc_store.transaction() as session:
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
        print(f"Inserted {count} people")

    tag_filter = json.dumps({"attr::person.status": "active"})
    scan = non_enc_store.scan(
        category="people", tag_filter=tag_filter, profile=profile_name
    )
    entries = [entry async for entry in scan]
    print(f"Found {len(entries)} active people in non-encrypted db")
    assert len(entries) == 1, "Expected 1 active person"

    await test_insert_connections(non_enc_store)
    await test_scan_connections(non_enc_store)
    await test_count_connections(non_enc_store)
    await test_replace_connections(non_enc_store)
    await test_remove_connections(non_enc_store)
    await test_wql_exist_connections(non_enc_store)

    await non_enc_store.close()


async def cleanup():
    """Clean up the PostgreSQL database."""
    print("Cleaning up PostgreSQL database...")
    await DBStore.remove(conn_str)
    print("Database removed")


async def main():
    """Main test function executing all test scenarios."""
    print("Starting PostgreSQL db_store.py test program...")
    store = await test_provision()
    await test_insert(store)
    await test_scan(store)
    await test_replace(store)
    await test_complex_filter(store)
    await test_insert_connections(store)
    await test_scan_connections(store)
    await test_count_connections(store)
    await test_replace_connections(store)
    await test_remove_connections(store)
    await test_wql_exist_connections(store)
    await test_fetch_all(store)
    await test_remove_all_people(store)
    await test_remove_all_connections(store)
    await test_non_encrypted()
    await cleanup()
    print("All tests passed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
