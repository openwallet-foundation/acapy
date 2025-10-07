"""PostgreSQL normalized database test with WQL queries.

Tests PostgreSQL database for 'connection' category with WQL queries.
1. Database provisioning with a normalized schema.
2. Data insertion with JSON values and tags.
3. Scanning with WQL equality queries and limits.
4. Counting records with WQL existence queries.
5. Fetching records with WQL filters.
6. Updating records with replace.
7. Fetching all records with WQL range queries.
8. Removing records with WQL equality queries.
9. Cleanup and verification.
"""

import asyncio
import json
import logging
import os

import pytest

from acapy_agent.database_manager.databases.backends.backend_registration import (
    register_backends,
)
from acapy_agent.database_manager.databases.errors import DatabaseError
from acapy_agent.database_manager.databases.postgresql_normalized.backend import (
    PostgresqlBackend,
)
from acapy_agent.database_manager.databases.postgresql_normalized.database import (
    PostgresDatabase,
)

# Skip all tests in this file if POSTGRES_URL env var is not set
if not os.getenv("POSTGRES_URL"):
    pytest.skip(
        "PostgreSQL tests disabled: set POSTGRES_URL to enable",
        allow_module_level=True,
    )
pytestmark = pytest.mark.postgres


# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

# Sample connection JSON data (same as SQLite test)
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
    "alias": "Conn1Alias",
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
    "alias": None,
    "error_msg": None,
    "their_label": "Test Wallet",
    "their_public_did": None,
    "connection_protocol": "didexchange/1.0",
}

CONNECTION_JSON_3 = {
    "connection_id": "conn_3",
    "request_id": "f234g567-h890-5ijk-pqrs-tuvwxyz",
    "invitation_key": "Fn8jLw4m7u6t3x2Be9vKqR",
    "state": "completed",
    "their_role": "invitee",
    "invitation_msg_id": "5e678f12-cdef-6lmn-opqr-uvwxyz123",
    "their_did": "did:peer:3BcDeFgHiJkLmNoP456789012",
    "my_did": "did:peer:6YzAbCdEfGhIjKlMn789012",
    "created_at": "2025-05-09T15:00:00.000000Z",
    "updated_at": "2025-05-09T15:01:00.000000Z",
    "inbound_connection_id": "conn_123",
    "accept": "auto",
    "invitation_mode": "once",
    "alias": "Conn3Alias",
    "error_msg": None,
    "their_label": "Another Wallet",
    "their_public_did": None,
    "connection_protocol": "didexchange/1.1",
}


