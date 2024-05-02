import pytest


from ....askar.profile import AskarProfileManager
from ....config.injection_context import InjectionContext

from ..base import VCHolder
from ..vc_record import VCRecord

from . import test_in_memory_vc_holder as in_memory


async def make_profile():
    context = InjectionContext()
    profile = await AskarProfileManager().provision(
        context,
        {
            # "auto_recreate": True,
            # "auto_remove": True,
            "name": ":memory:",
            "key": await AskarProfileManager.generate_store_key(),
            "key_derivation_method": "RAW",  # much faster than using argon-hashed keys
        },
    )
    return profile


@pytest.fixture()
async def holder():
    profile = await make_profile()
    yield profile.inject(VCHolder)
    await profile.close()


@pytest.mark.askar
class TestAskarVCHolder(in_memory.TestInMemoryVCHolder):
    # run same test suite with different holder fixture

    @pytest.mark.asyncio
    async def test_tag_query(self, holder: VCHolder, record: VCRecord):
        test_uri_list = [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://example.org/examples#UniversityDegreeCredential",
        ]
        test_query = holder.build_type_or_schema_query(test_uri_list)
        assert test_query == {
            "$and": [
                {
                    "$or": [
                        {
                            "type": "https://www.w3.org/2018/credentials#VerifiableCredential"
                        },
                        {
                            "schema": "https://www.w3.org/2018/credentials#VerifiableCredential"
                        },
                    ]
                },
                {
                    "$or": [
                        {
                            "type": "https://example.org/examples#UniversityDegreeCredential"
                        },
                        {
                            "schema": "https://example.org/examples#UniversityDegreeCredential"
                        },
                    ]
                },
            ]
        }
        await holder.store_credential(record)

        search = holder.search_credentials(pd_uri_list=test_uri_list)
        rows = await search.fetch()
        assert rows == [record]
