"""Tests for SQLite generic database functionality."""

# poetry run python \
# acapy_agent/database_manager/databases/sqlite_normalized/test/test_sqlite_generic.py

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


async def run_tests(store, db_path, is_encrypted=True):
    """Run database tests."""
    try:
        # Debug: Log current data state
        async with store.session() as session:
            entries = await session.fetch_all(category="people")
            parsed_entries = []
            for entry in entries:
                try:
                    value = json.loads(entry.value)
                    parsed_entries.append(f"{entry.name}: {entry.tags}, value={value}")
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON for {entry.name}: {entry.value}")
                    raise
            print(f"People before tests: {parsed_entries}")

        # Step 3: Test scan in database with offset and limit
        print("\n### Testing Scan in Database with Offset and Limit ###")
        tag_filter = json.dumps({"attr::person.status": "active"})
        expected_first_person = "person1" if is_encrypted else "person4"
        expected_second_person = "person3" if is_encrypted else "person6"
        scanned_entries = list(
            store.scan(
                profile="test_profile", category="people", tag_filter=tag_filter, limit=1
            )
        )
        print(f"Scanned with limit=1: {len(scanned_entries)} entries")
        assert len(scanned_entries) == 1, "Expected 1 entry with limit=1"
        assert scanned_entries[0].name == expected_first_person, (
            f"Expected {expected_first_person}, got {scanned_entries[0].name}"
        )
        try:
            value = json.loads(scanned_entries[0].value)
            print(f" - {scanned_entries[0].name}: {value}")
        except json.JSONDecodeError:
            print(
                f"Failed to parse JSON for {scanned_entries[0].name}: "
                f"{scanned_entries[0].value}"
            )
            raise

        scanned_entries = list(
            store.scan(
                profile="test_profile", category="people", tag_filter=tag_filter, offset=1
            )
        )
        print(f"Scanned with offset=1: {len(scanned_entries)} entries")
        assert len(scanned_entries) == 1, "Expected 1 entry with offset=1"
        assert scanned_entries[0].name == expected_second_person, (
            f"Expected {expected_second_person}, got {scanned_entries[0].name}"
        )
        try:
            value = json.loads(scanned_entries[0].value)
            print(f" - {scanned_entries[0].name}: {value}")
        except json.JSONDecodeError:
            print(
                f"Failed to parse JSON for {scanned_entries[0].name}: "
                f"{scanned_entries[0].value}"
            )
            raise

        scanned_entries = list(
            store.scan(
                profile="test_profile",
                category="people",
                tag_filter=tag_filter,
                offset=0,
                limit=2,
            )
        )
        print(f"Scanned with offset=0, limit=2: {len(scanned_entries)} entries")
        assert len(scanned_entries) == 2, "Expected 2 entries with offset=0, limit=2"
        assert (
            scanned_entries[0].name == expected_first_person
            and scanned_entries[1].name == expected_second_person
        ), f"Expected {expected_first_person} and {expected_second_person}"
        for entry in scanned_entries:
            try:
                value = json.loads(entry.value)
                print(f" - {entry.name}: {value}")
            except json.JSONDecodeError:
                print(f"Failed to parse JSON for {entry.name}: {entry.value}")
                raise

        scanned_entries = list(
            store.scan(
                profile="test_profile",
                category="people",
                tag_filter=tag_filter,
                offset=1,
                limit=1,
            )
        )
        print(f"Scanned with offset=1, limit=1: {len(scanned_entries)} entries")
        assert len(scanned_entries) == 1, "Expected 1 entry with offset=1, limit=1"
        assert scanned_entries[0].name == expected_second_person, (
            f"Expected {expected_second_person}, got {scanned_entries[0].name}"
        )
        try:
            value = json.loads(scanned_entries[0].value)
            print(f" - {scanned_entries[0].name}: {value}")
        except json.JSONDecodeError:
            print(
                f"Failed to parse JSON for {scanned_entries[0].name}: "
                f"{scanned_entries[0].value}"
            )
            raise

        scanned_entries = list(
            store.scan(
                profile="test_profile", category="people", tag_filter=tag_filter, offset=2
            )
        )
        print(f"Scanned with offset=2: {len(scanned_entries)} entries")
        assert len(scanned_entries) == 0, "Expected 0 entries with offset=2"

        # Step 4: Test replace in database
        print("\n### Testing Replace in Database ###")
        async with store.transaction() as session:
            print(f"Updating {'Alice' if is_encrypted else 'David'}...")
            await session.replace(
                category="people",
                name="person1" if is_encrypted else "person4",
                value=json.dumps(
                    {"name": "Alice Updated" if is_encrypted else "David Updated"}
                ),
                tags={
                    "attr::person.gender": "F" if is_encrypted else "M",
                    "attr::person.status": "inactive",
                    "attr::person.birthdate::value": "19950615"
                    if is_encrypted
                    else "19800101",
                },
            )
            updated_entry = await session.fetch(
                category="people",
                name="person1" if is_encrypted else "person4",
            )
            try:
                value = json.loads(updated_entry.value)
                print(
                    f"Updated {'Alice' if is_encrypted else 'David'}: "
                    f"{updated_entry.name}, value={value}"
                )
            except json.JSONDecodeError:
                print(
                    f"Failed to parse JSON for {updated_entry.name}: "
                    f"{updated_entry.value}"
                )
                raise
            expected_value = json.dumps(
                {"name": "Alice Updated" if is_encrypted else "David Updated"}
            )
            assert updated_entry.value == expected_value, "Value not updated"
            assert updated_entry.tags["attr::person.status"] == "inactive", (
                "Tag not updated"
            )
            assert updated_entry.tags["attr::person.birthdate::value"] == (
                "19950615" if is_encrypted else "19800101"
            ), "Birthdate tag not updated"

            print(f"Inserting {'David' if is_encrypted else 'Grace'}...")
            await session.insert(
                category="people",
                name="person4" if is_encrypted else "person7",
                value=json.dumps({"name": "David" if is_encrypted else "Grace"}),
                tags={
                    "attr::person.gender": "M" if is_encrypted else "F",
                    "attr::person.status": "active" if is_encrypted else "inactive",
                    "attr::person.birthdate::value": "19800101"
                    if is_encrypted
                    else "20010101",
                },
            )
            new_entry = await session.fetch(
                category="people",
                name="person4" if is_encrypted else "person7",
            )
            try:
                value = json.loads(new_entry.value)
                print(
                    f"Inserted {'David' if is_encrypted else 'Grace'}: "
                    f"{new_entry.name}, value={value}"
                )
            except json.JSONDecodeError:
                print(f"Failed to parse JSON for {new_entry.name}: {new_entry.value}")
                raise
            assert new_entry is not None, "Insert failed"

            print(f"Updating {'David' if is_encrypted else 'Grace'}...")
            await session.replace(
                category="people",
                name="person4" if is_encrypted else "person7",
                value=json.dumps(
                    {"name": "David Updated" if is_encrypted else "Grace Updated"}
                ),
                tags={
                    "attr::person.gender": "M" if is_encrypted else "F",
                    "attr::person.status": "inactive",
                    "attr::person.birthdate::value": "19800101"
                    if is_encrypted
                    else "20010101",
                },
            )
            updated_entry = await session.fetch(
                category="people",
                name="person4" if is_encrypted else "person7",
            )
            try:
                value = json.loads(updated_entry.value)
                print(
                    f"Updated {'David' if is_encrypted else 'Grace'}: "
                    f"{updated_entry.name}, value={value}"
                )
            except json.JSONDecodeError:
                print(
                    f"Failed to parse JSON for {updated_entry.name}: "
                    f"{updated_entry.value}"
                )
                raise
            expected_value = json.dumps(
                {"name": "David Updated" if is_encrypted else "Grace Updated"}
            )
            assert updated_entry.value == expected_value, "Value not updated"
            assert updated_entry.tags["attr::person.status"] == "inactive", (
                "Tag not updated"
            )
            assert updated_entry.tags["attr::person.birthdate::value"] == (
                "19800101" if is_encrypted else "20010101"
            ), "Birthdate tag not updated"

            # Debug: Log data state after updates
            entries = await session.fetch_all(category="people")
            parsed_entries = []
            for entry in entries:
                try:
                    value = json.loads(entry.value)
                    parsed_entries.append(f"{entry.name}: {entry.tags}, value={value}")
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON for {entry.name}: {entry.value}")
                    raise
            print(f"People after Step 4 updates: {parsed_entries}")

        # Step 5: Test remove_all with tag_filter
        print("\n### Testing Remove_all with tag_filter ###")
        async with store.transaction() as session:
            print("Removing inactive people born after 2000...")
            remove_filter = json.dumps(
                {
                    "$and": [
                        {"attr::person.status": "inactive"},
                        {"attr::person.birthdate::value": {"$gt": "20000101"}},
                    ]
                }
            )
            entries = await session.fetch_all(category="people", tag_filter=remove_filter)
            parsed_entries = []
            for entry in entries:
                try:
                    value = json.loads(entry.value)
                    parsed_entries.append(f"{entry.name}: {entry.tags}, value={value}")
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON for {entry.name}: {entry.value}")
                    raise
            print(f"Entries to delete in Step 5: {parsed_entries}")
            deleted_count = await session.remove_all(
                category="people", tag_filter=remove_filter
            )
            print(f"Deleted {deleted_count} inactive people born after 2000")
            assert deleted_count == (1 if is_encrypted else 2), (
                f"Expected to delete {1 if is_encrypted else 2} person "
                f"(Bob if encrypted; Eve, Grace if non-encrypted), "
                f"got {deleted_count}"
            )
            entries = await session.fetch_all(category="people")
            parsed_entries = []
            for entry in entries:
                try:
                    value = json.loads(entry.value)
                    parsed_entries.append(f"{entry.name}: {entry.tags}, value={value}")
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON for {entry.name}: {entry.value}")
                    raise
            print(f"People after Step 5 deletion: {parsed_entries}")

        # Step 6: Work with data
        print("\n### Working with Data ###")
        print(
            f"Using the database with {'new_secure_key' if is_encrypted else 'no key'}..."
        )
        async with store.session() as session:
            entries = await session.fetch_all(category="people")
            parsed_entries = []
            for entry in entries:
                try:
                    value = json.loads(entry.value)
                    parsed_entries.append(f"{entry.name}: {entry.tags}, value={value}")
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON for {entry.name}: {entry.value}")
                    raise
            print(f"Found {len(entries)} people: {parsed_entries}")
            assert len(entries) == (3 if is_encrypted else 2), (
                f"Expected {3 if is_encrypted else 2} people after deletion"
            )

        # Step 7: Test credential category with complex WQL query
        print("\n### Testing Credential Category with Complex WQL Query ###")
        async with store.transaction() as session:
            print("Inserting test credential...")
            await session.insert(
                category="credential",
                name="cred1",
                value=json.dumps({"id": "cred1"}),
                tags={
                    "attr::person.name.family::value": "DOE22sss",
                    "attr::person.name.given::value": "John111",
                    "attr::person.birthDate::value": "19501011",
                },
                expiry_ms=3600000,
            )
            print("Test credential inserted successfully!")

            wql_query = json.dumps(
                {
                    "$and": [
                        {
                            "$or": [
                                {"attr::person.name.family::value": {"$like": "%DOE%"}},
                                {"attr::person.name.given::value": "John111"},
                            ]
                        },
                        {"$not": {"attr::person.birthDate::value": {"$lt": "19400101"}}},
                        {
                            "attr::person.name.family::value": {
                                "$in": ["DOE22sss", "SMITH", "JOHNSON"]
                            }
                        },
                        {"$exist": ["attr::person.birthDate::value"]},
                        {
                            "$and": [
                                {"attr::person.name.given::value": {"$like": "John%"}},
                                {"$not": {"attr::person.name.family::value": "SMITH"}},
                            ]
                        },
                    ]
                }
            )
            print(f"Testing WQL query: {wql_query}")
            scanned_entries = await session.fetch_all(
                category="credential", tag_filter=wql_query, limit=10
            )
            print(f"Scanned {len(scanned_entries)} credentials")
            assert len(scanned_entries) == 1, "Expected 1 credential"
            assert scanned_entries[0].name == "cred1", "Expected cred1"
            try:
                value = json.loads(scanned_entries[0].value)
                print(f" - {scanned_entries[0].name}: {value}")
            except json.JSONDecodeError:
                print(
                    f"Failed to parse JSON for {scanned_entries[0].name}: "
                    f"{scanned_entries[0].value}"
                )
                raise

        # Step 8: Clean up
        print("\n### Cleaning Up ###")
        print("Removing all people and credentials from the database...")
        async with store.transaction() as session:
            deleted_count_people = await session.remove_all(category="people")
            deleted_count_credentials = await session.remove_all(category="credential")
            print(
                f"Wiped out {deleted_count_people} people and "
                f"{deleted_count_credentials} credentials!"
            )
            assert deleted_count_people == (3 if is_encrypted else 2), (
                f"Expected to delete {3 if is_encrypted else 2} people after deletion"
            )
            assert deleted_count_credentials == 1, "Expected to delete 1 credential"

    except Exception as e:
        LOGGER.error(f"Error in run_tests: {str(e)}")
        raise


