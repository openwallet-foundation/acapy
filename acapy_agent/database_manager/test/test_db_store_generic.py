# poetry run python acapy_agent/database_manager/test/test_db_store_generic.py


import asyncio
import os
import json
import logging
from acapy_agent.database_manager.dbstore import DBStore

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

# Define the database path and ensure the directory exists
db_path = "test_dbstore.db"
os.makedirs(os.path.dirname(db_path), exist_ok=True) if os.path.dirname(db_path) else None
uri = f"sqlite://{db_path}"

# Define the non-encrypted database path
non_enc_db_path = "test_dbstore_no_enc.db"
os.makedirs(os.path.dirname(non_enc_db_path), exist_ok=True) if os.path.dirname(
    non_enc_db_path
) else None
non_enc_uri = f"sqlite://{non_enc_db_path}"

profile_name = "test_profile"


async def test_provision():
    """Test provisioning an encrypted database."""
    print("Provisioning the encrypted database...")
    store = await DBStore.provision(
        uri=uri,
        pass_key="Strong_key",
        profile=profile_name,
        recreate=True,
        release_number="release_0",
        schema_config="generic",
    )
    print(f"Database provisioned at {db_path}")
    assert os.path.exists(db_path), "Database file not created"
    return store


async def test_insert(store):
    """Test inserting test data into the database."""
    print("Inserting test data...")
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
    """Test scanning with tag filter as dictionary and pagination."""
    print("Testing scan with tag filter as dictionary...")
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

    print("Testing scan with limit and offset...")
    scan_paginated = store.scan(
        category="people", tag_filter=tag_filter, limit=1, offset=1, profile=profile_name
    )
    paginated_entries = [entry async for entry in scan_paginated]
    print(f"Found {len(paginated_entries)} entries with limit=1, offset=1")
    assert len(paginated_entries) == 1, "Expected 1 entry"


async def test_replace(store):
    """Test replacing existing entries."""
    print("Testing replace...")
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
    """Test scanning with a complex tag filter."""
    print("Testing complex filter...")
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
        try:
            value = json.loads(entry.value)
            print(f" - {entry.name}: {value}")
        except json.JSONDecodeError:
            print(f"Failed to parse JSON for {entry.name}: {entry.value}")
            raise


async def test_rekey(store):
    """Test rekeying the database."""
    print("Rekeying the database...")
    await store.rekey(pass_key="new_secure_key")
    print("Rekey successful")


async def test_open_with_new_key():
    """Test opening with the new key."""
    print("Opening with new key...")
    store_new = await DBStore.open(
        uri=uri, pass_key="new_secure_key", profile=profile_name
    )
    print("Opened successfully with new key")
    return store_new


async def test_open_with_old_key():
    """Test that the old key fails after rekeying."""
    print("Trying to open with old key...")
    try:
        await DBStore.open(uri=uri, pass_key="Strong_key", profile=profile_name)
        assert False, "Should not open with old key"
    except Exception as e:
        print(f"Correctly failed to open with old key: {e}")


async def test_fetch_all(store):
    """Test fetching all entries."""
    print("Fetching all entries...")
    async with store.session() as session:
        entries = await session.fetch_all(category="people")
        print(f"Found {len(entries)} entries")
        assert len(entries) == 4, "Expected 4 entries after replace"


async def test_remove_all(store):
    """Test removing all entries."""
    print("Removing all entries...")
    async with store.transaction() as session:
        deleted_count = await session.remove_all(category="people")
        print(f"Deleted {deleted_count} entries")
        assert deleted_count == 4, "Expected to delete 4 entries"
    await store.close()


async def test_open_with_wrong_key():
    """Test that a wrong key fails to open the database."""
    print("Trying to open with wrong key...")
    try:
        await DBStore.open(uri=uri, pass_key="wrong_key", profile=profile_name)
        assert False, "Should not open with wrong key"
    except Exception as e:
        print(f"Correctly failed to open with wrong key: {e}")


async def test_non_encrypted():
    """Test provisioning and using a non-encrypted database."""
    print("Provisioning non-encrypted database...")
    non_enc_store = await DBStore.provision(
        uri=non_enc_uri,
        pass_key=None,
        profile=profile_name,
        recreate=True,
        release_number="release_0",
        schema_config="generic",
    )
    print(f"Non-encrypted database provisioned at {non_enc_db_path}")

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

    await non_enc_store.close()
    print("Trying to open non-encrypted db with a key...")
    try:
        await DBStore.open(uri=non_enc_uri, pass_key="some_key", profile=profile_name)
        assert False, "Should not open non-encrypted db with a key"
    except Exception as e:
        print(f"Correctly failed to open non-encrypted db with a key: {e}")


async def cleanup():
    """Clean up database files."""
    print("Cleaning up database files...")
    await DBStore.remove(uri)
    await DBStore.remove(non_enc_uri)
    print("Database files removed")


async def main():
    """Main test function executing all test scenarios."""
    print("Starting db_store.py test program...")
    store = await test_provision()
    await test_insert(store)
    await test_scan(store)
    await test_replace(store)
    await test_complex_filter(store)
    await test_rekey(store)
    store_new = await test_open_with_new_key()
    await test_fetch_all(store_new)
    await test_remove_all(store_new)
    await test_open_with_old_key()
    await test_open_with_wrong_key()
    await test_non_encrypted()
    await cleanup()
    print("All tests passed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
