from asynctest import TestCase as AsyncTestCase

from ....core.in_memory import InMemoryProfile
from ....storage.base import StorageNotFoundError

from .. import issuer_cred_rev_record as test_module
from ..issuer_cred_rev_record import IssuerCredRevRecord

TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
CRED_DEF_ID = f"{TEST_DID}:3:CL:1234:default"
REV_REG_ID = f"{TEST_DID}:4:{CRED_DEF_ID}:CL_ACCUM:0"


class TestIssuerCredRevRecord(AsyncTestCase):
    def setUp(self):
        self.session = InMemoryProfile.test_session()

    async def test_serde(self):
        rec = IssuerCredRevRecord(
            record_id=test_module.UUIDFour.EXAMPLE,
            state=IssuerCredRevRecord.STATE_ISSUED,
            cred_ex_id=test_module.UUIDFour.EXAMPLE,
            rev_reg_id=REV_REG_ID,
            cred_rev_id="1",
        )
        ser = rec.serialize()
        assert ser["record_id"] == rec.record_id
        assert ser["cred_def_id"] == CRED_DEF_ID
        assert rec.cred_def_id == CRED_DEF_ID

        assert rec == IssuerCredRevRecord.deserialize(ser)

    async def test_rec_ops(self):
        recs = [
            IssuerCredRevRecord(
                state=IssuerCredRevRecord.STATE_ISSUED,
                cred_ex_id=test_module.UUIDFour.EXAMPLE,
                rev_reg_id=REV_REG_ID,
                cred_rev_id=str(i + 1),
            )
            for i in range(2)
        ]
        await recs[0].set_state(
            self.session,
            IssuerCredRevRecord.STATE_REVOKED,
        )  # saves
        assert recs[0] != recs[1]

        assert (await IssuerCredRevRecord.query_by_ids(self.session))[0] == recs[0]
        assert (
            await IssuerCredRevRecord.retrieve_by_cred_ex_id(
                self.session, test_module.UUIDFour.EXAMPLE
            )
        ) == recs[0]
        assert (
            await IssuerCredRevRecord.query_by_ids(
                self.session,
                cred_def_id=CRED_DEF_ID,
            )
        )[0] == recs[0]
        assert (
            await IssuerCredRevRecord.query_by_ids(
                self.session,
                rev_reg_id=REV_REG_ID,
            )
        )[0] == recs[0]
        assert (
            await IssuerCredRevRecord.query_by_ids(
                self.session,
                cred_def_id=CRED_DEF_ID,
                rev_reg_id=REV_REG_ID,
            )
        )[0] == recs[0]
        assert (
            await IssuerCredRevRecord.query_by_ids(
                self.session,
                state=IssuerCredRevRecord.STATE_REVOKED,
            )
        )[0] == recs[0]
        assert not (
            await IssuerCredRevRecord.query_by_ids(
                self.session,
                state=IssuerCredRevRecord.STATE_ISSUED,
            )
        )

        assert (
            await IssuerCredRevRecord.retrieve_by_ids(
                self.session, rev_reg_id=REV_REG_ID, cred_rev_id="1"
            )
            == recs[0]
        )
        with self.assertRaises(StorageNotFoundError):
            await IssuerCredRevRecord.retrieve_by_ids(
                self.session, rev_reg_id=REV_REG_ID, cred_rev_id="2"
            )
