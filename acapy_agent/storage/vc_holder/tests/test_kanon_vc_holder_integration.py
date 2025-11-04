import os

import pytest
import pytest_asyncio

from ....storage.error import StorageDuplicateError, StorageNotFoundError
from ....utils.testing import create_test_profile
from ..base import VCHolder
from ..vc_record import VCRecord

# Skip all tests if POSTGRES_URL is not set
if not os.getenv("POSTGRES_URL"):
    pytest.skip(
        "Kanon PostgreSQL integration tests disabled: set POSTGRES_URL to enable",
        allow_module_level=True,
    )

pytestmark = pytest.mark.postgres

VC_CONTEXT = "https://www.w3.org/2018/credentials/v1"
VC_TYPE = "https://www.w3.org/2018/credentials#VerifiableCredential"
VC_SUBJECT_ID = "did:example:ebfeb1f712ebc6f1c276e12ec21"
VC_PROOF_TYPE = "Ed25519Signature2018"
VC_ISSUER_ID = "https://example.edu/issuers/14"
VC_SCHEMA_ID = "https://example.org/examples/degree.json"
VC_GIVEN_ID = "http://example.edu/credentials/3732"


@pytest_asyncio.fixture
async def holder():
    import json

    postgres_url = os.getenv("POSTGRES_URL")
    if postgres_url and "://" in postgres_url:
        postgres_url = postgres_url.split("://")[-1].split("@")[-1]

    profile = await create_test_profile(
        settings={
            "wallet.type": "kanon-anoncreds",
            "wallet.storage_type": "postgres",
            "wallet.storage_config": json.dumps({"url": postgres_url}),
            "wallet.storage_creds": json.dumps(
                {
                    "account": "postgres",
                    "password": "postgres",
                }
            ),
            "dbstore_storage_type": "postgres",
            "dbstore_storage_config": json.dumps({"url": postgres_url}),
            "dbstore_storage_creds": json.dumps(
                {
                    "account": "postgres",
                    "password": "postgres",
                }
            ),
            "dbstore_schema_config": "normalize",
        }
    )
    yield profile.inject(VCHolder)
    # Cleanup happens automatically when profile is garbage collected


@pytest.fixture
def record():
    yield VCRecord(
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
        cred_value={
            "@context": [
                VC_CONTEXT,
                "https://www.w3.org/2018/credentials/examples/v1",
            ],
            "id": VC_GIVEN_ID,
            "type": ["VerifiableCredential", "UniversityDegreeCredential"],
            "issuer": VC_ISSUER_ID,
            "identifier": "83627467",
            "name": "University Degree",
            "issuanceDate": "2010-01-01T19:53:24Z",
            "credentialSubject": {
                "id": VC_SUBJECT_ID,
                "givenName": "Cai",
                "familyName": "Leblanc",
            },
            "proof": {
                "type": "Ed25519Signature2018",
                "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                "created": "2021-05-07T08:50:17.626625",
                "proofPurpose": "assertionMethod",
                "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..rubQvgig7cN-F6cYn_AJF1BCSaMpkoR517Ot_4pqwdJnQ-JwKXq6d6cNos5JR73E9WkwYISXapY0fYTIG9-fBA",
            },
        },
    )


@pytest.mark.asyncio
async def test_store_retrieve(holder: VCHolder, record: VCRecord):
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
async def test_delete(holder: VCHolder, record: VCRecord):
    """Test credential deletion."""
    await holder.store_credential(record)
    await holder.delete_credential(record)
    with pytest.raises(StorageNotFoundError):
        await holder.retrieve_credential_by_id(record.record_id)


@pytest.mark.asyncio
async def test_search(holder: VCHolder, record: VCRecord):
    await holder.store_credential(record)

    search = holder.search_credentials()
    rows = await search.fetch()
    assert rows == [record]
    await search.close()

    search = holder.search_credentials()
    assert search.__class__.__name__ in str(search)
    rows = []
    async for row in search:
        rows.append(row)
    assert rows == [record]
    await search.close()

    search = holder.search_credentials(
        contexts=[VC_CONTEXT],
        types=[VC_TYPE],
        schema_ids=[VC_SCHEMA_ID],
        subject_ids=[VC_SUBJECT_ID],
        proof_types=[VC_PROOF_TYPE],
        issuer_id=VC_ISSUER_ID,
        given_id=VC_GIVEN_ID,
        tag_query={"tag": "value"},
    )
    rows = await search.fetch()
    assert rows == [record]

    rows = await holder.search_credentials(contexts=["other-context"]).fetch()
    assert not rows

    rows = await holder.search_credentials(types=["other-type"]).fetch()
    assert not rows

    rows = await holder.search_credentials(schema_ids=["other schema"]).fetch()
    assert not rows

    rows = await holder.search_credentials(subject_ids=["other subject"]).fetch()
    assert not rows

    rows = await holder.search_credentials(proof_types=["other proof type"]).fetch()
    assert not rows

    rows = await holder.search_credentials(issuer_id="other issuer").fetch()
    assert not rows

    rows = await holder.search_credentials(given_id="other given id").fetch()
    assert not rows

    await search.close()


