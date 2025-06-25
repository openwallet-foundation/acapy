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
            await recs[0].set_state(
                session,
                IssuerCredRevRecord.STATE_REVOKED,
            )  # saves
            assert recs[0] != recs[1]

            assert (await IssuerCredRevRecord.query_by_ids(session))[0] == recs[0]
            assert (
                await IssuerCredRevRecord.retrieve_by_cred_ex_id(
                    session, test_module.UUID4_EXAMPLE
                )
            ) == recs[0]
            assert (
                await IssuerCredRevRecord.query_by_ids(
                    session,
                    cred_def_id=CRED_DEF_ID,
                )
            )[0] == recs[0]
            assert (
                await IssuerCredRevRecord.query_by_ids(
                    session,
                    rev_reg_id=REV_REG_ID,
                )
            )[0] == recs[0]
            assert (
                await IssuerCredRevRecord.query_by_ids(
                    session,
                    cred_def_id=CRED_DEF_ID,
                    rev_reg_id=REV_REG_ID,
                )
            )[0] == recs[0]
            assert (
                await IssuerCredRevRecord.query_by_ids(
                    session,
                    state=IssuerCredRevRecord.STATE_REVOKED,
                )
            )[0] == recs[0]
            assert not (
                await IssuerCredRevRecord.query_by_ids(
                    session,
                    state=IssuerCredRevRecord.STATE_ISSUED,
                )
            )

            await recs[1].set_state(  # Save extra record
                session,
                IssuerCredRevRecord.STATE_REVOKED,
            )
            # Fetch cred rev id as string
            assert await IssuerCredRevRecord.retrieve_by_ids(
                session, rev_reg_id=REV_REG_ID, cred_rev_id="1"
            ) == [recs[0]]

            # Fetch cred rev id as list
            assert await IssuerCredRevRecord.retrieve_by_ids(
                session, rev_reg_id=REV_REG_ID, cred_rev_id=["2"]
            ) == [recs[1]]

            # Fetch both
            assert (
                await IssuerCredRevRecord.retrieve_by_ids(
                    session, rev_reg_id=REV_REG_ID, cred_rev_id=["1", "2"]
                )
            ) == recs

            # Fetch cred rev id that doesn't exist
            assert (
                await IssuerCredRevRecord.retrieve_by_ids(
                    session, rev_reg_id=REV_REG_ID, cred_rev_id=["3"]
                )
            ) == []
