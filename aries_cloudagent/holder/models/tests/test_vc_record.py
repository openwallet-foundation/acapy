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

        assert record.contexts == contexts
        assert record.types == types
        assert record.schema_ids == schema_ids
        assert record.subject_ids == subject_ids
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
        record_b.contexts = []
        assert record_a != record_b
