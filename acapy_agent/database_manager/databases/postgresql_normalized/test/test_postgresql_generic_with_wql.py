"""Tests for PostgreSQL generic database with WQL support.

Skipped by default unless `POSTGRES_URL` is set in the environment.
"""

import asyncio
import json
import logging
import os

import pytest

from acapy_agent.database_manager.databases.errors import DatabaseError
from acapy_agent.database_manager.databases.postgresql_normalized.backend import (
    PostgresqlBackend,
)
from acapy_agent.database_manager.databases.postgresql_normalized.config import (
    PostgresConfig,
)

# Skip all tests in this file if POSTGRES_URL env var is not set
if not os.getenv("POSTGRES_URL"):
    pytest.skip(
        "PostgreSQL tests disabled: set POSTGRES_URL to enable",
        allow_module_level=True,
    )
pytestmark = pytest.mark.postgres

logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)


async def main():
    """Run test main function."""
    # Define configuration using PostgresConfig
    conn_str = os.environ.get(
        "POSTGRES_URL", "postgres://myuser:mypass@localhost:5432/mydb?sslmode=prefer"
    )
    _ = PostgresConfig(  # Config validation test
        uri=conn_str,
        min_size=4,
        max_size=10,
        timeout=30.0,
        max_idle=5.0,
        max_lifetime=3600.0,
        schema_config="generic",
    )

    print("=== Starting PostgreSQL Generic Schema Test ===")
    print(f"Provisioning database at {conn_str} with generic schema...")
    backend = PostgresqlBackend()
    store = None
    try:
        store = await backend.provision(
            uri=conn_str,
            key_method=None,
            pass_key=None,
            profile="test_profile",
            recreate=True,
            release_number="release_0",
            schema_config="generic",
        )
        await store.initialize()
        LOGGER.debug("Store initialized: %s", store)
        profile_name = await store.get_profile_name()
        print(f"Database ready! Profile name: {profile_name}")
        assert profile_name == "test_profile", (
            f"Profile name mismatch: expected 'test_profile', got '{profile_name}'"
        )
    except DatabaseError as e:
        LOGGER.error("Failed to initialize database: %s", str(e))
        print(f"Oops! Failed to initialize database: {e}")
        raise
    except Exception as e:
        LOGGER.error("Unexpected error during store initialization: %s", str(e))
        print(f"Oops! Unexpected error during store initialization: {e}")
        raise

    try:
        async with await store.transaction(profile="test_profile") as session:
            print("Adding David...")
            await session.insert(
                category="people",
                name="person4",
                value=json.dumps({"name": "David"}),
                tags={
                    "attr::person.status": "active",
                    "attr::person.gender": "M",
                    "attr::person.birthdate::value": "19800101",
                },
            )
            print("Adding Eve...")
            await session.insert(
                category="people",
                name="person5",
                value=json.dumps({"name": "Eve"}),
                tags={
                    "attr::person.status": "inactive",
                    "attr::person.gender": "F",
                    "attr::person.birthdate::value": "20010101",
                },
            )
            print("Adding Frank...")
            await session.insert(
                category="people",
                name="person6",
                value=json.dumps({"name": "Frank"}),
                tags={
                    "attr::person.status": "active",
                    "attr::person.gender": "O",
                    "attr::person.birthdate::value": "19950101",
                },
            )
            print("Test data added successfully!")

        await run_tests(store, conn_str)
    except Exception as e:
        LOGGER.error("Error in main: %s", str(e))
        raise
    finally:
        print(f"Closing store in main: {store}")
        await store.close(remove=True)
        print("Database closed gracefully in main.")


