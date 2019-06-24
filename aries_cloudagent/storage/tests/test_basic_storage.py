import pytest

from aries_cloudagent.storage.error import (
    StorageDuplicateError,
    StorageError,
    StorageNotFoundError,
    StorageSearchError,
)

from aries_cloudagent.storage.record import StorageRecord

from aries_cloudagent.storage.basic import BasicStorage


@pytest.fixture()
def store():
    yield BasicStorage()


def test_record(tags={}):
    return StorageRecord(type="TYPE", value="TEST", tags=tags)


def test_missing_record(tags={}):
    return StorageRecord(type="__MISSING__", value="000000000")


class TestBasicStorage:
    @pytest.mark.asyncio
    async def test_add_required(self, store):
        with pytest.raises(StorageError):
            await store.add_record(None)

    @pytest.mark.asyncio
    async def test_add_id_required(self, store):
        record = test_record()._replace(id=None)
        with pytest.raises(StorageError):
            await store.add_record(record)

    @pytest.mark.asyncio
    async def test_retrieve_missing(self, store):
        missing = test_missing_record()
        with pytest.raises(StorageNotFoundError):
            await store.get_record(missing.type, missing.id)

    @pytest.mark.asyncio
    async def test_add_retrieve(self, store):
        record = test_record()
        await store.add_record(record)
        result = await store.get_record(record.type, record.id)
        assert result
        assert result.id == record.id
        assert result.type == record.type
        assert result.value == record.value
        assert result.tags == record.tags

        with pytest.raises(StorageDuplicateError):
            await store.add_record(record)

    @pytest.mark.asyncio
    async def test_delete(self, store):
        record = test_record()
        await store.add_record(record)
        await store.delete_record(record)
        with pytest.raises(StorageNotFoundError):
            await store.get_record(record.type, record.id)

    @pytest.mark.asyncio
    async def test_delete_missing(self, store):
        missing = test_missing_record()
        with pytest.raises(StorageNotFoundError):
            await store.delete_record(missing)

    @pytest.mark.asyncio
    async def test_update_value(self, store):
        init_value = "a"
        upd_value = "b"
        record = test_record()._replace(value=init_value)
        await store.add_record(record)
        assert record.value == init_value
        await store.update_record_value(record, upd_value)
        result = await store.get_record(record.type, record.id)
        assert result.value == upd_value

    @pytest.mark.asyncio
    async def test_update_missing(self, store):
        missing = test_missing_record()
        with pytest.raises(StorageNotFoundError):
            await store.update_record_value(missing, missing.value)

    @pytest.mark.asyncio
    async def test_update_tags(self, store):
        record = test_record({})
        assert record.tags == {}
        await store.add_record(record)
        await store.update_record_tags(record, {"a": "A"})
        result = await store.get_record(record.type, record.id)
        assert result.tags.get("a") == "A"

    @pytest.mark.asyncio
    async def test_update_tags_missing(self, store):
        missing = test_missing_record()
        with pytest.raises(StorageNotFoundError):
            await store.update_record_tags(missing, {})

    @pytest.mark.asyncio
    async def test_delete_tags(self, store):
        record = test_record({"a": "A"})
        await store.add_record(record)
        await store.delete_record_tags(record, {"a": "A"})
        result = await store.get_record(record.type, record.id)
        assert result.tags.get("a") is None

    @pytest.mark.asyncio
    async def test_delete_tags_missing(self, store):
        missing = test_missing_record()
        with pytest.raises(StorageNotFoundError):
            await store.delete_record_tags(missing, {"a": "A"})

    @pytest.mark.asyncio
    async def test_search(self, store):
        record = test_record()
        await store.add_record(record)
        search = store.search_records(record.type, {}, None)
        await search.open()
        rows = await search.fetch(100)
        assert len(rows) == 1
        found = rows[0]
        assert found.id == record.id
        assert found.type == record.type
        assert found.value == record.value
        assert found.tags == record.tags
        more = await search.fetch(100)
        assert len(more) == 0

    @pytest.mark.asyncio
    async def test_iter_search(self, store):
        record = test_record()
        await store.add_record(record)
        count = 0
        search = store.search_records(record.type, {}, None)
        async for found in search:
            assert found.id == record.id
            assert found.type == record.type
            assert found.value == record.value
            assert found.tags == record.tags
            count += 1
        assert count == 1

    @pytest.mark.asyncio
    async def test_closed_search(self, store):
        search = store.search_records("TYPE", {}, None)
        with pytest.raises(StorageSearchError):
            await search.fetch(100)
