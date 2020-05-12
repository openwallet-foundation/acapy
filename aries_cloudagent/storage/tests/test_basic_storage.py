import pytest

from asynctest import mock as async_mock

from aries_cloudagent.storage.error import (
    StorageDuplicateError,
    StorageError,
    StorageNotFoundError,
    StorageSearchError,
)

from aries_cloudagent.storage.indy import IndyStorageRecordSearch
from aries_cloudagent.storage.basic import (
    BasicStorage,
    basic_tag_value_match,
    basic_tag_query_match,
)
from aries_cloudagent.storage.record import StorageRecord


@pytest.fixture()
def store():
    yield BasicStorage()


def test_record(tags={}):
    return StorageRecord(type="TYPE", value="TEST", tags=tags)


def test_missing_record(tags={}):
    return StorageRecord(type="__MISSING__", value="000000000")


class TestBasicStorage:
    def test_repr(self, store):
        assert store.__class__.__name__ in str(store)

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

        # search
        search = store.search_records(record.type, {}, None)
        assert search.__class__.__name__ in str(search)
        assert search.handle is None or isinstance(search, IndyStorageRecordSearch)
        assert not search.options
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

        # search again with fetch-all
        search = store.search_records(record.type, {}, None)
        await search.open()
        rows = await search.fetch_all()
        assert len(rows) == 1

        # search again with with iterator mystery error
        search = store.search_records(record.type, {}, None)
        with async_mock.patch.object(
            search, "fetch", async_mock.CoroutineMock()
        ) as mock_fetch:
            mock_fetch.return_value = async_mock.MagicMock(
                pop=async_mock.MagicMock(side_effect=IndexError())
            )
            with pytest.raises(StopAsyncIteration):
                await search.__anext__()

        # search again with fetch-single
        search = store.search_records(record.type, {}, None)
        await search.open()
        row = await search.fetch_single()
        assert row

        # search again with fetch-single on no rows
        search = store.search_records("NOT-MY-TYPE", {}, None)
        await search.open()
        with pytest.raises(StorageNotFoundError):
            await search.fetch_single()

        # search again with fetch-single on multiple rows
        record = test_record()
        await store.add_record(record)
        search = store.search_records(record.type, {}, None)
        async with search as s:
            with pytest.raises(StorageDuplicateError):
                await s.fetch_single()

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

    @pytest.mark.asyncio
    async def test_basic_tag_value_match(self, store):
        TAGS = {"a": "aardvark", "b": "bear", "z": "0"}
        record = test_record(TAGS)
        await store.add_record(record)

        assert not basic_tag_value_match(None, {"$neq": "octopus"})
        assert not basic_tag_value_match(TAGS["a"], {"$in": ["cat", "dog"]})
        assert basic_tag_value_match(TAGS["a"], {"$neq": "octopus"})
        assert basic_tag_value_match(TAGS["z"], {"$gt": "-0.5"})
        assert basic_tag_value_match(TAGS["z"], {"$gte": "0"})
        assert basic_tag_value_match(TAGS["z"], {"$lt": "1"})
        assert basic_tag_value_match(TAGS["z"], {"$lte": "0"})

        with pytest.raises(StorageSearchError) as excinfo:
            basic_tag_value_match(TAGS["z"], {"$gt": "-1", "$lt": "1"})
        assert "Unsupported subquery" in str(excinfo.value)

        with pytest.raises(StorageSearchError) as excinfo:
            basic_tag_value_match(TAGS["a"], {"$in": "aardvark"})
        assert "Expected list" in str(excinfo.value)

        with pytest.raises(StorageSearchError) as excinfo:
            basic_tag_value_match(TAGS["z"], {"$gte": -1})
        assert "Expected string" in str(excinfo.value)

        with pytest.raises(StorageSearchError) as excinfo:
            basic_tag_value_match(TAGS["z"], {"$near": "-1"})
        assert "Unsupported match operator" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_basic_tag_query_match(self, store):
        TAGS = {"a": "aardvark", "b": "bear", "z": "0"}
        record = test_record(TAGS)
        await store.add_record(record)

        assert basic_tag_query_match(None, None)
        assert not basic_tag_query_match(None, {"a": "aardvark"})
        assert basic_tag_query_match(
            TAGS, {"$or": [{"a": "aardvark"}, {"a": "alligator"}]}
        )
        assert basic_tag_query_match(TAGS, {"$not": {"a": "alligator"}})
        assert basic_tag_query_match(TAGS, {"z": {"$gt": "-1"}})

        with pytest.raises(StorageSearchError) as excinfo:
            basic_tag_query_match(TAGS, {"$or": "-1"})
        assert "Expected list" in str(excinfo.value)

        with pytest.raises(StorageSearchError) as excinfo:
            basic_tag_query_match(TAGS, {"$not": [{"z": "-1"}, {"z": "1"}]})
        assert "Expected dict for $not filter value" in str(excinfo.value)

        with pytest.raises(StorageSearchError) as excinfo:
            basic_tag_query_match(TAGS, {"$near": {"z": "-1"}})
        assert "Unexpected filter operator" in str(excinfo.value)

        with pytest.raises(StorageSearchError) as excinfo:
            basic_tag_query_match(TAGS, {"a": -1})
        assert "Expected string or dict for filter value" in str(excinfo.value)
