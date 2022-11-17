from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ......core.in_memory import InMemoryProfile
from ......messaging.decorators.attach_decorator_didcomm_v2_cred import AttachDecorator

from ...message_types import ATTACHMENT_FORMAT, CRED_30_PROPOSAL
from ...messages.cred_format import V30CredFormat
from ...messages.inner.cred_preview import (
    V30CredAttrSpec,
    V30CredPreview,
    V30CredPreviewBody,
)
from ...messages.cred_proposal import V30CredProposal

from .. import cred_ex_record as test_module
from ..cred_ex_record import V30CredExRecord

TEST_DID = "LjgpST2rjsoxYegQDRm7EL"
SCHEMA_NAME = "bc-reg"
SCHEMA_TXN = 12
SCHEMA_ID = f"{TEST_DID}:2:{SCHEMA_NAME}:1.0"
SCHEMA = {
    "ver": "1.0",
    "id": SCHEMA_ID,
    "name": SCHEMA_NAME,
    "version": "1.0",
    "attrNames": ["legalName", "jurisdictionId", "incorporationDate"],
    "seqNo": SCHEMA_TXN,
}
CRED_DEF_ID = f"{TEST_DID}:3:CL:12:tag1"
CRED_PREVIEW = V30CredPreview(
    _body=V30CredPreviewBody(
        attributes=(
            V30CredAttrSpec.list_plain({"test": "123", "hello": "world"})
            + [V30CredAttrSpec(name="icon", value="cG90YXRv", mime_type="image/png")]
        )
    )
)
INDY_FILTER = {
    "schema_id": SCHEMA_ID,
    "cred_def_id": CRED_DEF_ID,
}


class TestV30CredExRecord(AsyncTestCase):
    async def test_record(self):
        same = [
            V30CredExRecord(
                cred_ex_id="dummy-0",
                thread_id="thread-0",
                initiator=V30CredExRecord.INITIATOR_SELF,
                role=V30CredExRecord.ROLE_ISSUER,
            )
        ] * 2
        diff = [
            V30CredExRecord(
                cred_ex_id="dummy-1",
                initiator=V30CredExRecord.INITIATOR_SELF,
                role=V30CredExRecord.ROLE_ISSUER,
            ),
            V30CredExRecord(
                cred_ex_id="dummy-0",
                thread_id="thread-1",
                initiator=V30CredExRecord.INITIATOR_SELF,
                role=V30CredExRecord.ROLE_ISSUER,
            ),
            V30CredExRecord(
                cred_ex_id="dummy-0",
                thread_id="thread-1",
                initiator=V30CredExRecord.INITIATOR_EXTERNAL,
                role=V30CredExRecord.ROLE_ISSUER,
            ),
        ]

        for i in range(len(same) - 1):
            for j in range(i, len(same)):
                assert same[i] == same[j]

        for i in range(len(diff) - 1):
            for j in range(i, len(diff)):
                assert diff[i] == diff[j] if i == j else diff[i] != diff[j]

        assert not same[0].cred_preview  # cover non-proposal's non-preview

    def test_serde(self):
        """Test de/serialization."""

        cred_proposal = V30CredProposal(
            _body=CRED_PREVIEW,
            attachments=[
                AttachDecorator.data_base64(
                    INDY_FILTER,
                    ident="indy",
                    format=V30CredFormat(
                        format_=ATTACHMENT_FORMAT[CRED_30_PROPOSAL][
                            V30CredFormat.Format.INDY.api
                        ],
                    ),
                )
            ],
        )
        for proposal_arg in [cred_proposal, cred_proposal.serialize()]:
            cx_rec = V30CredExRecord(
                cred_ex_id="dummy",
                connection_id="0000...",
                thread_id="dummy-thid",
                parent_thread_id="dummy-pthid",
                initiator=V30CredExRecord.INITIATOR_EXTERNAL,
                role=V30CredExRecord.ROLE_ISSUER,
                state=V30CredExRecord.STATE_PROPOSAL_RECEIVED,
                cred_proposal=proposal_arg,
                cred_offer=None,
                cred_request=None,
                cred_issue=None,
                auto_offer=False,
                auto_issue=False,
                auto_remove=True,
                error_msg=None,
                trace=False,
            )
            assert type(cx_rec.cred_proposal) == V30CredProposal
            ser = cx_rec.serialize()
            deser = V30CredExRecord.deserialize(ser)
            assert type(deser.cred_proposal) == V30CredProposal

    async def test_save_error_state(self):
        session = InMemoryProfile.test_session()
        record = V30CredExRecord(state=None)
        assert record._last_state is None
        await record.save_error_state(session)  # cover short circuit

        record.state = V30CredExRecord.STATE_PROPOSAL_RECEIVED
        await record.save(session)

        with async_mock.patch.object(
            record, "save", async_mock.CoroutineMock()
        ) as mock_save, async_mock.patch.object(
            test_module.LOGGER, "exception", async_mock.MagicMock()
        ) as mock_log_exc:
            mock_save.side_effect = test_module.StorageError()
            await record.save_error_state(session, reason="test")
            mock_log_exc.assert_called_once()