async def run_tests(store: PostgresDatabase, conn_str: str):
    """Run normalized PostgreSQL tests with WQL queries."""
    try:
        # Debug: Log current data state
        session = await store.session(profile="test_profile")
        async with session:
            entries = await session.fetch_all(category="connection")
            print(
                "Connections before tests: "
                f"{
                    [
                        f'{entry.name}: {entry.tags}, value={json.loads(entry.value)}'
                        for entry in entries
                    ]
                }"
            )

        # Step 3: Test scan with WQL equality query
        print("\n### Testing Scan with WQL Equality Query ###")
        wql_equality = json.dumps({"state": "active"})
        print(f"Testing WQL Equality Query: {wql_equality}")
        scanned_entries = []
        async for entry in store.scan(
            profile="test_profile",
            category="connection",
            tag_filter=wql_equality,
            limit=2,
        ):
            scanned_entries.append(entry)
            print(f" - {entry.name}: {json.loads(entry.value)}")
        print(f"Scanned with limit=2: {len(scanned_entries)} entries")
        assert len(scanned_entries) == 1, "Expected 1 active connection"
        for entry in scanned_entries:
            assert json.loads(entry.value)["state"] == "active", (
                "State should be 'active'"
            )

        # Step 4: Test count with WQL existence query
        print("\n### Testing Count with WQL Existence Query ###")
        wql_existence = json.dumps({"$exist": ["alias"]})
        print(f"Testing WQL Existence Query: {wql_existence}")
        session = await store.session(profile="test_profile")
        async with session:
            count = await session.count(category="connection", tag_filter=wql_existence)
            print(f"Counted {count} connections with 'alias'")
            assert count == 2, "Expected 2 connections with 'alias'"

        # Step 5: Test replace in database
        print("\n### Testing Replace in Database ###")
        transaction = await store.transaction(profile="test_profile")
        async with transaction:
            print("Updating Connection 1...")
            updated_json = CONNECTION_JSON_1.copy()
            updated_json["state"] = "completed"
            updated_json["their_label"] = "Updated Wallet"
            await transaction.replace(
                category="connection",
                name="conn_1",
                value=json.dumps(updated_json),
                tags={"state": "completed", "alias": updated_json["alias"]},
            )
            updated_entry = await transaction.fetch(category="connection", name="conn_1")
            print(f"Updated Connection 1: {json.loads(updated_entry.value)}")
            assert json.loads(updated_entry.value)["state"] == "completed", (
                "State not updated"
            )

            print("Inserting Connection 4...")
            await transaction.insert(
                category="connection",
                name="conn_4",
                value=json.dumps(CONNECTION_JSON_1),
                tags={
                    "state": CONNECTION_JSON_1["state"],
                    "alias": CONNECTION_JSON_1["alias"],
                },
            )
            new_entry = await transaction.fetch(category="connection", name="conn_4")
            print(f"Inserted Connection 4: {json.loads(new_entry.value)}")
            assert new_entry is not None, "Insert failed"

            print("Updating Connection 4...")
            updated_json_4 = CONNECTION_JSON_1.copy()
            updated_json_4["state"] = "inactive"
            await transaction.replace(
                category="connection",
                name="conn_4",
                value=json.dumps(updated_json_4),
                tags={"state": "inactive", "alias": updated_json_4["alias"]},
            )
            updated_conn4 = await transaction.fetch(category="connection", name="conn_4")
            print(f"Updated Connection 4: {json.loads(updated_conn4.value)}")
            assert json.loads(updated_conn4.value)["state"] == "inactive", (
                "State not updated"
            )

        # Debug: Inspect connections for conn_3
        print("\n### Debugging Connections for conn_3 ###")
        session = await store.session(profile="test_profile")
        async with session:
            entries = await session.fetch_all(category="connection")
            for entry in entries:
                if entry.name == "conn_3":
                    print(f"Found conn_3: {json.loads(entry.value)}")
                else:
                    print(
                        f"Found other connection {entry.name}: {json.loads(entry.value)}"
                    )

        # Step 6: Test fetch with WQL filters
        print("\n### Testing Fetch with WQL Filters ###")
        session = await store.session(profile="test_profile")
        async with session:
            print("Fetching conn_1 with state='completed'...")
            entry = await session.fetch(
                category="connection",
                name="conn_1",
                tag_filter=json.dumps({"state": "completed"}),
            )
            assert entry is not None, "Should fetch conn_1 with state='completed'"
            print(f"Fetched: {entry.name} with state={json.loads(entry.value)['state']}")

            print("Fetching conn_1 with state='active'...")
            entry = await session.fetch(
                category="connection",
                name="conn_1",
                tag_filter=json.dumps({"state": "active"}),
            )
            assert entry is None, "Should not fetch conn_1 with state='active'"

            print("Fetching conn_2 with {'$exist': ['alias']}...")
            LOGGER.debug(
                "Executing WQL query: %s for conn_2", json.dumps({"$exist": ["alias"]})
            )
            entry = await session.fetch(
                category="connection",
                name="conn_2",
                tag_filter=json.dumps({"$exist": ["alias"]}),
            )
            assert entry is None, "Should not fetch conn_2 since alias is None"
            LOGGER.debug("Result for conn_2 $exist query: %s", entry)

            print("Fetching conn_3 with {'$exist': ['alias']}...")
            LOGGER.debug(
                "Executing WQL query: %s for conn_3", json.dumps({"$exist": ["alias"]})
            )
            entry = await session.fetch(
                category="connection",
                name="conn_3",
                tag_filter=json.dumps({"$exist": ["alias"]}),
            )
            assert entry is not None, "Should fetch conn_3 with alias present"
            print(f"Fetched: {entry.name} with alias={json.loads(entry.value)['alias']}")
            LOGGER.debug("Result for conn_3 $exist query: %s", entry)

            print("Fetching conn_1 with created_at < '2025-05-08T00:00:00Z'...")
            entry = await session.fetch(
                category="connection",
                name="conn_1",
                tag_filter=json.dumps({"created_at": {"$lt": "2025-05-08T00:00:00Z"}}),
            )
            assert entry is not None, (
                "Should fetch conn_1 with created_at < '2025-05-08T00:00:00Z'"
            )
            print(
                f"Fetched: {entry.name} with "
                f"created_at={json.loads(entry.value)['created_at']}"
            )

            print("Fetching conn_3 with created_at < '2025-05-08T00:00:00Z'...")
            entry = await session.fetch(
                category="connection",
                name="conn_3",
                tag_filter=json.dumps({"created_at": {"$lt": "2025-05-08T00:00:00Z"}}),
            )
            assert entry is None, (
                "Should not fetch conn_3 with created_at < '2025-05-08T00:00:00Z'"
            )

        # Step 7: Test fetch_all with WQL range query
        print("\n### Testing Fetch All with WQL Range Query ###")
        wql_range = json.dumps({"created_at": {"$gt": "2025-05-08T00:00:00Z"}})
        print(f"Testing WQL Range Query: {wql_range}")
        session = await store.session(profile="test_profile")
        async with session:
            entries = await session.fetch_all(category="connection", tag_filter=wql_range)
            print(f"Found {len(entries)} connections created after 2025-05-08")
            assert len(entries) == 2, "Expected 2 connections after 2025-05-08"
            for entry in entries:
                print(f" - {entry.name}: {json.loads(entry.value)}")
                assert json.loads(entry.value)["created_at"] > "2025-05-08T00:00:00Z", (
                    "Date should be after 2025-05-08"
                )

        # Step 8: Test remove_all with WQL equality query
        print("\n### Testing Remove All with WQL Equality Query ###")
        wql_remove = json.dumps({"state": "inactive"})
        print(f"Testing WQL Remove Query: {wql_remove}")
        transaction = await store.transaction(profile="test_profile")
        async with transaction:
            deleted_count = await transaction.remove_all(
                category="connection", tag_filter=wql_remove
            )
            print(f"Deleted {deleted_count} inactive connections")
            assert deleted_count == 2, "Expected to delete 2 inactive connections"
            remaining = await transaction.fetch_all(category="connection")
            print(f"Remaining connections: {len(remaining)}")
            assert len(remaining) == 2, "Expected 2 connections remaining"

        # Step 9: Clean up
        print("\n### Cleaning Up ###")
        print("Removing all connections from the database...")
        transaction = await store.transaction(profile="test_profile")
        async with transaction:
            deleted_count = await transaction.remove_all(category="connection")
            print(f"Wiped out {deleted_count} entries!")
            assert deleted_count == 2, "Expected to delete 2 entries!"

        # Verify cleanup
        print("\nChecking if the database is empty...")
        session = await store.session(profile="test_profile")
        async with session:
            entries_after_remove = await session.fetch_all(category="connection")
            print(f"Remaining entries: {len(entries_after_remove)} (should be 0)")
            assert len(entries_after_remove) == 0, "Database should be empty!"

    except Exception as e:
        LOGGER.error(f"Error in run_tests: {str(e)}")
        raise


