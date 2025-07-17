from unittest import IsolatedAsyncioTestCase

from ....utils.testing import create_test_profile
from .. import issuer_cred_rev_record as test_module
from ..issuer_cred_rev_record import IssuerCredRevRecord

TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
CRED_DEF_ID = f"{TEST_DID}:3:CL:1234:default"
REV_REG_ID = f"{TEST_DID}:4:{CRED_DEF_ID}:CL_ACCUM:0"


class TestIssuerCredRevRecord(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.profile = await create_test_profile()

    async def test_serde(self):
        rec = IssuerCredRevRecord(
            record_id=test_module.UUID4_EXAMPLE,
            state=IssuerCredRevRecord.STATE_ISSUED,
            cred_ex_id=test_module.UUID4_EXAMPLE,
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
                cred_ex_id=test_module.UUID4_EXAMPLE,
                rev_reg_id=REV_REG_ID,
                cred_rev_id=str(i + 1),
            )
            for i in range(2)
        ]

        async with self.profile.session() as session:
            # Save and update first record
            await recs[0].set_state(
                session,
                IssuerCredRevRecord.STATE_REVOKED,
            )

            # Confirm the two records have different revocation IDs
            assert recs[0].cred_rev_id != recs[1].cred_rev_id

            # Helper to simplify record comparison
            def strip(record):
                return {
                    "cred_ex_id": record.cred_ex_id,
                    "cred_rev_id": record.cred_rev_id,
                    "rev_reg_id": record.rev_reg_id,
                    "cred_def_id": record.cred_def_id,
                    "state": record.state,
                }

            # Query and compare based on stripped fields
            result = await IssuerCredRevRecord.query_by_ids(session)
            assert strip(result[0]) == strip(recs[0])

            result = await IssuerCredRevRecord.retrieve_by_cred_ex_id(
                session, test_module.UUID4_EXAMPLE
            )
            assert strip(result) == strip(recs[0])

            result = await IssuerCredRevRecord.query_by_ids(
                session, cred_def_id=CRED_DEF_ID
            )
            assert strip(result[0]) == strip(recs[0])

            result = await IssuerCredRevRecord.query_by_ids(
                session, rev_reg_id=REV_REG_ID
            )
            assert strip(result[0]) == strip(recs[0])

            result = await IssuerCredRevRecord.query_by_ids(
                session, cred_def_id=CRED_DEF_ID, rev_reg_id=REV_REG_ID
            )
            assert strip(result[0]) == strip(recs[0])

            result = await IssuerCredRevRecord.query_by_ids(
                session, state=IssuerCredRevRecord.STATE_REVOKED
            )
            assert strip(result[0]) == strip(recs[0])

            result = await IssuerCredRevRecord.query_by_ids(
                session, state=IssuerCredRevRecord.STATE_ISSUED
            )
            assert not result

            # Save second record
            await recs[1].set_state(
                session,
                IssuerCredRevRecord.STATE_REVOKED,
            )

            result = await IssuerCredRevRecord.retrieve_by_ids(
                session, rev_reg_id=REV_REG_ID, cred_rev_id="1"
            )
            assert [strip(r) for r in result] == [strip(recs[0])]

            result = await IssuerCredRevRecord.retrieve_by_ids(
                session, rev_reg_id=REV_REG_ID, cred_rev_id=["2"]
            )
            assert [strip(r) for r in result] == [strip(recs[1])]

            result = await IssuerCredRevRecord.retrieve_by_ids(
                session, rev_reg_id=REV_REG_ID, cred_rev_id=["1", "2"]
            )
            assert sorted(
                [strip(r) for r in result], key=lambda r: r["cred_rev_id"]
            ) == sorted([strip(r) for r in recs], key=lambda r: r["cred_rev_id"])

            result = await IssuerCredRevRecord.retrieve_by_ids(
                session, rev_reg_id=REV_REG_ID, cred_rev_id=["3"]
            )
            assert result == []
