import types
from typing import Any, Dict, Optional

import pytest

from acapy_agent.database_manager.dbstore import DBStoreError, DBStoreErrorCode


class FakeDBStoreHandle:
    def __init__(self):
        self._rows: Dict[tuple[str, str], Dict[str, Any]] = {}

    def insert(self, category: str, name: str, value: str, tags: Optional[dict] = None):
        key = (category, name)
        if key in self._rows:
            raise DBStoreError(DBStoreErrorCode.DUPLICATE, "duplicate")
        self._rows[key] = {
            "category": category,
            "name": name,
            "value": value,
            "tags": tags or {},
        }

    def fetch(self, category: str, name: str, for_update: bool = False):
        row = self._rows.get((category, name))
        if not row:
            return None
        return types.SimpleNamespace(
            category=row["category"],
            name=row["name"],
            value=row["value"],
            tags=row["tags"],
        )

    def replace(self, category: str, name: str, value: str, tags: dict):
        if (category, name) not in self._rows:
            raise DBStoreError(DBStoreErrorCode.NOT_FOUND, "not found")
        self._rows[(category, name)] = {
            "category": category,
            "name": name,
            "value": value,
            "tags": tags,
        }

    def remove(self, category: str, name: str):
        if (category, name) not in self._rows:
            raise DBStoreError(DBStoreErrorCode.NOT_FOUND, "not found")
        del self._rows[(category, name)]

    async def fetch_all(self, category: str, tag_filter: Optional[dict] = None, **kwargs):
        # simple filter implementation
        for (cat, _), row in self._rows.items():
            if cat != category:
                continue
            tags = row["tags"] or {}
            ok = True
            for k, v in (tag_filter or {}).items():
                if tags.get(k) != v:
                    ok = False
                    break
            if ok:
                yield types.SimpleNamespace(
                    category=row["category"],
                    name=row["name"],
                    value=row["value"],
                    tags=row["tags"],
                )

    def remove_all(self, category: str, tag_filter: Optional[dict] = None):
        to_delete = []
        for (cat, name), row in self._rows.items():
            if cat != category:
                continue
            tags = row["tags"] or {}
            ok = True
            for k, v in (tag_filter or {}).items():
                if tags.get(k) != v:
                    ok = False
                    break
            if ok:
                to_delete.append((cat, name))
        for key in to_delete:
            del self._rows[key]


class FakeStoreSession:
    def __init__(self, handle):
        self.handle = handle

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def fetch(self, *args, **kwargs):
        return await self.handle.fetch(*args, **kwargs)

    async def replace(self, *args, **kwargs):
        return await self.handle.replace(*args, **kwargs)

    async def insert(self, *args, **kwargs):
        return await self.handle.insert(*args, **kwargs)

    async def remove(self, *args, **kwargs):
        return await self.handle.remove(*args, **kwargs)

    async def fetch_all(self, *args, **kwargs):
        results = []
        async for row in self.handle.fetch_all(*args, **kwargs):
            results.append(row)
        return results

    async def remove_all(self, *args, **kwargs):
        return await self.handle.remove_all(*args, **kwargs)