async def main():
    """Main test function."""
    register_backends()
    print(
        "=== Starting PostgreSQL Normalized Schema Test "
        "(Connection Category with WQL Queries) ==="
    )
    store = None
    try:
        # Step 1: Provision the database
        conn_str = os.environ.get(
            "POSTGRES_URL", "postgres://myuser:mypass@localhost:5432/mydb?sslmode=prefer"
        )
        print("\n### Setting Up the Database ###")
        print(f"Provisioning database at {conn_str} with normalized schema...")
        backend = PostgresqlBackend()
        try:
            store = await backend.provision(
                uri=conn_str,
                key_method=None,
                pass_key=None,
                profile="test_profile",
                recreate=True,
                release_number="release_0_1",
                schema_config="normalize",
            )
            await store.initialize()
            LOGGER.debug(f"Store initialized: {store}")
            profile_name = await store.get_profile_name()
            print(f"Database ready! Profile name: {profile_name}")
            assert profile_name == "test_profile", (
                f"Profile name mismatch: expected 'test_profile', got '{profile_name}'"
            )
        except DatabaseError as e:
            print(f"Oops! Failed to initialize database: {e}")
            LOGGER.error("Failed to initialize database: %s", str(e))
            exit(1)
        except Exception as e:
            print(f"Oops! Unexpected error during store initialization: {e}")
            LOGGER.error("Unexpected error during store initialization: %s", str(e))
            exit(1)

        # Step 2: Add test connections to the database
        print("\n### Adding Connections to the Database ###")
        transaction = await store.transaction(profile="test_profile")
        async with transaction:
            print("Adding Connection 1...")
            await transaction.insert(
                category="connection",
                name="conn_1",
                value=json.dumps(CONNECTION_JSON_1),
                tags={
                    "state": CONNECTION_JSON_1["state"],
                    "alias": CONNECTION_JSON_1["alias"],
                },
                expiry_ms=3600000,
            )
            print("Adding Connection 2...")
            await transaction.insert(
                category="connection",
                name="conn_2",
                value=json.dumps(CONNECTION_JSON_2),
                tags={
                    "state": CONNECTION_JSON_2["state"],
                    "alias": CONNECTION_JSON_2["alias"],
                },
                expiry_ms=3600000,
            )
            print("Adding Connection 3...")
            await transaction.insert(
                category="connection",
                name="conn_3",
                value=json.dumps(CONNECTION_JSON_3),
                tags={
                    "state": CONNECTION_JSON_3["state"],
                    "alias": CONNECTION_JSON_3["alias"],
                },
                expiry_ms=3600000,
            )
            print("All three connections added successfully!")

        # Debug: Inspect connections for conn_3
        print("\n### Debugging Initial Connections for conn_3 ###")
        session = await store.session(profile="test_profile")
        async with session:
            entries = await session.fetch_all(category="connection")
            for entry in entries:
                if entry.name == "conn_3":
                    print(f"Found conn_3: {json.loads(entry.value)}")
                else:
                    print(
                        f"Found other connection {entry.name}: {json.loads(entry.value)}"
                    )

        # Run tests
        await run_tests(store, conn_str)

        print("\n### TEST COMPLETED ###")

    except Exception as e:
        LOGGER.error(f"Error in main: {str(e)}")
        raise
    finally:
        if store:
            LOGGER.debug(f"Closing store in main: {store}")
            # await store.close(remove=True)
            print("Database closed gracefully in main.")


if __name__ == "__main__":
    asyncio.run(main())