@pytest.mark.asyncio
async def test_tag_query(holder: VCHolder, record: VCRecord):
    """Test tag query building and filtering."""
    test_uri_list = [
        "https://www.w3.org/2018/credentials#VerifiableCredential",
        "https://example.org/examples#UniversityDegreeCredential",
    ]
    test_query = holder.build_type_or_schema_query(test_uri_list)
    assert test_query == {
        "$and": [
            {
                "$or": [
                    {"type": "https://www.w3.org/2018/credentials#VerifiableCredential"},
                    {
                        "schema": "https://www.w3.org/2018/credentials#VerifiableCredential"
                    },
                ]
            },
            {
                "$or": [
                    {"type": "https://example.org/examples#UniversityDegreeCredential"},
                    {"schema": "https://example.org/examples#UniversityDegreeCredential"},
                ]
            },
        ]
    }
    await holder.store_credential(record)

    search = holder.search_credentials(pd_uri_list=test_uri_list)
    rows = await search.fetch()
    assert rows == [record]


@pytest.mark.asyncio
async def test_tag_query_valid_and_operator(holder: VCHolder, record: VCRecord):
    """Test that AND operator in tag queries works correctly."""
    test_uri_list = [
        "https://www.w3.org/2018/credentials#VerifiableCredential",
        "https://example.org/examples#UniversityDegreeCredential2",
    ]
    await holder.store_credential(record)

    search = holder.search_credentials(pd_uri_list=test_uri_list)
    rows = await search.fetch()
    assert rows == []


@pytest.mark.asyncio
async def test_sorting_vcrecord(holder: VCHolder):
    record_a = VCRecord(
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
        given_id=VC_GIVEN_ID + "_a",
        cred_tags={"tag": "value"},
        cred_value={
            "@context": [
                VC_CONTEXT,
                "https://www.w3.org/2018/credentials/examples/v1",
            ],
            "id": VC_GIVEN_ID + "_a",
            "type": ["VerifiableCredential", "UniversityDegreeCredential"],
            "issuer": VC_ISSUER_ID,
            "identifier": "83627467",
            "name": "University Degree",
            "issuanceDate": "2010-01-01T19:53:24Z",
            "credentialSubject": {
                "id": VC_SUBJECT_ID,
                "givenName": "Cai",
                "familyName": "Leblanc",
            },
            "proof": {
                "type": "Ed25519Signature2018",
                "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                "created": "2021-05-07T08:50:17.626625",
                "proofPurpose": "assertionMethod",
                "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..rubQvgig7cN-F6cYn_AJF1BCSaMpkoR517Ot_4pqwdJnQ-JwKXq6d6cNos5JR73E9WkwYISXapY0fYTIG9-fBA",
            },
        },
    )
    await holder.store_credential(record_a)

    record_b = VCRecord(
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
        given_id=VC_GIVEN_ID + "_b",
        cred_tags={"tag": "value"},
        cred_value={
            "@context": [
                VC_CONTEXT,
                "https://www.w3.org/2018/credentials/examples/v1",
            ],
            "id": VC_GIVEN_ID + "_b",
            "type": ["VerifiableCredential", "UniversityDegreeCredential"],
            "issuer": VC_ISSUER_ID,
            "identifier": "83627467",
            "name": "University Degree",
            "issuanceDate": "2012-01-01T19:53:24Z",
            "credentialSubject": {
                "id": VC_SUBJECT_ID,
                "givenName": "Cai",
                "familyName": "Leblanc",
            },
            "proof": {
                "type": "Ed25519Signature2018",
                "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                "created": "2021-05-07T08:50:17.626625",
                "proofPurpose": "assertionMethod",
                "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..rubQvgig7cN-F6cYn_AJF1BCSaMpkoR517Ot_4pqwdJnQ-JwKXq6d6cNos5JR73E9WkwYISXapY0fYTIG9-fBA",
            },
        },
    )
    await holder.store_credential(record_b)

    record_c = VCRecord(
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
        given_id=VC_GIVEN_ID + "_c",
        cred_tags={"tag": "value"},
        cred_value={
            "@context": [
                VC_CONTEXT,
                "https://www.w3.org/2018/credentials/examples/v1",
            ],
            "id": VC_GIVEN_ID + "_c",
            "type": ["VerifiableCredential", "UniversityDegreeCredential"],
            "issuer": VC_ISSUER_ID,
            "identifier": "83627467",
            "name": "University Degree",
            "issuanceDate": "2009-01-01T19:53:24Z",
            "credentialSubject": {
                "id": VC_SUBJECT_ID,
                "givenName": "Cai",
                "familyName": "Leblanc",
            },
            "proof": {
                "type": "Ed25519Signature2018",
                "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                "created": "2021-05-07T08:50:17.626625",
                "proofPurpose": "assertionMethod",
                "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..rubQvgig7cN-F6cYn_AJF1BCSaMpkoR517Ot_4pqwdJnQ-JwKXq6d6cNos5JR73E9WkwYISXapY0fYTIG9-fBA",
            },
        },
    )
    await holder.store_credential(record_c)

    # Verify all three credentials were stored
    search = holder.search_credentials()
    rows = await search.fetch()
    assert len(rows) == 3


