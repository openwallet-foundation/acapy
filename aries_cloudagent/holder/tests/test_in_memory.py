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

from ..in_memory import InMemoryVCHolder
from ..models.vc_record import VCRecord
from ..vc_holder import VCHolder


VC_CONTEXT = "https://www.w3.org/2018/credentials/v1"
VC_TYPE = "https://www.w3.org/2018/credentials/v1/VerifiableCredential"


@pytest.fixture()
def holder():
    profile = InMemoryProfile.test_profile()
    yield InMemoryVCHolder(profile)


@pytest.fixture()
def store_search():
    profile = InMemoryProfile.test_profile()
    yield InMemoryStorage(profile)


def test_record(tags={}) -> VCRecord:
    return VCRecord(
        contexts=[
            VC_CONTEXT,
            "https://www.w3.org/2018/credentials/examples/v1",
        ],
        types=[
            VC_TYPE,
            "https://www.w3.org/2018/credentials/examples/v1/UniversityDegreeCredential",
        ],
        issuer_id="https://example.edu/issuers/14",
        subject_ids=["did:example:ebfeb1f712ebc6f1c276e12ec21"],
        given_id="http://example.edu/credentials/3732",
        tags={"tag": "value"},
        value="{}",
    )


class TestInMemoryVCHolder:
    def test_repr(self, holder):
        assert holder.__class__.__name__ in str(holder)

    @pytest.mark.asyncio
    async def test_store_retrieve(self, holder: VCHolder):
        record = test_record()
        await holder.store_credential(record)
        result = await holder.retrieve_credential_by_id(record.record_id)
        assert result
        assert result.contexts == record.contexts
        assert result.types == record.types
        assert result.record_id == record.record_id
        assert result.issuer_id == record.issuer_id
        assert result.subject_ids == record.subject_ids
        assert result.value == record.value
        assert result.tags == record.tags

        with pytest.raises(StorageDuplicateError):
            await holder.store_credential(record)

    @pytest.mark.asyncio
    async def test_delete(self, holder: VCHolder):
        record = test_record()
        await holder.store_credential(record)
        await holder.delete_credential(record)
        with pytest.raises(StorageNotFoundError):
            await holder.retrieve_credential_by_id(record.record_id)

    @pytest.mark.asyncio
    async def test_search(self, holder: VCHolder):
        record = test_record()
        await holder.store_credential(record)

        rows = await holder.search_credentials().fetch()
        assert rows == [record]

        rows = await holder.search_credentials(contexts=[VC_CONTEXT]).fetch()
        assert rows == [record]

        rows = await holder.search_credentials(contexts=["missing"]).fetch()
        assert not rows

        # rows = await store.find_all_records(record.type, {}, None)
        # assert len(rows) == 1
        # found = rows[0]
        # assert found.id == record.id
        # assert found.type == record.type
        # assert found.value == record.value
        # assert found.tags == record.tags
