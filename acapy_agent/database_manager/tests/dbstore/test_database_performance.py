"""Database performance and optimization tests.

These tests are intentionally skipped by default to avoid slowing down
standard CI runs. Enable locally by removing the module-level skip below.
"""

import asyncio
import json
from typing import Optional

import pytest

from acapy_agent.database_manager.dbstore import DBStore


class DatabasePerformanceTestBase:
    """Base class for database performance tests."""

    # Class-level database store that can be reused
    _class_store: Optional[DBStore] = None
    _class_store_lock = asyncio.Lock()

    @classmethod
    async def get_class_store(cls) -> DBStore:
        """Get or create a class-level database store for reuse."""
        async with cls._class_store_lock:
            if cls._class_store is None:
                import tempfile
                from pathlib import Path

                tmpdir = tempfile.mkdtemp()
                db_path = Path(tmpdir) / "class_test.db"
                uri = f"sqlite://{db_path}"

                cls._class_store = await DBStore.provision(
                    uri=uri,
                    pass_key=None,  # No encryption for speed
                    profile="class_test_profile",
                    recreate=True,
                    release_number="release_0_1",
                    schema_config="normalize",
                )
            return cls._class_store

    @classmethod
    async def cleanup_class_store(cls):
        """Cleanup class-level store."""
        async with cls._class_store_lock:
            if cls._class_store:
                await cls._class_store.close()
                cls._class_store = None

    async def bulk_insert_test_data(self, store, category, count=100):
        """Efficiently insert test data in bulk."""
        async with store.transaction() as session:
            for i in range(count):
                await session.insert(
                    category=category,
                    name=f"test_{i:04d}",
                    value=json.dumps({"id": i, "data": f"test_data_{i}"}),
                    tags={"type": "test", "index": str(i)},
                    expiry_ms=3600000,
                )

    async def parallel_operations(self, store, operations):
        """Execute multiple database operations in parallel."""
        tasks = []
        for op in operations:
            if op["type"] == "insert":
                task = self._insert_op(store, op)
            elif op["type"] == "scan":
                task = self._scan_op(store, op)
            elif op["type"] == "remove":
                task = self._remove_op(store, op)
            else:
                continue
            tasks.append(task)

        return await asyncio.gather(*tasks)

    async def _insert_op(self, store, op):
        """Execute insert operation."""
        async with store.transaction() as session:
            return await session.insert(
                category=op["category"],
                name=op["name"],
                value=op["value"],
                tags=op.get("tags", {}),
            )

    async def _scan_op(self, store, op):
        """Execute scan operation."""
        # Use store.scan() not session.scan()
        scan_obj = store.scan(
            category=op["category"],
            tag_filter=op.get("tag_filter"),
            limit=op.get("limit", 100),
        )
        # Collect entries from scan iterator
        entries = []
        async for entry in scan_obj:
            entries.append(entry)
        return entries

    async def _remove_op(self, store, op):
        """Execute remove operation."""
        async with store.transaction() as session:
            return await session.remove(
                category=op["category"],
                name=op["name"],
            )


class TestDatabasePerformancePatterns(DatabasePerformanceTestBase):
    """Test database performance patterns and optimizations."""

    @pytest.mark.asyncio
    async def test_bulk_insert_performance(self, fast_store):
        """Test bulk insert performance."""
        import time

        start = time.time()
        await self.bulk_insert_test_data(fast_store, "test_category", count=1000)
        elapsed = time.time() - start

        assert elapsed < 2.0, (
            f"Bulk insert of 1000 records took {elapsed:.2f}s (should be < 2s)"
        )

        # Verify data
        scan_obj = fast_store.scan(category="test_category", limit=10)
        entries = []
        async for entry in scan_obj:
            entries.append(entry)
        assert len(entries) == 10

    @pytest.mark.asyncio
    async def test_parallel_operations(self, fast_store):
        """Test parallel database operations."""
        operations = [
            {
                "type": "insert",
                "category": "cat1",
                "name": "item1",
                "value": '{"test": 1}',
            },
            {
                "type": "insert",
                "category": "cat1",
                "name": "item2",
                "value": '{"test": 2}',
            },
            {
                "type": "insert",
                "category": "cat2",
                "name": "item3",
                "value": '{"test": 3}',
            },
            {"type": "scan", "category": "cat1"},
            {"type": "scan", "category": "cat2"},
        ]

        results = await self.parallel_operations(fast_store, operations)

        # Verify parallel operations completed
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_reused_store(self):
        """Test using a reused class-level store."""
        store = await self.get_class_store()

        # First operation
        async with store.transaction() as session:
            await session.insert(
                category="reuse_test",
                name="test1",
                value='{"data": "test"}',
            )

        # Second operation on same store
        scan_obj = store.scan(category="reuse_test")
        entries = []
        async for entry in scan_obj:
            entries.append(entry)
        assert len(entries) >= 1

        # Note: Don't close the store here as it's reused by other tests

    @classmethod
    def teardown_class(cls):
        """Cleanup after all tests in class."""
        asyncio.run(cls.cleanup_class_store())


class TestDatabaseConnectionPool:
    """Test database connection pool management and optimization."""

    @pytest.mark.asyncio
    async def test_connection_reuse(self, fast_store):
        """Test that connections are properly reused."""
        # Perform multiple operations that should reuse connections
        for _ in range(10):
            async with fast_store.transaction() as session:
                await session.insert(
                    category="pool_test",
                    name=f"test_{_}",
                    value='{"test": true}',
                )

        # Verify all operations succeeded
        scan_obj = fast_store.scan(category="pool_test")
        entries = []
        async for entry in scan_obj:
            entries.append(entry)
        assert len(entries) == 10

    @pytest.mark.asyncio
    async def test_concurrent_transactions(self, fast_store):
        """Test concurrent transaction handling."""

        async def transaction_task(store, task_id):
            async with store.transaction() as session:
                await session.insert(
                    category="concurrent_test",
                    name=f"task_{task_id}",
                    value=json.dumps({"task": task_id}),
                )
                # Simulate some work
                await asyncio.sleep(0.01)
                return task_id

        # Run 20 concurrent transactions
        tasks = [transaction_task(fast_store, i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 20
        assert set(results) == set(range(20))

        # Verify all were inserted
        scan_obj = fast_store.scan(category="concurrent_test")
        entries = []
        async for entry in scan_obj:
            entries.append(entry)
        assert len(entries) == 20
