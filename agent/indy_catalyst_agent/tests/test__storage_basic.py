import pytest

from indy_catalyst_agent.storage import StorageRecord
from indy_catalyst_agent.storage.basic import BasicStorage

@pytest.fixture()
def store():
    yield BasicStorage()

def test_record(tags={}):
    return StorageRecord(type='type', value='test', tags=tags)

class TestBasicStorage:

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

    @pytest.mark.asyncio
    async def test_search(self, store):
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
        assert count is 1

    @pytest.mark.asyncio
    async def test_delete(self, store):
        record = test_record()
        await store.add_record(record)
        await store.delete_record(record)
        result = await store.get_record(record.type, record.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_tags(self, store):
        record = test_record({})
        assert record.tags == {}
        await store.add_record(record)
        await store.update_record_tags(record, {'a': 1})
        result = await store.get_record(record.type, record.id)
        assert result.tags.get('a') is 1
