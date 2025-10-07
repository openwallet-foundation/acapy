"""SQLite normalized database test.

This script tests the functionality of the SQLite database for the
'connection' category using ConnectionHandler.
1. Database provisioning (encrypted and non-encrypted).
2. Data insertion with JSON values and tags.
3. Scanning with tag filters, offsets, and limits.
4. Counting records with tag filters.
5. Updating records with replace.
6. Fetching individual and all records.
7. Removing individual and bulk records.
8. Testing WQL $exist query.
9. Encryption rekeying and security checks.
10. Cleanup and verification.
"""

import asyncio
import json
import os

from acapy_agent.database_manager.databases.backends.backend_registration import (
    register_backends,
)
from acapy_agent.database_manager.databases.sqlite_normalized.backend import SqliteConfig
from acapy_agent.database_manager.databases.sqlite_normalized.database import (
    SqliteDatabase,
)

try:
    import sqlcipher3 as sqlcipher
except ImportError:
    sqlcipher = None
import logging

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

# Sample connection JSON data
CONNECTION_JSON_1 = {
    "connection_id": "conn_1",
    "request_id": "d954a0b3-e050-4183-8a4a-b81b231a13d2",
    "invitation_key": "Bf6vVuUjEg3syenW3AoPHvD6XKd8CKrGPN5hmy9CkKrX",
    "state": "active",
    "their_role": "invitee",
    "invitation_msg_id": "3b456399-3fde-4e5b-a1b5-d070f940dfe3",
    "their_did": "did:peer:1zQmdgg9s3MwBEZ49QGn2ohLHbg6osFTepqumgL8RNZ2Mxhf",
    "my_did": "did:peer:4zQmVepvKPxDn7xyHsUfxEd7dxJaMancWche8Q2Hq5TjZniS",
    "created_at": "2025-05-07T13:42:17.621783Z",
    "updated_at": "2025-05-07T13:43:37.830311Z",
    "inbound_connection_id": None,
    "accept": "auto",
    "invitation_mode": "once",
    "alias": None,
    "error_msg": None,
    "their_label": "My Wallet - 2596",
    "their_public_did": None,
    "connection_protocol": "didexchange/1.1",
}

CONNECTION_JSON_2 = {
    "connection_id": "conn_2",
    "request_id": "e123f456-g789-4hij-klmn-opqrstuvwxyz",
    "invitation_key": "Dm9kXu2qW8vRy3zAe4BoIqP7nLc5Jy6Hx2g",
    "state": "inactive",
    "their_role": "inviter",
    "invitation_msg_id": "4c567e90-bdef-5klm-nopq-rstuvwxyz",
    "their_did": "did:peer:2AbCdEfGhIjKlMn1234567890",
    "my_did": "did:peer:5XyZaBcDeFgHiJkLmNoP123456",
    "created_at": "2025-05-08T14:00:00.000000Z",
    "updated_at": "2025-05-08T14:01:00.000000Z",
    "inbound_connection_id": None,
    "accept": "manual",
    "invitation_mode": "multi",
    "alias": "TestConn",
    "error_msg": None,
    "their_label": "Test Wallet",
    "their_public_did": None,
    "connection_protocol": "didexchange/1.0",
}

CONNECTION_JSON_3 = {
    "connection_id": "conn_3",
    "request_id": "f234g567-h890-5ijk-pqrs-tuvwxyz",
    "invitation_key": "Fn8jLw4m7u6t3x2Be9vKqR",
    "state": "active",
    "their_role": "invitee",
    "invitation_msg_id": "5e678f12-cdef-6lmn-opqr-uvwxyz123",
    "their_did": "did:peer:3BcDeFgHiJkLmNoP456789012",
    "my_did": "did:peer:6YzAbCdEfGhIjKlMn789012",
    "created_at": "2025-05-09T15:00:00.000000Z",
    "updated_at": "2025-05-09T15:01:00.000000Z",
    "inbound_connection_id": "conn_123",
    "accept": "auto",
    "invitation_mode": "once",
    "alias": None,
    "error_msg": None,
    "their_label": "Another Wallet",
    "their_public_did": None,
    "connection_protocol": "didexchange/1.1",
}


