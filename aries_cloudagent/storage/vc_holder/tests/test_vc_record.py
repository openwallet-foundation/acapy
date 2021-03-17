from ..vc_record import VCRecord

contexts = [
    "https://www.w3.org/2018/credentials/v1",
    "https://www.w3.org/2018/credentials/examples/v1",
]
types = [
    "https://www.w3.org/2018/credentials/v1/VerifiableCredential",
    "https://www.w3.org/2018/credentials/examples/v1/UniversityDegreeCredential",
]
issuer_id = "https://example.edu/issuers/14"
subject_ids = ["did:example:ebfeb1f712ebc6f1c276e12ec21"]
schema_ids = ["https://example.org/examples/degree.json"]
given_id = "http://example.edu/credentials/3732"
tags = {"tag": "value"}
value = "{}"
sample_json_cred_1 = """
    {
      "vc": {
        "@context": "https://www.w3.org/2018/credentials/v1",
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
        }
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
        "credentialSubject": "did:example:ebfeb1f712ebc6f1c276e12ec21",
        "proof": {
            "type": "RsaSignature2018",
            "created": "2017-06-18T21:19:10Z",
            "proofPurpose": "assertionMethod",
            "verificationMethod": "https://example.edu/issuers/keys/1",
            "jws": "eyJhbGciOiJSUzI1NiIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..TCYt5XsITJX1CxPCT8yAV-TVkIEq_PbChOMqsLfRoPsnsgw5WEuts01mq-pQy7UJiN5mgRxD-WUcX16dUEMGlv50aqzpqh4Qktb3rk-BuQy72IFLOqV0G_zS245-kronKb78cPN25DGlcTwLtjPAYuNzVBAh4vGHSrQyHUdBBPM"
        }
    }
"""


def test_record() -> VCRecord:
    return VCRecord(
        contexts=contexts,
        types=types,
        schema_ids=schema_ids,
        issuer_id=issuer_id,
        subject_ids=subject_ids,
        value=value,
        given_id=given_id,
        tags=tags,
    )


class TestVCRecord:
    def test_create(self):
        record = test_record()

        assert record.contexts == set(contexts)
        assert record.types == set(types)
        assert record.schema_ids == set(schema_ids)
        assert record.subject_ids == set(subject_ids)
        assert record.issuer_id == issuer_id
        assert record.given_id == given_id
        assert record.record_id and type(record.record_id) is str
        assert record.tags == tags
        assert record.value == value

    def test_eq(self):
        record_a = test_record()
        record_b = test_record()

        assert record_a != record_b
        record_b.record_id = record_a.record_id
        assert record_a == record_b
        assert record_a != object()
        record_b.contexts.clear()
        assert record_a != record_b

    def test_deserialize(self):
        VCRecord.deserialize_jsonld_cred(sample_json_cred_1)
        VCRecord.deserialize_jsonld_cred(sample_json_cred_2)
        VCRecord.deserialize_jsonld_cred(sample_json_cred_3)