class FakeProfile:
    def __init__(self):
        self._handle = FakeDBStoreHandle()
        self.store = self
        self.dbstore_handle = self._handle
        self.profile = types.SimpleNamespace(name="p")
        self.name = "p"

    def session(self):
        return FakeStoreSession(self._handle)

    @property
    def opened(self):
        return types.SimpleNamespace(db_store=self)

    def scan(
        self,
        *,
        category: str,
        tag_filter: Optional[dict] = None,
        limit: int = 10,
        offset: int = 0,
        profile: Optional[str] = None,
        order_by: Optional[str] = None,
        descending: bool = False,
    ):
        async def _gen():
            rows = []
            for (cat, name), row in self._handle._rows.items():
                if cat != category:
                    continue
                tags = row["tags"] or {}
                ok = True
                for k, v in (tag_filter or {}).items():
                    if tags.get(k) != v:
                        ok = False
                        break
                if ok:
                    rows.append(
                        types.SimpleNamespace(
                            category=cat, name=name, value=row["value"], tags=row["tags"]
                        )
                    )
            if order_by == "name":
                rows.sort(key=lambda r: r.name, reverse=descending)
            else:
                rows.sort(key=lambda r: r.name)
            _offset = offset or 0
            _limit = limit or len(rows)
            sliced = rows[_offset : _offset + _limit]
            for r in sliced:
                yield r

        return _gen()

    def scan_keyset(
        self,
        *,
        category: str,
        tag_filter: Optional[dict] = None,
        last_id: Optional[int] = None,
        limit: int = 10,
        profile: Optional[str] = None,
        order_by: Optional[str] = None,
        descending: bool = False,
    ):
        async def _gen():
            rows = [
                types.SimpleNamespace(
                    category=cat, name=name, value=row["value"], tags=row["tags"]
                )
                for (cat, name), row in self._handle._rows.items()
                if cat == category
            ]
            rows.sort(key=lambda r: r.name, reverse=descending)
            start = last_id or 0
            end = start + limit
            for r in rows[start:end]:
                yield r

        return _gen()


@pytest.mark.asyncio
async def test_add_get_update_delete_record_roundtrip():
    from acapy_agent.storage.kanon_storage import KanonStorage
    from acapy_agent.storage.record import StorageRecord

    profile = FakeProfile()
    storage = KanonStorage(profile)

    record = StorageRecord(type="config", id="pub", value='{"did": "D"}', tags={"k": "v"})

    await storage.add_record(record)

    got = await storage.get_record("config", "pub")
    assert got.value == record.value
    assert got.tags == {"k": "v"}

    await storage.update_record(record, value='{"did": "D2"}', tags={"k": "v2"})

    got2 = await storage.get_record("config", "pub")
    assert got2.value == '{"did": "D2"}'
    assert got2.tags == {"k": "v2"}

    # find_record path
    found = await storage.find_record("config", {"k": "v2"})
    assert found.id == "pub"

    # delete
    await storage.delete_record(record)
    with pytest.raises(Exception):
        await storage.get_record("config", "pub")


@pytest.mark.asyncio
async def test_find_paginated_records_and_keyset():
    from acapy_agent.storage.kanon_storage import KanonStorage
    from acapy_agent.storage.record import StorageRecord

    profile = FakeProfile()
    storage = KanonStorage(profile)

    for i in range(5):
        rec = StorageRecord(
            type="config",
            id=f"id{i}",
            value=f"v{i}",
            tags={"idx": str(i)},
        )
        await storage.add_record(rec)

    page = await storage.find_paginated_records(
        "config", limit=2, offset=1, order_by="name", descending=False
    )
    assert [r.id for r in page] == ["id1", "id2"]

    page1 = await storage.find_paginated_records_keyset(
        "config", limit=2, order_by="name", descending=False
    )
    assert [r.id for r in page1] == ["id0", "id1"]
    page2 = await storage.find_paginated_records_keyset(
        "config", last_id=2, limit=2, order_by="name", descending=False
    )
    assert [r.id for r in page2] == ["id2", "id3"]


@pytest.mark.asyncio
async def test_find_all_and_delete_all_and_search_session():
    from acapy_agent.storage.error import StorageSearchError
    from acapy_agent.storage.kanon_storage import KanonStorage, KanonStorageSearch
    from acapy_agent.storage.record import StorageRecord

    profile = FakeProfile()
    storage = KanonStorage(profile)

    for i in range(3):
        rec = StorageRecord(
            type="config",
            id=f"k{i}",
            value=f"v{i}",
            tags={"g": "1" if i % 2 == 0 else "2"},
        )
        await storage.add_record(rec)

    allrecs = await storage.find_all_records(
        "config", {"g": "1"}, order_by="name", descending=False
    )
    assert [r.id for r in allrecs] == ["k0", "k2"]

    search = KanonStorageSearch(profile)
    sess = search.search_records("config", {"g": "1"}, page_size=1)
    assert not sess.opened
    first = await sess.__anext__()
    assert first.id == "k0"
    got = await sess.fetch(max_count=2)
    if got:
        assert got[0].id == "k2"
    await sess.close()
    with pytest.raises(StorageSearchError):
        await sess.fetch(1)

    await storage.delete_all_records("config", {"g": "1"})
    remain = await storage.find_all_records("config", None)
    assert [r.id for r in remain] == ["k1"]


