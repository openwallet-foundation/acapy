import types

import pytest

from acapy_agent.database_manager.dbstore import DBStore
from acapy_agent.database_manager.interfaces import (
    AbstractDatabaseSession,
    AbstractDatabaseStore,
)


class _AsyncDB(AbstractDatabaseStore):
    async def create_profile(self, name: str = None) -> str:
        return name or "p"

    async def get_profile_name(self) -> str:
        return "p"

    async def remove_profile(self, name: str) -> bool:
        return True

    async def rekey(self, key_method: str = None, pass_key: str = None):
        return None

    async def scan(
        self,
        profile,
        category,
        tag_filter=None,
        offset=None,
        limit=None,
        order_by=None,
        descending=False,
    ):
        for i in range((offset or 0), (offset or 0) + (limit or 2)):
            yield types.SimpleNamespace(
                category=category, name=f"an{i}", value="{}", tags={}
            )

    async def scan_keyset(
        self,
        profile,
        category,
        tag_filter=None,
        last_id=None,
        limit=None,
        order_by=None,
        descending=False,
    ):
        start = (last_id or 0) + 1
        for i in range(start, start + (limit or 2)):
            yield types.SimpleNamespace(
                category=category, name=f"ak{i}", value="{}", tags={}
            )

    def session(self, profile: str = None, release_number: str = "release_0"):
        return _AsyncSession()

    def transaction(self, profile: str = None, release_number: str = "release_0"):
        s = _AsyncSession()
        s._is_txn = True
        return s

    async def close(self, remove: bool = False) -> bool:
        return True


class _AsyncSession(AbstractDatabaseSession):
    def __init__(self):
        self._is_txn = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def count(self, category: str, tag_filter: str | dict = None) -> int:
        return 2

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
            types.SimpleNamespace(category=category, name=f"an{i}", value="{}", tags={})
            for i in range(2)
        ]

    async def insert(self, *args, **kwargs):
        return None

    async def replace(self, *args, **kwargs):
        return None

    async def remove(self, *args, **kwargs):
        return None

    async def remove_all(self, *args, **kwargs) -> int:
        return 2

    async def commit(self):
        return None

    async def rollback(self):
        return None

    async def close(self):
        return None

    def translate_error(self, e):
        return e


@pytest.mark.asyncio
async def test_async_scan_paths():
    store = DBStore(_AsyncDB(), uri="sqlite://:memory:")
    s = store.scan(category="c", limit=2, offset=0)
    items = [i async for i in s]
    assert [it.name for it in items] == ["an0", "an1"]

    ks = store.scan_keyset(category="c", last_id=1, limit=2)
    items = [i async for i in ks]
    assert [it.name for it in items] == ["ak2", "ak3"]