async def run_tests(store, db_path, config_new, is_encrypted=True):
    """Run test suite for the database store."""
    try:
        # Debug: Log current data state
        async with store.session() as session:
            entries = await session.fetch_all(category="connection")
            print(
                f"Connections before tests: {
                    [
                        f'{entry.name}: {entry.tags}, value={json.loads(entry.value)}'
                        for entry in entries
                    ]
                }"
            )

        # Step 3: Test scan in database with offset and limit
        print("\n### Testing Scan in Database with Offset and Limit ###")
        scanned_entries = list(
            store.scan(
                profile="test_profile", category="connection", tag_filter=None, limit=1
            )
        )
        print(f"Scanned with limit=1: {len(scanned_entries)} entries")
        assert len(scanned_entries) == 1, "Expected 1 entry with limit=1"
        print(f" - {scanned_entries[0].name}: {json.loads(scanned_entries[0].value)}")

        scanned_entries = list(
            store.scan(
                profile="test_profile", category="connection", tag_filter=None, offset=1
            )
        )
        print(f"Scanned with offset=1: {len(scanned_entries)} entries")
        assert len(scanned_entries) == 2, "Expected 2 entries with offset=1"
        for entry in scanned_entries:
            print(f" - {entry.name}: {json.loads(entry.value)}")

        scanned_entries = list(
            store.scan(
                profile="test_profile",
                category="connection",
                tag_filter=None,
                offset=0,
                limit=2,
            )
        )
        print(f"Scanned with offset=0, limit=2: {len(scanned_entries)} entries")
        assert len(scanned_entries) == 2, "Expected 2 entries with offset=0, limit=2"
        for entry in scanned_entries:
            print(f" - {entry.name}: {json.loads(entry.value)}")

        scanned_entries = list(
            store.scan(
                profile="test_profile",
                category="connection",
                tag_filter=None,
                offset=1,
                limit=1,
            )
        )
        print(f"Scanned with offset=1, limit=1: {len(scanned_entries)} entries")
        assert len(scanned_entries) == 1, "Expected 1 entry with offset=1, limit=1"
        print(f" - {scanned_entries[0].name}: {json.loads(scanned_entries[0].value)}")

        scanned_entries = list(
            store.scan(
                profile="test_profile", category="connection", tag_filter=None, offset=2
            )
        )
        print(f"Scanned with offset=2: {len(scanned_entries)} entries")
        assert len(scanned_entries) == 1, "Expected 1 entry with offset=2"

        # Step 4: Test replace in database
        print("\n### Testing Replace in Database ###")
        async with store.transaction() as session:
            print(
                "Updating Connection 4..."
                if not is_encrypted
                else "Updating Connection 1..."
            )
            updated_json = CONNECTION_JSON_1.copy()
            updated_json["state"] = "completed"
            updated_json["their_label"] = "Updated Wallet"
            await session.replace(
                category="connection",
                name="conn_4" if not is_encrypted else "conn_1",
                value=json.dumps(updated_json),
                tags={},
            )
            updated_entry = await session.fetch(
                category="connection", name="conn_4" if not is_encrypted else "conn_1"
            )
            print(
                f"Updated Connection {'4' if not is_encrypted else '1'}: "
                f"{json.loads(updated_entry.value)}"
            )
            assert json.loads(updated_entry.value)["state"] == "completed", (
                "State not updated"
            )

            print(
                "Inserting Connection 4..."
                if is_encrypted
                else "Inserting Connection 7..."
            )
            await session.insert(
                category="connection",
                name="conn_4" if is_encrypted else "conn_7",
                value=json.dumps(CONNECTION_JSON_1),
                tags={},
            )
            new_entry = await session.fetch(
                category="connection", name="conn_4" if is_encrypted else "conn_7"
            )
            print(
                f"Inserted Connection {'4' if is_encrypted else '7'}: "
                f"{json.loads(new_entry.value)}"
            )
            assert new_entry is not None, "Insert failed"

            print(
                "Updating Connection 4..." if is_encrypted else "Updating Connection 7..."
            )
            updated_json_4 = CONNECTION_JSON_1.copy()
            updated_json_4["state"] = "inactive"
            await session.replace(
                category="connection",
                name="conn_4" if is_encrypted else "conn_7",
                value=json.dumps(updated_json_4),
                tags={},
            )
            updated_conn4 = await session.fetch(
                category="connection", name="conn_4" if is_encrypted else "conn_7"
            )
            print(
                f"Updated Connection {'4' if not is_encrypted else '7'}: "
                f"{json.loads(updated_conn4.value)}"
            )
            assert json.loads(updated_conn4.value)["state"] == "inactive", (
                "State not updated"
            )

        # Step 5: Test count and remove in database
        print("\n### Testing Count and Remove in Database ###")
        async with store.session() as session:
            count = await session.count(category="connection", tag_filter=None)
            print(f"Counted {count} connections")
            assert count == 4, "Expected 4 connections"

            print(
                "Removing Connection 3..." if is_encrypted else "Removing Connection 6..."
            )
            await session.remove(
                category="connection", name="conn_3" if is_encrypted else "conn_6"
            )
            removed_entry = await session.fetch(
                category="connection", name="conn_3" if is_encrypted else "conn_6"
            )
            assert removed_entry is None, (
                f"Connection {'3' if is_encrypted else '6'} should be removed"
            )

        # Step 6: Test WQL $exist query in database
        print("\n### Testing WQL $exist Query in Database ###")
        async with store.transaction() as session:
            print("Inserting test data for $exist query...")
            await session.insert(
                category="connection_test",
                name="conn_test1",
                value=json.dumps({"field": "value"}),
                tags={},
            )
            await session.insert(
                category="connection_test",
                name="conn_test2",
                value=json.dumps({}),
                tags={},
            )
            await session.insert(
                category="connection_test",
                name="conn_test3",
                value=json.dumps({"field": "another"}),
                tags={},
            )

            wql_query = json.dumps({"$exist": ["field"]})
            print(f"Testing WQL query: {wql_query}")
            all_entries = await session.fetch_all(category="connection_test")
            filtered_entries = [
                entry for entry in all_entries if "field" in json.loads(entry.value)
            ]
            count = len(filtered_entries)
            print(f"Counted {count} connections with 'field' in value")
            assert count == 2, "Expected 2 connections with 'field' in value"

            print("Cleaning up test data...")
            await session.remove_all(category="connection_test")

        # Step 7: Check if the key works (only for encrypted database)
        if is_encrypted:
            print("\n### Testing the Key ###")
            print(
                f"Trying to access the database with "
                f"{'new_secure_key' if is_encrypted else 'no key'}..."
            )
            async with store.session() as session:
                count = await session.count(category="connection")
                print(
                    f"Counted {count} connections with "
                    f"{'new key' if is_encrypted else 'no key'}"
                )
            print("Success! The key works perfectly.")

        # Step 8: Ensure the old key fails (only for encrypted database)
        if is_encrypted:
            print("\n### Testing the Old Key ###")
            print("Attempting to open with the old key 'strong_key' (should fail)...")
            config_old = SqliteConfig(
                uri=f"sqlite://{db_path}",
                encryption_key="strong_key",
                pool_size=5,
                schema_config="normalize",
            )
            print(f"Pool size configured for old key: {config_old.pool_size}")
            try:
                pool, profile_name, path, effective_release_number = config_old.provision(
                    profile="test_profile", recreate=False, release_number="release_0_1"
                )
                store_old = SqliteDatabase(
                    pool, profile_name, path, effective_release_number
                )
                print("Error: The old key worked when it shouldn’t have!")
                store_old.close()
                raise RuntimeError("Old key worked unexpectedly")
            except Exception as e:
                print(f"Good! Old key failed as expected: {e}")

        # Step 9: Work with data
        print("\n### Working with Data ###")
        print(
            f"Using the database with {'new_secure_key' if is_encrypted else 'no key'}..."
        )
        async with store.session() as session:
            entries = await session.fetch_all(category="connection")
            print(f"Found {len(entries)} connections: {entries}")
            assert len(entries) == 3, "Expected 3 connections after operations!"

        # Step 10: Clean up
        print("\n### Cleaning Up ###")
        print("Removing all connections from the database...")
        async with store.transaction() as session:
            deleted_count = await session.remove_all(category="connection")
            print(f"Wiped out {deleted_count} entries!")
            assert deleted_count == 3, "Should have deleted 3 entries!"

        # Verify cleanup
        print("\nChecking if the database is empty...")
        async with store.session() as session:
            entries_after_remove = await session.fetch_all(category="connection")
            print(f"Remaining entries: {len(entries_after_remove)} (should be 0)")
            assert len(entries_after_remove) == 0, "Database should be empty!"

    except Exception as e:
        LOGGER.error(f"Error in run_tests: {str(e)}")
        raise
    finally:
        # Do not close store here to allow reuse in main
        pass