@pytest.mark.asyncio
async def test_storage_error_paths():
    from acapy_agent.storage.error import StorageDuplicateError, StorageNotFoundError
    from acapy_agent.storage.kanon_storage import KanonStorage
    from acapy_agent.storage.record import StorageRecord

    profile = FakeProfile()
    storage = KanonStorage(profile)

    rec = StorageRecord(type="t", id="a", value="v", tags={})
    await storage.add_record(rec)
    with pytest.raises(StorageDuplicateError):
        await storage.add_record(StorageRecord(type="t", id="a", value="v2", tags={}))

    with pytest.raises(StorageNotFoundError):
        await storage.get_record("t", "missing")

    with pytest.raises(StorageNotFoundError):
        await storage.update_record(
            StorageRecord(type="t", id="missing", value="v", tags={}), value="v2", tags={}
        )

    with pytest.raises(StorageNotFoundError):
        await storage.delete_record(
            StorageRecord(type="t", id="missing", value="v", tags={})
        )

    with pytest.raises(Exception):
        await storage.find_record("t", {"k": "v"})

    from acapy_agent.storage.error import StorageDuplicateError

    await storage.add_record(StorageRecord(type="t", id="b", value="v", tags={"k": "v"}))
    await storage.add_record(StorageRecord(type="t", id="c", value="v", tags={"k": "v"}))
    with pytest.raises(StorageDuplicateError):
        await storage.find_record("t", {"k": "v"})


@pytest.mark.asyncio
async def test_session_property_and_validations_and_error_mapping(monkeypatch):
    from acapy_agent.storage.error import StorageError
    from acapy_agent.storage.kanon_storage import KanonStorage
    from acapy_agent.storage.record import StorageRecord

    profile = FakeProfile()
    storage = KanonStorage(profile)

    assert storage.session is profile.dbstore_handle

    with pytest.raises(StorageError):
        await storage.get_record("", "id")
    with pytest.raises(StorageError):
        await storage.get_record("type", "")

    session = profile.session()
    rec = StorageRecord(type="x", id="one", value="v", tags={})
    await storage.add_record(rec, session=session)
    got = await storage.get_record("x", "one", session=session)
    assert got.id == "one"

    class BadSess(FakeStoreSession):
        async def fetch_all(self, *args, **kwargs):
            raise DBStoreError(DBStoreErrorCode.BUSY, "boom")

        async def __aenter__(self):
            return self

        async def __aexit__(self, et, ev, tb):
            return False

    def _bad_session():
        return BadSess(profile._handle)

    monkeypatch.setattr(profile, "session", _bad_session)
    with pytest.raises(StorageError):
        await storage.find_all_records("x", None)

    class BadDelSess(FakeStoreSession):
        async def remove_all(self, *args, **kwargs):
            raise DBStoreError(DBStoreErrorCode.BUSY, "fail")

        async def __aenter__(self):
            return self

        async def __aexit__(self, et, ev, tb):
            return False

    def _bad_del_session():
        return BadDelSess(profile._handle)

    monkeypatch.setattr(profile, "session", _bad_del_session)
    with pytest.raises(StorageError):
        await storage.delete_all_records("x", None)


@pytest.mark.asyncio
async def test_search_session_db_error(monkeypatch):
    from acapy_agent.storage.error import StorageSearchError
    from acapy_agent.storage.kanon_storage import KanonStorageSearch

    profile = FakeProfile()

    def _bad_scan(**kwargs):
        async def _gen():
            raise DBStoreError(DBStoreErrorCode.BUSY, "scan error")

        return _gen()

    monkeypatch.setattr(profile, "scan", _bad_scan)
    search = KanonStorageSearch(profile)
    sess = search.search_records("cat", {})
    with pytest.raises(StorageSearchError):
        await sess.__anext__()
