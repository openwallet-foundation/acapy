import json

from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ....messaging.models.base import BaseModelError

from ..vc_record import VCRecord

CONTEXTS = [
    "https://www.w3.org/2018/credentials/v1",
    "https://www.w3.org/2018/credentials/examples/v1",
]
TYPES = [
    "https://www.w3.org/2018/credentials/v1/VerifiableCredential",
    "https://www.w3.org/2018/credentials/examples/v1/UniversityDegreeCredential",
]
ISSUER_ID = "https://example.edu/issuers/14"
SUBJECT_IDS = ["did:example:ebfeb1f712ebc6f1c276e12ec21"]
SCHEMA_IDS = ["https://example.org/examples/degree.json"]
GIVEN_ID = "http://example.edu/credentials/3732"
CRED_TAGS = {"tag": "value"}
CRED_VALUE = {"...": "..."}


def test_record() -> VCRecord:
    return VCRecord(
        contexts=CONTEXTS,
        types=TYPES,
        schema_ids=SCHEMA_IDS,
        issuer_id=ISSUER_ID,
        subject_ids=SUBJECT_IDS,
        cred_value=CRED_VALUE,
        given_id=GIVEN_ID,
        cred_tags=CRED_TAGS,
    )


class TestVCRecord(AsyncTestCase):
    def test_create(self):
        record = test_record()

        assert record.contexts == set(CONTEXTS)
        assert record.types == set(TYPES)
        assert record.schema_ids == set(SCHEMA_IDS)
        assert record.subject_ids == set(SUBJECT_IDS)
        assert record.issuer_id == ISSUER_ID
        assert record.given_id == GIVEN_ID
        assert record.record_id and type(record.record_id) is str
        assert record.cred_tags == CRED_TAGS
        assert record.cred_value == CRED_VALUE

    def test_eq(self):
        record_a = test_record()
        record_b = test_record()

        assert record_a != record_b
        record_b.record_id = record_a.record_id
        assert record_a == record_b
        assert record_a != object()
        record_b.contexts.clear()
        assert record_a != record_b

    async def test_serde(self):
        obj = test_record().serialize()
        record = VCRecord.deserialize(obj)
        assert type(record) == VCRecord

        obj_x = test_record()
        obj_x.cred_tags = -1  # not a dict
        with self.assertRaises(BaseModelError):
            obj_x.serialize()
