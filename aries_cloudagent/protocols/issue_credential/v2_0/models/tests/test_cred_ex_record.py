from asynctest import TestCase as AsyncTestCase

from ..cred_ex_record import V20CredExRecord


class TestV20CredExRecord(AsyncTestCase):
    async def test_record(self):
        same = [
            V20CredExRecord(
                cred_ex_id="dummy-0",
                thread_id="thread-0",
                initiator=V20CredExRecord.INITIATOR_SELF,
                role=V20CredExRecord.ROLE_ISSUER,
            )
        ] * 2
        diff = [
            V20CredExRecord(
                cred_ex_id="dummy-1",
                initiator=V20CredExRecord.INITIATOR_SELF,
                role=V20CredExRecord.ROLE_ISSUER,
            ),
            V20CredExRecord(
                cred_ex_id="dummy-0",
                thread_id="thread-1",
                initiator=V20CredExRecord.INITIATOR_SELF,
                role=V20CredExRecord.ROLE_ISSUER,
            ),
            V20CredExRecord(
                cred_ex_id="dummy-0",
                thread_id="thread-1",
                initiator=V20CredExRecord.INITIATOR_EXTERNAL,
                role=V20CredExRecord.ROLE_ISSUER,
            ),
        ]

        for i in range(len(same) - 1):
            for j in range(i, len(same)):
                assert same[i] == same[j]

        for i in range(len(diff) - 1):
            for j in range(i, len(diff)):
                assert diff[i] == diff[j] if i == j else diff[i] != diff[j]

        assert same[0].connection_id == same[0].conn_id  # cover connection_id
        assert not same[0].cred_preview  # cover non-proposal's non-preview
