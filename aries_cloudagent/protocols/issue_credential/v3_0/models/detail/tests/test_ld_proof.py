from asynctest import TestCase as AsyncTestCase

from ..ld_proof import V30CredExRecordLDProof


class TestV30CredExRecordLDProof(AsyncTestCase):
    async def test_record(self):
        same = [
            V30CredExRecordLDProof(cred_ex_ld_proof_id="dummy-0", cred_ex_id="abc")
        ] * 2
        diff = [
            V30CredExRecordLDProof(
                cred_ex_ld_proof_id="dummy-0",
                cred_ex_id="def",
            ),
            V30CredExRecordLDProof(
                cred_ex_ld_proof_id="dummy-0",
                cred_ex_id="abc",
            ),
        ]

        for i in range(len(same) - 1):
            for j in range(i, len(same)):
                assert same[i] == same[j]

        for i in range(len(diff) - 1):
            for j in range(i, len(diff)):
                assert diff[i] == diff[j] if i == j else diff[i] != diff[j]

        assert same[0].cred_ex_ld_proof_id == "dummy-0"
