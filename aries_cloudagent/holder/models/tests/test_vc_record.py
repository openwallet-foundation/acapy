from ..vc_record import VCRecord


class TestVCRecord:
    def test_create(self):
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
        schema_id = "https://example.org/examples/degree.json"
        given_id = "http://example.edu/credentials/3732"
        tags = {"tag": "value"}
        value = "{}"

        record = VCRecord(
            contexts=contexts,
            types=types,
            issuer_id=issuer_id,
            subject_ids=subject_ids,
            schema_id=schema_id,
            value=value,
            given_id=given_id,
            tags=tags,
        )

        assert record.contexts == contexts
        assert record.types == types
        assert record.subject_ids == subject_ids
        assert record.issuer_id == issuer_id
        assert record.schema_id == schema_id
        assert record.given_id == given_id
        assert record.record_id and type(record.record_id) is str
        assert record.tags == tags
        assert record.value == value
