from asynctest import TestCase as AsyncTestCase

from ..indy import V20CredExRecordIndy


class TestV20CredExRecordIndy(AsyncTestCase):
    async def test_record(self):
        same = [
            V20CredExRecordIndy(
                cred_ex_indy_id="dummy-0",
                cred_ex_id="abc",
                cred_request_metadata={"a": 1, "b": 2},
                rev_reg_id=None,
                cred_rev_id=None,
            )
        ] * 2
        diff = [
            V20CredExRecordIndy(
                cred_ex_indy_id="dummy-1",
                cred_ex_id="def",
                cred_request_metadata={"a": 1, "b": 2},
                rev_reg_id=None,
                cred_rev_id=None,
            ),
            V20CredExRecordIndy(
                cred_ex_indy_id="dummy-1",
                cred_ex_id="ghi",
                cred_request_metadata={"a": 1, "b": 2},
                rev_reg_id=None,
                cred_rev_id=None,
            ),
            V20CredExRecordIndy(
                cred_ex_indy_id="dummy-1",
                cred_ex_id="def",
                cred_request_metadata={"a": 1, "b": 2},
                rev_reg_id="rev-reg-id",
                cred_rev_id="cred-rev-id",
            ),
        ]

        for i in range(len(same) - 1):
            for j in range(i, len(same)):
                assert same[i] == same[j]

        for i in range(len(diff) - 1):
            for j in range(i, len(diff)):
                assert diff[i] == diff[j] if i == j else diff[i] != diff[j]

        assert same[0].cred_ex_indy_id == "dummy-0"