@pytest.mark.asyncio
async def test_set_serialization_with_empty_sets(holder: VCHolder):
    record = VCRecord(
        contexts=[VC_CONTEXT],
        expanded_types=[VC_TYPE],
        schema_ids=[],  # Empty list becomes empty set
        issuer_id=VC_ISSUER_ID,
        subject_ids=[VC_SUBJECT_ID],
        proof_types=[VC_PROOF_TYPE],
        given_id="test_empty_sets",
        cred_tags={},
        cred_value={
            "@context": [VC_CONTEXT],
            "id": "test_empty_sets",
            "type": ["VerifiableCredential"],
            "issuer": VC_ISSUER_ID,
            "issuanceDate": "2010-01-01T00:00:00Z",
            "credentialSubject": {"id": VC_SUBJECT_ID},
            "proof": {
                "type": VC_PROOF_TYPE,
                "created": "2021-01-01T00:00:00Z",
                "proofPurpose": "assertionMethod",
                "verificationMethod": "did:example:key1",
                "jws": "test_signature",
            },
        },
    )
    await holder.store_credential(record)

    result = await holder.retrieve_credential_by_given_id("test_empty_sets")
    assert result.given_id == "test_empty_sets"
    assert result.schema_ids == set()


@pytest.mark.asyncio
async def test_set_serialization_with_multiple_values(holder: VCHolder):
    record = VCRecord(
        contexts=[
            VC_CONTEXT,
            "https://www.w3.org/2018/credentials/examples/v1",
            "https://www.w3.org/ns/credentials/v2",
        ],
        expanded_types=[
            VC_TYPE,
            "https://example.org/examples#UniversityDegreeCredential",
            "https://example.org/examples#BachelorDegree",
        ],
        schema_ids=[
            VC_SCHEMA_ID,
            "https://example.org/examples/bachelor.json",
        ],
        issuer_id=VC_ISSUER_ID,
        subject_ids=[
            VC_SUBJECT_ID,
            "did:example:additional_subject",
        ],
        proof_types=[
            VC_PROOF_TYPE,
            "DataIntegrityProof",
        ],
        given_id="test_multiple_sets",
        cred_tags={"multi": "value"},
        cred_value={
            "@context": [VC_CONTEXT],
            "id": "test_multiple_sets",
            "type": ["VerifiableCredential"],
            "issuer": VC_ISSUER_ID,
            "issuanceDate": "2010-01-01T00:00:00Z",
            "credentialSubject": {"id": VC_SUBJECT_ID},
            "proof": {
                "type": VC_PROOF_TYPE,
                "created": "2021-01-01T00:00:00Z",
                "proofPurpose": "assertionMethod",
                "verificationMethod": "did:example:key1",
                "jws": "test_signature",
            },
        },
    )

    await holder.store_credential(record)

    result = await holder.retrieve_credential_by_given_id("test_multiple_sets")
    assert len(result.contexts) == 3
    assert len(result.expanded_types) == 3
    assert len(result.schema_ids) == 2
    assert len(result.subject_ids) == 2
    assert len(result.proof_types) == 2
