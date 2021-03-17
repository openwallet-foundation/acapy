import pytest

from ....core.in_memory import InMemoryProfile
from ...error import (
    StorageDuplicateError,
    StorageNotFoundError,
)

from ..base import VCHolder
from ..in_memory import InMemoryVCHolder
from ..vc_record import VCRecord


VC_CONTEXT = "https://www.w3.org/2018/credentials/v1"
VC_TYPE = "https://www.w3.org/2018/credentials/v1/VerifiableCredential"
VC_SUBJECT_ID = "did:example:ebfeb1f712ebc6f1c276e12ec21"
VC_ISSUER_ID = "https://example.edu/issuers/14"
VC_SCHEMA_ID = "https://example.org/examples/degree.json"
VC_GIVEN_ID = "http://example.edu/credentials/3732"


@pytest.fixture()
def holder():
    profile = InMemoryProfile.test_profile()
    yield profile.inject(VCHolder)


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
        schema_ids=[VC_SCHEMA_ID],
        issuer_id=VC_ISSUER_ID,
        subject_ids=[VC_SUBJECT_ID],
        given_id=VC_GIVEN_ID,
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
        assert result == record

        result = await holder.retrieve_credential_by_given_id(record.given_id)
        assert result == record

        with pytest.raises(StorageDuplicateError):
            await holder.store_credential(record)

        with pytest.raises(StorageNotFoundError):
            await holder.retrieve_credential_by_id("missing")

        with pytest.raises(StorageNotFoundError):
            await holder.retrieve_credential_by_given_id("missing")

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

        # test async iter and repr
        search = holder.search_credentials()
        assert search.__class__.__name__ in str(search)
        rows = []
        async for row in search:
            rows.append(row)
        assert rows == [record]

        rows = await holder.search_credentials(
            contexts=[VC_CONTEXT],
            types=[VC_TYPE],
            schema_ids=[VC_SCHEMA_ID],
            subject_id=VC_SUBJECT_ID,
            issuer_id=VC_ISSUER_ID,
        ).fetch()
        assert rows == [record]

        rows = await holder.search_credentials(contexts=["other-context"]).fetch()
        assert not rows

        rows = await holder.search_credentials(types=["other-type"]).fetch()
        assert not rows

        rows = await holder.search_credentials(schema_ids=["other schema"]).fetch()
        assert not rows

        rows = await holder.search_credentials(subject_id="other subject").fetch()
        assert not rows

        rows = await holder.search_credentials(issuer_id="other issuer").fetch()
        assert not rows