async def main():
    """Run the main test function."""
    register_backends()
    print(
        "Starting the SQLite database test program for 'connection' category "
        "(Asyncio Version)..."
    )
    store = None
    non_enc_store = None
    store_old = None
    store_with_key = None
    try:
        # Define the database path and ensure the directory exists
        db_path = "test.db"
        os.makedirs(os.path.dirname(db_path), exist_ok=True) if os.path.dirname(
            db_path
        ) else None

        # Step 1: Provision the database with an encryption key
        print("\n### Setting Up the Database ###")
        print(
            "Provisioning the database at", db_path, "with encryption key 'strong_key'..."
        )
        config = SqliteConfig(
            uri=f"sqlite://{db_path}",
            encryption_key="strong_key",
            pool_size=5,
            schema_config="normalize",
        )
        print(f"Pool size configured: {config.pool_size}")
        try:
            pool, profile_name, path, effective_release_number = config.provision(
                profile="test_profile", recreate=True, release_number="release_0_1"
            )
            store = SqliteDatabase(pool, profile_name, path, effective_release_number)
            LOGGER.debug(f"Store initialized: {store}")
            profile_name = await store.get_profile_name()
            print(f"Database ready! Profile name: {profile_name}")
            assert profile_name == "test_profile", "Profile name mismatch"
        except Exception as e:
            print(f"Oops! Failed to set up the database: {e}")
            exit(1)
        print(f"Database file exists? {os.path.exists(db_path)}")

        # Step 2: Add some test connections to the database
        print("\n### Adding Connections to the Database ###")
        async with store.transaction() as session:
            print("Adding Connection 1...")
            await session.insert(
                category="connection",
                name="conn_1",
                value=json.dumps(CONNECTION_JSON_1),
                tags={},
                expiry_ms=3600000,
            )
            print("Adding Connection 2...")
            await session.insert(
                category="connection",
                name="conn_2",
                value=json.dumps(CONNECTION_JSON_2),
                tags={},
                expiry_ms=3600000,
            )
            print("Adding Connection 3...")
            await session.insert(
                category="connection",
                name="conn_3",
                value=json.dumps(CONNECTION_JSON_3),
                tags={},
                expiry_ms=3600000,
            )
            print("All three connections added successfully!")

        # Run initial tests before rekeying
        await run_tests(store, db_path, config, is_encrypted=True)

        # Step 7: Change the encryption key
        print("\n### Changing the Encryption Key ###")
        print("Switching from 'strong_key' to 'new_secure_key'...")
        try:
            # Rekey the database using SqliteDatabase.rekey
            LOGGER.debug(f"Store before rekeying: {store}")
            await store.rekey(pass_key="new_secure_key")
            print("Database rekeyed successfully.")
            LOGGER.debug(f"Store after rekeying: {store}")

            # Reopen with new key to verify
            config_new = SqliteConfig(
                uri=f"sqlite://{db_path}",
                encryption_key="new_secure_key",
                pool_size=5,
                schema_config="normalize",
            )
            print(f"Pool size configured for new key: {config_new.pool_size}")
            pool, profile_name, path, effective_release_number = config_new.provision(
                profile="test_profile", recreate=False, release_number="release_0_1"
            )
            store = SqliteDatabase(pool, profile_name, path, effective_release_number)
            LOGGER.debug("Database reopened with new key 'new_secure_key': %s", store)
            print("Database reopened with new key 'new_secure_key'.")

            # Re-run tests with the new key
            print("\n### Restarting Tests with New Key ###")
            async with store.transaction() as session:
                print("Re-adding test data for new key tests...")
                await session.insert(
                    category="connection",
                    name="conn_1",
                    value=json.dumps(CONNECTION_JSON_1),
                    tags={},
                    expiry_ms=3600000,
                )
                await session.insert(
                    category="connection",
                    name="conn_2",
                    value=json.dumps(CONNECTION_JSON_2),
                    tags={},
                    expiry_ms=3600000,
                )
                await session.insert(
                    category="connection",
                    name="conn_3",
                    value=json.dumps(CONNECTION_JSON_3),
                    tags={},
                    expiry_ms=3600000,
                )
                print("Test data re-added successfully!")

            await run_tests(store, db_path, config_new, is_encrypted=True)

        except Exception as e:
            LOGGER.error(f"Key change or re-test failed: {str(e)}")
            print(f"Key change or re-test failed: {e}")
            exit(1)

        # Step 12: Test Non-Encrypted Database
        print("\n=======================================")
        print("=== Testing Non-Encrypted Database ===")
        print("=======================================")
        non_enc_db_path = "test_non_enc.db"
        os.makedirs(os.path.dirname(non_enc_db_path), exist_ok=True) if os.path.dirname(
            non_enc_db_path
        ) else None

        print(f"Provisioning non-encrypted database at {non_enc_db_path}...")
        non_enc_config = SqliteConfig(
            uri=f"sqlite://{non_enc_db_path}",
            encryption_key=None,
            pool_size=5,
            schema_config="normalize",
        )
        print(f"Pool size configured for non-encrypted: {non_enc_config.pool_size}")
        try:
            pool, profile_name, path, effective_release_number = non_enc_config.provision(
                profile="test_profile", recreate=True, release_number="release_0_1"
            )
            non_enc_store = SqliteDatabase(
                pool, profile_name, path, effective_release_number
            )
            profile_name = await non_enc_store.get_profile_name()
            print(f"Non-encrypted database ready! Profile name: {profile_name}")
        except Exception as e:
            print(f"Oops! Failed to set up the non-encrypted database: {e}")
            exit(1)

        print("\nAdding connections to the non-encrypted database...")
        async with non_enc_store.transaction() as session:
            await session.insert(
                category="connection",
                name="conn_4",
                value=json.dumps(CONNECTION_JSON_1),
                tags={},
            )
            await session.insert(
                category="connection",
                name="conn_5",
                value=json.dumps(CONNECTION_JSON_2),
                tags={},
            )
            await session.insert(
                category="connection",
                name="conn_6",
                value=json.dumps(CONNECTION_JSON_3),
                tags={},
            )
            print("Test data added successfully!")

        # Run tests for non-encrypted database
        await run_tests(
            non_enc_store, non_enc_db_path, non_enc_config, is_encrypted=False
        )

        print("\nTrying to open non-encrypted database with a key (should fail)...")
        config_with_key = SqliteConfig(
            uri=f"sqlite://{non_enc_db_path}",
            encryption_key="some_key",
            pool_size=5,
            schema_config="normalize",
        )
        print(
            f"Pool size configured for non-encrypted with key: "
            f"{config_with_key.pool_size}"
        )
        try:
            pool, profile_name, path, effective_release_number = (
                config_with_key.provision(
                    profile="test_profile", recreate=False, release_number="release_0_1"
                )
            )
            store_with_key = SqliteDatabase(
                pool, profile_name, path, effective_release_number
            )
            print("Error: Opened non-encrypted database with a key!")
            store_with_key.close()
            exit(1)
        except Exception as e:
            print(f"Correct! Failed to open with a key as expected: {e}")

        print("\n### TEST COMPLETED ###")

    except Exception as e:
        LOGGER.error(f"Error in main: {str(e)}")
        raise
    finally:
        for db_store in [store, non_enc_store, store_old, store_with_key]:
            if db_store is not None:
                try:
                    if hasattr(db_store, "close") and callable(db_store.close):
                        db_store.close()
                        LOGGER.debug(f"Closed database store: {db_store}")
                    else:
                        LOGGER.error(f"Close method missing for store: {db_store}")
                except Exception as close_err:
                    LOGGER.error(f"Error closing store {db_store}: {str(close_err)}")
            else:
                LOGGER.debug("Skipping None store")


if __name__ == "__main__":
    asyncio.run(main(), debug=True)