async def main():
    """Main function to run SQLite database tests."""
    register_backends()
    print("Starting the SQLite database test program")
    store = None
    non_enc_store = None
    store_old = None
    store_wrong = None
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
            schema_config="generic",
        )
        try:
            pool, profile_name, path, effective_release_number = config.provision(
                profile="test_profile", recreate=True, release_number="release_0"
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

        # Step 2: Add some test people to the database
        print("\n### Adding People to the Database ###")
        async with store.transaction() as session:
            print("Adding Alice...")
            await session.insert(
                category="people",
                name="person1",
                value=json.dumps({"name": "Alice"}),
                tags={
                    "attr::person.gender": "F",
                    "attr::person.birthdate::value": "19950615",
                    "attr::person.status": "active",
                },
                expiry_ms=3600000,
            )
            print("Adding Bob...")
            await session.insert(
                category="people",
                name="person2",
                value=json.dumps({"name": "Bob"}),
                tags={
                    "attr::person.gender": "M",
                    "attr::person.birthdate::value": "20050620",
                    "attr::person.status": "inactive",
                },
                expiry_ms=3600000,
            )
            print("Adding Charlie...")
            await session.insert(
                category="people",
                name="person3",
                value=json.dumps({"name": "Charlie"}),
                tags={
                    "attr::person.gender": "F",
                    "attr::person.birthdate::value": "19900101",
                    "attr::person.status": "active",
                },
                expiry_ms=3600000,
            )
            print("All three people added successfully!")

        # Run initial tests
        await run_tests(store, db_path, is_encrypted=True)

        # Step 5: Change the encryption key
        print("\n### Changing the Encryption Key ###")
        print("Switching from 'strong_key' to 'new_secure_key'...")
        try:
            LOGGER.debug(f"Store before rekeying: {store}")
            await store.rekey(pass_key="new_secure_key")
            print("Database rekeyed successfully.")
            LOGGER.debug(f"Store after rekeying: {store}")

            # Reopen with new key to verify
            config_new = SqliteConfig(
                uri=f"sqlite://{db_path}",
                encryption_key="new_secure_key",
                pool_size=5,
                schema_config="generic",
            )
            pool, profile_name, path, effective_release_number = config_new.provision(
                profile="test_profile", recreate=False, release_number="release_0"
            )
            store = SqliteDatabase(pool, profile_name, path, effective_release_number)
            LOGGER.debug("Database reopened with new key 'new_secure_key': %s", store)
            print("Database reopened with new key 'new_secure_key'.")
        except Exception as e:
            LOGGER.error(f"Key change failed: {str(e)}")
            print(f"Key change failed: {e}")
            exit(1)

        # Step 6: Check if the new key works
        print("\n### Testing the New Key ###")
        print("Trying to reopen the database with 'new_secure_key'...")
        try:
            async with store.session() as session:
                count = await session.count(category="people")
                print(f"Counted {count} people with new key")
            print("Success! The new key works perfectly.")
        except Exception as e:
            print(f"Uh-oh! New key didn’t work: {e}")
            exit(1)

        # Step 7: Ensure the old key fails
        print("\n### Testing the Old Key ###")
        print("Attempting to open with the old key 'strong_key' (should fail)...")
        config_old = SqliteConfig(
            uri=f"sqlite://{db_path}",
            encryption_key="strong_key",
            pool_size=5,
            schema_config="generic",
        )
        try:
            pool, profile_name, path, effective_release_number = config_old.provision(
                profile="test_profile", recreate=False, release_number="release_0"
            )
            store_old = SqliteDatabase(pool, profile_name, path, effective_release_number)
            print("Error: The old key worked when it shouldn’t have!")
            await store_old.close()
            exit(1)
        except Exception as e:
            print(f"Good! Old key failed as expected: {e}")

        # Step 8: Re-run tests with new key
        print("\n### Restarting Tests with New Key ###")
        async with store.transaction() as session:
            print("Clearing existing people data...")
            deleted_count = await session.remove_all(category="people")
            print(f"Deleted {deleted_count} existing people entries")
            print("Re-adding test data for new key tests...")
            await session.insert(
                category="people",
                name="person1",
                value=json.dumps({"name": "Alice"}),
                tags={
                    "attr::person.gender": "F",
                    "attr::person.birthdate::value": "19950615",
                    "attr::person.status": "active",
                },
                expiry_ms=3600000,
            )
            await session.insert(
                category="people",
                name="person2",
                value=json.dumps({"name": "Bob"}),
                tags={
                    "attr::person.gender": "M",
                    "attr::person.birthdate::value": "20050620",
                    "attr::person.status": "inactive",
                },
                expiry_ms=3600000,
            )
            await session.insert(
                category="people",
                name="person3",
                value=json.dumps({"name": "Charlie"}),
                tags={
                    "attr::person.gender": "F",
                    "attr::person.birthdate::value": "19900101",
                    "attr::person.status": "active",
                },
                expiry_ms=3600000,
            )
            print("Test data re-added successfully!")
        await run_tests(store, db_path, is_encrypted=True)

        # Step 9: Test security with a wrong key
        print("\n### Testing Security ###")
        print("Trying a wrong key 'wrong_key' (should fail)...")
        config_wrong = SqliteConfig(
            uri=f"sqlite://{db_path}",
            encryption_key="wrong_key",
            pool_size=5,
            schema_config="generic",
        )
        try:
            pool, profile_name, path, effective_release_number = config_wrong.provision(
                profile="test_profile", recreate=False, release_number="release_0"
            )
            store_wrong = SqliteDatabase(
                pool, profile_name, path, effective_release_number
            )
            print("Error: Wrong key worked when it shouldn’t have!")
            await store_wrong.close()
            exit(1)
        except Exception as e:
            print(f"Perfect! Wrong key failed as expected: {e}")

        # Step 10: Test Non-Encrypted Database
        print("\n=======================================")
        print("=== Testing Non-Encrypted Database ===")
        print("=======================================")
        non_enc_db_path = "test_non_enc.db"
        if os.path.dirname(non_enc_db_path):
            os.makedirs(os.path.dirname(non_enc_db_path), exist_ok=True)
        print(f"Provisioning non-encrypted database at {non_enc_db_path}...")
        non_enc_config = SqliteConfig(
            uri=f"sqlite://{non_enc_db_path}",
            encryption_key=None,
            pool_size=5,
            schema_config="generic",
        )
        try:
            pool, profile_name, path, effective_release_number = non_enc_config.provision(
                profile="test_profile", recreate=True, release_number="release_0"
            )
            non_enc_store = SqliteDatabase(
                pool, profile_name, path, effective_release_number
            )
            print(
                f"Non-encrypted database ready! Profile name: "
                f"{await non_enc_store.get_profile_name()}"
            )
        except Exception as e:
            print(f"Oops! Failed to set up the non-encrypted database: {e}")
            exit(1)

        print("\nAdding people to the non-encrypted database...")
        async with non_enc_store.transaction() as session:
            await session.insert(
                category="people",
                name="person4",
                value=json.dumps({"name": "David"}),
                tags={
                    "attr::person.gender": "M",
                    "attr::person.birthdate::value": "19800101",
                    "attr::person.status": "active",
                },
                expiry_ms=3600000,
            )
            await session.insert(
                category="people",
                name="person5",
                value=json.dumps({"name": "Eve"}),
                tags={
                    "attr::person.gender": "F",
                    "attr::person.birthdate::value": "20010101",
                    "attr::person.status": "inactive",
                },
                expiry_ms=3600000,
            )
            await session.insert(
                category="people",
                name="person6",
                value=json.dumps({"name": "Frank"}),
                tags={
                    "attr::person.gender": "O",
                    "attr::person.birthdate::value": "19950101",
                    "attr::person.status": "active",
                },
                expiry_ms=3600000,
            )
            print("Test data added successfully!")

        await run_tests(non_enc_store, non_enc_db_path, is_encrypted=False)

        print("\nTrying to open non-encrypted database with a key (should fail)...")
        config_with_key = SqliteConfig(
            uri=f"sqlite://{non_enc_db_path}",
            encryption_key="some_key",
            pool_size=5,
            schema_config="generic",
        )
        try:
            pool, profile_name, path, effective_release_number = (
                config_with_key.provision(
                    profile="test_profile", recreate=False, release_number="release_0"
                )
            )
            store_with_key = SqliteDatabase(
                pool, profile_name, path, effective_release_number
            )
            print("Error: Opened non-encrypted database with a key!")
            await store_with_key.close()
            exit(1)
        except Exception as e:
            print(f"Correct! Failed to open with a key as expected: {e}")

        print("\n### All Done! ###")
        print("Tests completed successfully.")

    except Exception as e:
        LOGGER.error(f"Error in main: {str(e)}")
        raise
    finally:
        for db_store in [store, non_enc_store, store_old, store_wrong, store_with_key]:
            if (
                db_store is not None
                and hasattr(db_store, "pool")
                and db_store.pool is not None
            ):
                try:
                    # Check if pool has active connections before closing
                    if hasattr(db_store.pool, "_closed") and not db_store.pool._closed:
                        await db_store.close()
                        LOGGER.debug(f"Closed database store: {db_store}")
                    else:
                        LOGGER.debug(f"Skipping store {db_store}: Already closed")
                except Exception as close_err:
                    LOGGER.error(f"Error closing store {db_store}: {str(close_err)}")
            else:
                LOGGER.debug(f"Skipping store {db_store}: None or no pool")


if __name__ == "__main__":
    asyncio.run(main(), debug=True)
