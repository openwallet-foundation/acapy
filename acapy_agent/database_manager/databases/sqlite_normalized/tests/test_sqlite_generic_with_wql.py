"""Tests for SQLite generic database with WQL support."""

# poetry run python \
# acapy_agent/database_manager/databases/sqlite_normalized/test/\
# test_sqlite_generic_with_wql.py
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
    """Run database tests with WQL."""
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

        # Step 3: Test scan in database with offset, limit, and complex WQL
        print("\n### Testing Scan in Database with Offset, Limit, and Complex WQL ###")
        tag_filter = json.dumps({"attr::person.status": "active"})
        expected_first_person = "person1" if is_encrypted else "person4"
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

        # Test scan with complex WQL: Active females
        print("\nTesting scan with complex WQL (active females)...")
        complex_scan_filter = json.dumps(
            {"$and": [{"attr::person.status": "active"}, {"attr::person.gender": "F"}]}
        )
        scanned_entries_complex = list(
            store.scan(
                profile="test_profile",
                category="people",
                tag_filter=complex_scan_filter,
                limit=2,
            )
        )
        print(f"Scanned with limit=2: {len(scanned_entries_complex)} entries")
        assert len(scanned_entries_complex) == (2 if is_encrypted else 0), (
            f"Expected {2 if is_encrypted else 0} active females "
            f"(Alice, Charlie if encrypted; none if non-encrypted)"
        )
        for entry in scanned_entries_complex:
            try:
                value = json.loads(entry.value)
                print(f" - {entry.name}: {value}")
            except json.JSONDecodeError:
                print(f"Failed to parse JSON for {entry.name}: {entry.value}")
                raise

        # Test scan with complex WQL: Not male
        print("\nTesting scan with complex WQL (not male)...")
        not_male_filter = json.dumps({"attr::person.gender": {"$neq": "M"}})
        scanned_entries_not_male = list(
            store.scan(
                profile="test_profile", category="people", tag_filter=not_male_filter
            )
        )
        print(f"Scanned not male: {len(scanned_entries_not_male)} entries")
        assert len(scanned_entries_not_male) == 2, (
            "Expected 2 not male "
            "(Alice, Charlie if encrypted; Eve, Frank if non-encrypted)"
        )
        for entry in scanned_entries_not_male:
            try:
                value = json.loads(entry.value)
                print(f" - {entry.name}: {value}")
            except json.JSONDecodeError:
                print(f"Failed to parse JSON for {entry.name}: {entry.value}")
                raise

        # Step 4: Test fetch with tag_filter
        print("\n### Testing Fetch with tag_filter ###")
        async with store.session() as session:
            # Test fetch with matching tag_filter
            print(f"Fetching {expected_first_person} with status='active'...")
            entry = await session.fetch(
                category="people",
                name=expected_first_person,
                tag_filter=json.dumps({"attr::person.status": "active"}),
            )
            assert entry is not None, (
                f"Should fetch {expected_first_person} with status='active'"
            )
            try:
                value = json.loads(entry.value)
                print(
                    f"Fetched: {entry.name} with "
                    f"status={entry.tags['attr::person.status']}, value={value}"
                )
            except json.JSONDecodeError:
                print(f"Failed to parse JSON for {entry.name}: {entry.value}")
                raise

            # Test fetch with non-matching tag_filter
            print(f"Fetching {expected_first_person} with status='inactive'...")
            entry = await session.fetch(
                category="people",
                name=expected_first_person,
                tag_filter=json.dumps({"attr::person.status": "inactive"}),
            )
            assert entry is None, (
                f"Should not fetch {expected_first_person} with status='inactive'"
            )

            # Test fetch with complex WQL: Active and female
            print(
                f"Fetching {'person1' if is_encrypted else 'person5'} "
                f"with status='active' and gender='F'..."
            )
            complex_filter = json.dumps(
                {
                    "$and": [
                        {"attr::person.status": "active"},
                        {"attr::person.gender": "F"},
                    ]
                }
            )
            entry = await session.fetch(
                category="people",
                name="person1" if is_encrypted else "person5",
                tag_filter=complex_filter,
            )
            assert entry is not None if is_encrypted else entry is None, (
                f"Should {'fetch Alice' if is_encrypted else 'not fetch Eve'} "
                f"with status='active' and gender='F'"
            )
            if entry:
                try:
                    value = json.loads(entry.value)
                    print(
                        f"Fetched: {entry.name} with "
                        f"status={entry.tags['attr::person.status']} and "
                        f"gender={entry.tags['attr::person.gender']}, value={value}"
                    )
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON for {entry.name}: {entry.value}")
                    raise

        # Step 5: Test fetch_all with tag_filter
        print("\n### Testing Fetch_all with tag_filter ###")
        async with store.session() as session:
            # Test fetch_all with complex WQL: Active females
            print("Fetching all active females...")
            active_females_filter = json.dumps(
                {
                    "$and": [
                        {"attr::person.status": "active"},
                        {"attr::person.gender": "F"},
                    ]
                }
            )
            entries = await session.fetch_all(
                category="people", tag_filter=active_females_filter
            )
            print(f"Found {len(entries)} active females")
            assert len(entries) == (2 if is_encrypted else 0), (
                f"Expected {2 if is_encrypted else 0} active females "
                f"(Alice, Charlie if encrypted; none if non-encrypted)"
            )
            for entry in entries:
                try:
                    value = json.loads(entry.value)
                    print(f" - {entry.name}: {value}")
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON for {entry.name}: {entry.value}")
                    raise

            # Test fetch_all with WQL that should return no entries
            print("Fetching all people with status='pending'...")
            pending_filter = json.dumps({"attr::person.status": "pending"})
            entries = await session.fetch_all(
                category="people", tag_filter=pending_filter
            )
            print(f"Found {len(entries)} people with status='pending'")
            assert len(entries) == 0, "Expected 0 people with status='pending'"

        # Step 6: Test replace
        print("\n### Testing Replace ###")
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
                category="people", name="person1" if is_encrypted else "person4"
            )
            try:
                value = json.loads(updated_entry.value)
                name = "Alice" if is_encrypted else "David"
                print(f"Updated {name}: {updated_entry.name}, value={value}")
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
                    "attr::person.status": "active",
                    "attr::person.birthdate::value": "19800101"
                    if is_encrypted
                    else "20010101",
                },
            )
            new_entry = await session.fetch(
                category="people", name="person4" if is_encrypted else "person7"
            )
            try:
                value = json.loads(new_entry.value)
                name = "David" if is_encrypted else "Grace"
                print(f"Inserted {name}: {new_entry.name}, value={value}")
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
                category="people", name="person4" if is_encrypted else "person7"
            )
            try:
                value = json.loads(updated_entry.value)
                name = "David" if is_encrypted else "Grace"
                print(f"Updated {name}: {updated_entry.name}, value={value}")
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
            print(f"People after Step 6 updates: {parsed_entries}")

        # Step 7: Test count with tag_filter
        print("\n### Testing Count with tag_filter ###")
        async with store.session() as session:
            # Test count with complex WQL: Inactive males
            print("Counting inactive males...")
            inactive_males_filter = json.dumps(
                {
                    "$and": [
                        {"attr::person.status": "inactive"},
                        {"attr::person.gender": "M"},
                    ]
                }
            )
            count_inactive_males = await session.count(
                category="people", tag_filter=inactive_males_filter
            )
            print(f"Counted {count_inactive_males} inactive males")
            expected = 2 if is_encrypted else 1
            assert count_inactive_males == expected, (
                f"Expected {expected} inactive males "
                f"(Bob, David if encrypted; David if non-encrypted), "
                f"got {count_inactive_males}"
            )
            if count_inactive_males > 0:
                entries = await session.fetch_all(
                    category="people", tag_filter=inactive_males_filter
                )
                parsed_entries = []
                for entry in entries:
                    try:
                        value = json.loads(entry.value)
                        parsed_entries.append(f"{entry.name}: {value}")
                    except json.JSONDecodeError:
                        print(f"Failed to parse JSON for {entry.name}: {entry.value}")
                        raise
                print(f"Inactive males: {parsed_entries}")

        # Step 8: Test remove_all with tag_filter
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
            print(f"Entries to delete in Step 8: {parsed_entries}")
            deleted_count = await session.remove_all(
                category="people", tag_filter=remove_filter
            )
            print(f"Deleted {deleted_count} inactive people born after 2000")
            assert deleted_count == (1 if is_encrypted else 2), (
                f"Expected to delete {1 if is_encrypted else 2} person "
                f"(Bob if encrypted; Eve, Grace if non-encrypted), got {deleted_count}"
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
            print(f"People after Step 8 deletion: {parsed_entries}")

    except Exception as e:
        LOGGER.error(f"Error in run_tests: {str(e)}")
        raise


async def main():
    """Run the main test function."""
    register_backends()
    print("Starting the SQLite database test program with WQL")
    store = None
    non_enc_store = None
    store_wrong = None
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

        # Step 9: Change the encryption key
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

        # Step 10: Check if the new key works
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

        # Step 11: Ensure the old key fails
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
            await store_old.close()  # Call asynchronously
            exit(1)
        except Exception as e:
            print(f"Good! Old key failed as expected: {e}")

        # Step 12: Re-run tests with new key
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

        # Step 13: Test security with a wrong key
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
            await store_wrong.close()  # Call asynchronously
            exit(1)
        except Exception as e:
            print(f"Perfect! Wrong key failed as expected: {e}")

        # Step 14: Test Non-Encrypted Database
        print("\n=======================================")
        print("=== Testing Non-Encrypted Database ===")
        print("=======================================")
        non_enc_db_path = "test_non_enc.db"
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
            profile_name = await non_enc_store.get_profile_name()
            print(f"Non-encrypted database ready! Profile name: {profile_name}")
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

        # Run tests for non-encrypted database
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
            await store_with_key.close()  # Call asynchronously
            exit(1)
        except Exception as e:
            print(f"Correct! Failed to open with a key as expected: {e}")

        print("\n### All Done! ###")
        print("Tests completed successfully. ")

    except Exception as e:
        LOGGER.error(f"Error in main: {str(e)}")
        raise
    finally:
        for db_store in [store, non_enc_store, store_wrong]:
            if db_store is not None:
                try:
                    await db_store.close()  # Call asynchronously
                    LOGGER.debug(f"Closed database store: {db_store}")
                except Exception as close_err:
                    LOGGER.error(f"Error closing store {db_store}: {str(close_err)}")
            else:
                LOGGER.debug("Skipping None store")


if __name__ == "__main__":
    asyncio.run(main(), debug=True)
