import pytest

from asynctest import mock as async_mock

from ...core.in_memory import InMemoryProfile
from ...storage.error import (
    StorageDuplicateError,
    StorageError,
    StorageNotFoundError,
    StorageSearchError,
)
from ...storage.in_memory import (
    InMemoryStorage,
    tag_value_match,
    tag_query_match,
)
from ...storage.record import StorageRecord


@pytest.fixture()
def store():
    profile = InMemoryProfile.test_profile()
    yield InMemoryStorage(profile)


def test_record(tags={}):
    return StorageRecord(type="TYPE", value="TEST", tags=tags)


def test_missing_record(tags={}):
    return StorageRecord(type="__MISSING__", value="000000000")


class TestInMemoryStorage:
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
    async def test_update_record(self, store):
        init_value = "a"
        init_tags = {"a": "a", "b": "b"}
        upd_value = "b"
        upd_tags = {"a": "A", "c": "C"}
        record = test_record(init_tags)._replace(value=init_value)
        await store.add_record(record)
        assert record.value == init_value
        assert record.tags == init_tags
        await store.update_record(record, upd_value, upd_tags)
        result = await store.get_record(record.type, record.id)
        assert result.value == upd_value
        assert result.tags == upd_tags

    @pytest.mark.asyncio
    async def test_update_missing(self, store):
        missing = test_missing_record()
        with pytest.raises(StorageNotFoundError):
            await store.update_record(missing, missing.value, {})

    @pytest.mark.asyncio
    async def test_search(self, store):
        record = test_record()
        await store.add_record(record)

        # search
        search = store.search_records(record.type, {}, None)
        assert search.__class__.__name__ in str(search)
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
            async for row in search:
                pytest.fail("Should not arrive here")

        # search with find_record
        row = await store.find_record(record.type, {}, None)
        assert row

        # search again with find_record on no rows
        with pytest.raises(StorageNotFoundError):
            _ = await store.find_record("NOT-MY-TYPE", {}, None)

        # search again with find_row on multiple rows
        record = test_record()
        await store.add_record(record)
        with pytest.raises(StorageDuplicateError):
            await store.find_record(record.type, {}, None)

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
        _rows = await search.fetch_all()
        with pytest.raises(StorageSearchError):
            await search.fetch(100)

    @pytest.mark.asyncio
    async def test_tag_value_match(self, store):
        TAGS = {"a": "aardvark", "b": "bear", "z": "0"}
        record = test_record(TAGS)
        await store.add_record(record)

        assert not tag_value_match(None, {"$neq": "octopus"})
        assert not tag_value_match(TAGS["a"], {"$in": ["cat", "dog"]})
        assert tag_value_match(TAGS["a"], {"$neq": "octopus"})
        assert tag_value_match(TAGS["z"], {"$gt": "-0.5"})
        assert tag_value_match(TAGS["z"], {"$gte": "0"})
        assert tag_value_match(TAGS["z"], {"$lt": "1"})
        assert tag_value_match(TAGS["z"], {"$lte": "0"})

        with pytest.raises(StorageSearchError) as excinfo:
            tag_value_match(TAGS["z"], {"$gt": "-1", "$lt": "1"})
        assert "Unsupported subquery" in str(excinfo.value)

        with pytest.raises(StorageSearchError) as excinfo:
            tag_value_match(TAGS["a"], {"$in": "aardvark"})
        assert "Expected list" in str(excinfo.value)

        with pytest.raises(StorageSearchError) as excinfo:
            tag_value_match(TAGS["z"], {"$gte": -1})
        assert "Expected string" in str(excinfo.value)

        with pytest.raises(StorageSearchError) as excinfo:
            tag_value_match(TAGS["z"], {"$near": "-1"})
        assert "Unsupported match operator" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_tag_query_match(self, store):
        TAGS = {"a": "aardvark", "b": "bear", "z": "0"}
        record = test_record(TAGS)
        await store.add_record(record)

        assert tag_query_match(None, None)
        assert not tag_query_match(None, {"a": "aardvark"})
        assert tag_query_match(TAGS, {"$or": [{"a": "aardvark"}, {"a": "alligator"}]})
        assert tag_query_match(TAGS, {"$not": {"a": "alligator"}})
        assert tag_query_match(TAGS, {"z": {"$gt": "-1"}})

        with pytest.raises(StorageSearchError) as excinfo:
            tag_query_match(TAGS, {"$or": "-1"})
        assert "Expected list" in str(excinfo.value)

        with pytest.raises(StorageSearchError) as excinfo:
            tag_query_match(TAGS, {"$not": [{"z": "-1"}, {"z": "1"}]})
        assert "Expected dict for $not filter value" in str(excinfo.value)

        with pytest.raises(StorageSearchError) as excinfo:
            tag_query_match(TAGS, {"$near": {"z": "-1"}})
        assert "Unexpected filter operator" in str(excinfo.value)

        with pytest.raises(StorageSearchError) as excinfo:
            tag_query_match(TAGS, {"a": -1})
        assert "Expected string or dict for filter value" in str(excinfo.value)
