from typing import Callable

import pytest

from ....messaging.models.base import BaseModelError

from ..vc_record import VCRecord


sample_json_cred_1 = """
    {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "id": "https://eu.com/claims/DriversLicense",
        "type": ["EUDriversLicense"],
        "issuer": "did:example:123",
        "issuanceDate": "2010-01-01T19:73:24Z",
        "credentialSchema": {
            "id": "https://eu.com/claims/DriversLicense.json",
            "type": "JsonSchemaValidator2018"
        },
        "credentialSubject": {
            "id": "did:example:ebfeb1f712ebc6f1c276e12ec21",
            "accounts": [
            {
                "id": "1234567890",
                "route": "DE-9876543210"
            },
            {
                "id": "2457913570",
                "route": "DE-0753197542"
            }
            ]
        },
        "proof": {
            "type": "RsaSignature2018",
            "created": "2017-06-18T21:19:10Z",
            "proofPurpose": "assertionMethod",
            "verificationMethod": "https://example.edu/issuers/keys/1",
            "jws": "eyJhbGciOiJSUzI1NiIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..TCYt5XsITJX1CxPCT8yAV-TVkIEq_PbChOMqsLfRoPsnsgw5WEuts01mq-pQy7UJiN5mgRxD-WUcX16dUEMGlv50aqzpqh4Qktb3rk-BuQy72IFLOqV0G_zS245-kronKb78cPN25DGlcTwLtjPAYuNzVBAh4vGHSrQyHUdBBPM"
        }
    }
"""
sample_json_cred_2 = """
    {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://www.w3.org/2018/credentials/examples/v1"
        ],
        "id": "http://example.edu/credentials/1872",
        "type": ["VerifiableCredential", "AlumniCredential"],
        "issuer": {
            "id": "https://example.edu/issuers/565049"
        },
        "issuanceDate": "2011-01-01T19:73:24Z",
        "credentialSchema": [
            {
                "id": "https://example.org/examples/degree.json",
                "type": "JsonSchemaValidator2018"
            }
        ],
        "credentialSubject": [
            {
                "id": "did:example:ebfeb1f712ebc6f1c276e12ec21",
                "alumniOf": {
                "id": "did:example:c276e12ec21ebfeb1f712ebc6f1",
                "name": [{
                    "value": "Example University",
                    "lang": "en"
                }, {
                    "value": "Exemple d'Université",
                    "lang": "fr"
                }]
                }
            }
        ],
        "proof": {
            "type": "RsaSignature2018",
            "created": "2017-06-18T21:19:10Z",
            "proofPurpose": "assertionMethod",
            "verificationMethod": "https://example.edu/issuers/keys/1",
            "jws": "eyJhbGciOiJSUzI1NiIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..TCYt5XsITJX1CxPCT8yAV-TVkIEq_PbChOMqsLfRoPsnsgw5WEuts01mq-pQy7UJiN5mgRxD-WUcX16dUEMGlv50aqzpqh4Qktb3rk-BuQy72IFLOqV0G_zS245-kronKb78cPN25DGlcTwLtjPAYuNzVBAh4vGHSrQyHUdBBPM"
        }
    }
"""
sample_json_cred_3 = """
    {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://www.w3.org/2018/credentials/examples/v1"
        ],
        "id": "http://example.edu/credentials/1872",
        "type": ["VerifiableCredential", "AlumniCredential"],
        "issuer": {
            "id": "https://example.edu/issuers/565049"
        },
        "issuanceDate": "2010-01-01T19:73:24Z",
        "credentialSchema": "https://example.org/examples/degree.json",
        "credentialSubject": { "id": "did:example:ebfeb1f712ebc6f1c276e12ec21" },
        "proof": {
            "type": "RsaSignature2018",
            "created": "2017-06-18T21:19:10Z",
            "proofPurpose": "assertionMethod",
            "verificationMethod": "https://example.edu/issuers/keys/1",
            "jws": "eyJhbGciOiJSUzI1NiIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..TCYt5XsITJX1CxPCT8yAV-TVkIEq_PbChOMqsLfRoPsnsgw5WEuts01mq-pQy7UJiN5mgRxD-WUcX16dUEMGlv50aqzpqh4Qktb3rk-BuQy72IFLOqV0G_zS245-kronKb78cPN25DGlcTwLtjPAYuNzVBAh4vGHSrQyHUdBBPM"
        }
    }
"""
CONTEXTS = [
    "https://www.w3.org/2018/credentials/v1",
    "https://www.w3.org/2018/credentials/examples/v1",
]
TYPES = [
    "https://www.w3.org/2018/credentials#VerifiableCredential",
    "https://example.org/examples#UniversityDegreeCredential",
]
ISSUER_ID = "https://example.edu/issuers/14"
SUBJECT_IDS = ["did:example:ebfeb1f712ebc6f1c276e12ec21"]
SCHEMA_IDS = ["https://example.org/examples/degree.json"]
PROOF_TYPES = ["RsaSignature2018"]
GIVEN_ID = "http://example.edu/credentials/3732"
CRED_TAGS = {"tag": "value"}
CRED_VALUE = {"...": "..."}


@pytest.fixture
def record():
    def _record():
        return VCRecord(
            contexts=CONTEXTS,
            expanded_types=TYPES,
            schema_ids=SCHEMA_IDS,
            issuer_id=ISSUER_ID,
            subject_ids=SUBJECT_IDS,
            proof_types=PROOF_TYPES,
            cred_value=CRED_VALUE,
            given_id=GIVEN_ID,
            cred_tags=CRED_TAGS,
        )

    yield _record


class TestVCRecord:
    def test_create(self, record: Callable[[], VCRecord]):
        record_a = record()
        assert record_a.contexts == set(CONTEXTS)
        assert record_a.expanded_types == set(TYPES)
        assert record_a.schema_ids == set(SCHEMA_IDS)
        assert record_a.subject_ids == set(SUBJECT_IDS)
        assert record_a.proof_types == set(PROOF_TYPES)
        assert record_a.issuer_id == ISSUER_ID
        assert record_a.given_id == GIVEN_ID
        assert record_a.record_id and isinstance(record_a.record_id, str)
        assert record_a.cred_tags == CRED_TAGS
        assert record_a.cred_value == CRED_VALUE

    def test_eq(self, record: Callable[[], VCRecord]):
        record_a = record()
        record_b = record()

        assert record_a != record_b
        record_b.record_id = record_a.record_id
        assert record_a == record_b
        assert record_a != object()
        record_b.contexts.clear()
        assert record_a != record_b

    def test_serde(self, record: Callable[[], VCRecord]):
        obj = record().serialize()
        rec = VCRecord.deserialize(obj)
        assert isinstance(rec, VCRecord)

        obj_x = record()
        obj_x.cred_tags = -1  # not a dict
        with pytest.raises(BaseModelError):
            obj_x.serialize()