async def run_tests(store, conn_str):
    """Run PostgreSQL tests with WQL queries."""
    async with await store.session(profile="test_profile") as session:
        entries = []
        async for entry in store.scan(profile="test_profile", category="people"):
            try:
                value = json.loads(entry.value)
                entries.append(f"{entry.name}: {entry.tags}, value={value}")
            except json.JSONDecodeError:
                print(f"Failed to parse JSON for {entry.name}: {entry.value}")
                raise
        print(f"People before tests: {entries}")

    async for entry in store.scan(
        profile="test_profile",
        category="people",
        tag_filter={"attr::person.status": "active"},
        limit=1,
    ):
        try:
            value = json.loads(entry.value)
            print(f"Scanned with limit=1: 1 entries\n - {entry.name}: {value}")
        except json.JSONDecodeError:
            print(f"Failed to parse JSON for {entry.name}: {entry.value}")
            raise

    async for entry in store.scan(
        profile="test_profile",
        category="people",
        tag_filter={
            "$and": [{"attr::person.status": "active"}, {"attr::person.gender": "F"}]
        },
        limit=2,
    ):
        try:
            value = json.loads(entry.value)
            print(f"Scanned with limit=2: 0 entries\n - {entry.name}: {value}")
        except json.JSONDecodeError:
            print(f"Failed to parse JSON for {entry.name}: {entry.value}")
            raise

    async for entry in store.scan(
        profile="test_profile",
        category="people",
        tag_filter={"$not": {"attr::person.gender": "M"}},
    ):
        try:
            value = json.loads(entry.value)
            print(f"Scanned not male: 2 entries\n - {entry.name}: {value}")
        except json.JSONDecodeError:
            print(f"Failed to parse JSON for {entry.name}: {entry.value}")
            raise

    async with await store.session(profile="test_profile") as session:
        print("Fetching person4 with status='active'...")
        entry = await session.fetch(
            category="people",
            name="person4",
            tag_filter={"attr::person.status": "active"},
        )
        if entry:
            try:
                value = json.loads(entry.value)
                print(f"Fetched: {entry.name} with status=active, value={value}")
            except json.JSONDecodeError:
                print(f"Failed to parse JSON for {entry.name}: {entry.value}")
                raise
        print("Fetching person4 with status='inactive'...")
        entry = await session.fetch(
            category="people",
            name="person4",
            tag_filter={"attr::person.status": "inactive"},
        )
        if not entry:
            print("No person4 with status=inactive")
        print("Fetching person5 with status='active' and gender='F'...")
        entry = await session.fetch(
            category="people",
            name="person5",
            tag_filter={
                "$and": [{"attr::person.status": "active"}, {"attr::person.gender": "F"}]
            },
        )
        if not entry:
            print("No person5 with status=active and gender=F")

    async with await store.session(profile="test_profile") as session:
        print("Fetching all active females...")
        entries = await session.fetch_all(
            category="people",
            tag_filter={
                "$and": [{"attr::person.status": "active"}, {"attr::person.gender": "F"}]
            },
        )
        parsed_entries = []
        for entry in entries:
            try:
                value = json.loads(entry.value)
                parsed_entries.append(f"{entry.name}: {value}")
            except json.JSONDecodeError:
                print(f"Failed to parse JSON for {entry.name}: {entry.value}")
                raise
        print(f"Found {len(entries)} active females: {parsed_entries}")
        print("Fetching all people with status='pending'...")
        entries = await session.fetch_all(
            category="people", tag_filter={"attr::person.status": "pending"}
        )
        parsed_entries = []
        for entry in entries:
            try:
                value = json.loads(entry.value)
                parsed_entries.append(f"{entry.name}: {value}")
            except json.JSONDecodeError:
                print(f"Failed to parse JSON for {entry.name}: {entry.value}")
                raise
        print(f"Found {len(entries)} people with status='pending': {parsed_entries}")

    async with await store.transaction(profile="test_profile") as session:
        print("Updating David...")
        await session.replace(
            category="people",
            name="person4",
            value=json.dumps({"name": "David Updated"}),
            tags={
                "attr::person.status": "inactive",
                "attr::person.gender": "M",
                "attr::person.birthdate::value": "19800101",
            },
        )
        updated_entry = await session.fetch(category="people", name="person4")
        try:
            value = json.loads(updated_entry.value)
            print(f"Updated David: {updated_entry.name}, value={value}")
        except json.JSONDecodeError:
            print(f"Failed to parse JSON for {updated_entry.name}: {updated_entry.value}")
            raise
        assert updated_entry.value == json.dumps({"name": "David Updated"}), (
            "Value not updated"
        )


if __name__ == "__main__":
    asyncio.run(main())
