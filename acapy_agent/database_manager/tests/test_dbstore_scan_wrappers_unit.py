import types

import pytest

from acapy_agent.database_manager.dbstore import DBStore
from acapy_agent.database_manager.interfaces import (
    AbstractDatabaseSession,
    AbstractDatabaseStore,
)


class _FakeDB(AbstractDatabaseStore):
    async def create_profile(self, name: str = None) -> str:
        return name or "p"

    async def get_profile_name(self) -> str:
        return "p"

    async def remove_profile(self, name: str) -> bool:
        return True

    async def rekey(self, key_method: str = None, pass_key: str = None):
        return None

    def scan(
        self,
        profile,
        category,
        tag_filter=None,
        offset=None,
        limit=None,
        order_by=None,
        descending=False,
    ):
        def gen():
            for i in range((offset or 0), (offset or 0) + (limit or 3)):
                yield types.SimpleNamespace(
                    category=category, name=f"n{i}", value="{}", tags={}
                )

        return gen()

    def scan_keyset(
        self,
        profile,
        category,
        tag_filter=None,
        last_id=None,
        limit=None,
        order_by=None,
        descending=False,
    ):
        def gen():
            start = (last_id or 0) + 1
            for i in range(start, start + (limit or 3)):
                yield types.SimpleNamespace(
                    category=category, name=f"k{i}", value="{}", tags={}
                )

        return gen()

    def session(self, profile: str = None, release_number: str = "release_0"):
        return _FakeSession()

    def transaction(self, profile: str = None, release_number: str = "release_0"):
        s = _FakeSession()
        s._is_txn = True
        return s

    async def close(self, remove: bool = False) -> bool:
        return True


class _FakeSession(AbstractDatabaseSession):
    def __init__(self):
        self._is_txn = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def count(self, category: str, tag_filter: str | dict = None) -> int:
        return 3

    async def fetch(self, category: str, name: str, for_update: bool = False):
        return types.SimpleNamespace(category=category, name=name, value="{}", tags={})

    async def fetch_all(
        self,
        category: str,
        tag_filter: str | dict = None,
        limit: int = None,
        for_update: bool = False,
        order_by: str | None = None,
        descending: bool = False,
    ):
        return [
            types.SimpleNamespace(category=category, name=f"n{i}", value="{}", tags={})
            for i in range(3)
        ]

    async def insert(
        self,
        category: str,
        name: str,
        value: str | bytes = None,
        tags: dict = None,
        expiry_ms: int = None,
        value_json=None,
    ):
        return None

    async def replace(
        self,
        category: str,
        name: str,
        value: str | bytes = None,
        tags: dict = None,
        expiry_ms: int = None,
        value_json=None,
    ):
        return None

    async def remove(self, category: str, name: str):
        return None

    async def remove_all(self, category: str, tag_filter: str | dict = None) -> int:
        return 3

    async def commit(self):
        if not self._is_txn:
            raise Exception("not txn")

    async def rollback(self):
        if not self._is_txn:
            raise Exception("not txn")

    async def close(self):
        return None

    def translate_error(self, e):
        return e


@pytest.mark.asyncio
async def test_scan_and_keyset_sync_generators():
    store = DBStore(_FakeDB(), uri="sqlite://:memory:")
    s = store.scan(category="c", limit=2, offset=1)
    items = [i async for i in s]
    assert [it.name for it in items] == ["n1", "n2"]

    ks = store.scan_keyset(category="c", last_id=2, limit=2)
    items = [i async for i in ks]
    assert [it.name for it in items] == ["k3", "k4"]


@pytest.mark.asyncio
async def test_session_and_transaction_wrappers():
    store = DBStore(_FakeDB(), uri="sqlite://:memory:")
    async with store.session() as session:
        entries = await session.fetch_all(category="c")
        assert len(entries) == 3
    async with store.transaction() as t:
        await t.insert("c", "n1", value="{}")
        await t.replace("c", "n1", value="{}")
        await t.remove("c", "n1")
        assert await t.remove_all("c") == 3
