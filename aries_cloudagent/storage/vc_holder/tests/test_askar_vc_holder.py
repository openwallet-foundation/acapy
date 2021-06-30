import pytest


from ....askar.profile import AskarProfileManager
from ....config.injection_context import InjectionContext

from ..base import VCHolder
from ..vc_record import VCRecord

from . import test_in_memory_vc_holder as in_memory


VC_CONTEXT = "https://www.w3.org/2018/credentials/v1"
VC_TYPE = "https://www.w3.org/2018/credentials#VerifiableCredential"
VC_SUBJECT_ID = "did:example:ebfeb1f712ebc6f1c276e12ec21"
VC_PROOF_TYPE = "Ed25519Signature2018"
VC_ISSUER_ID = "https://example.edu/issuers/14"
VC_SCHEMA_ID = "https://example.org/examples/degree.json"
VC_GIVEN_ID = "http://example.edu/credentials/3732"


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


def test_record() -> VCRecord:
    return VCRecord(
        contexts=[
            VC_CONTEXT,
            "https://www.w3.org/2018/credentials/examples/v1",
        ],
        expanded_types=[
            VC_TYPE,
            "https://example.org/examples#UniversityDegreeCredential",
        ],
        schema_ids=[VC_SCHEMA_ID],
        issuer_id=VC_ISSUER_ID,
        subject_ids=[VC_SUBJECT_ID],
        proof_types=[VC_PROOF_TYPE],
        given_id=VC_GIVEN_ID,
        cred_tags={"tag": "value"},
        cred_value={"...": "..."},
    )


@pytest.mark.indy
class TestAskarVCHolder(in_memory.TestInMemoryVCHolder):
    # run same test suite with different holder fixture

    @pytest.mark.asyncio
    async def test_tag_query(self, holder: VCHolder):
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
        record = test_record()
        await holder.store_credential(record)

        search = holder.search_credentials(pd_uri_list=test_uri_list)
        rows = await search.fetch()
        assert rows == [record]
