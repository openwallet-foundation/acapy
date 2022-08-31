from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ......core.in_memory import InMemoryProfile
from ......indy.models.pres_preview import (
    IndyPresAttrSpec,
    IndyPresPredSpec,
    IndyPresPreview,
)
from ......messaging.decorators.attach_decorator import AttachDecorator
from ......messaging.models.base_record import BaseExchangeRecord, BaseExchangeSchema

from ...message_types import PRESENTATION_PROPOSAL
from ...messages.presentation_proposal import PresentationProposal

from .. import presentation_exchange as test_module
from ..presentation_exchange import V10PresentationExchange

S_ID = "NcYxiDXkpYi6ov5FcYDi1e:2:vidya:1.0"
CD_ID = f"NcYxiDXkpYi6ov5FcYDi1e:3:CL:{S_ID}:tag1"
INDY_PROOF_REQ = {
    "name": "proof-req",
    "version": "1.0",
    "nonce": "12345",
    "requested_attributes": {
        "0_player_uuid": {
            "name": "player",
            "restrictions": [
                {
                    "cred_def_id": f"{CD_ID}",
                    "attr::player::value": "Richie Knucklez",
                }
            ],
            "non_revoked": {
                "from": 1234567890,
                "to": 1234567890,
            },
        },
        "0_screencapture_uuid": {
            "name": "screenCapture",
            "restrictions": [{"cred_def_id": f"{CD_ID}"}],
            "non_revoked": {
                "from": 1234567890,
                "to": 1234567890,
            },
        },
    },
    "requested_predicates": {
        "0_highscore_GE_uuid": {
            "name": "highScore",
            "p_type": ">=",
            "p_value": 1000000,
            "restrictions": [{"cred_def_id": f"{CD_ID}"}],
            "non_revoked": {
                "from": 1234567890,
                "to": 1234567890,
            },
        }
    },
}
PRES_PREVIEW = IndyPresPreview(
    attributes=[
        IndyPresAttrSpec(name="player", cred_def_id=CD_ID, value="Richie Knucklez"),
        IndyPresAttrSpec(
            name="screenCapture",
            cred_def_id=CD_ID,
            mime_type="image/png",
            value="aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
        ),
    ],
    predicates=[
        IndyPresPredSpec(
            name="highScore", cred_def_id=CD_ID, predicate=">=", threshold=1000000
        )
    ],
)


class BasexRecordImpl(BaseExchangeRecord):
    class Meta:
        schema_class = "BasexRecordImplSchema"

    RECORD_TYPE = "record"


class BasexRecordImplSchema(BaseExchangeSchema):
    class Meta:
        model_class = BasexRecordImpl


class TestRecord(AsyncTestCase):
    async def test_record(self):
        presentation_proposal = PresentationProposal(
            comment="Hello World", presentation_proposal=PRES_PREVIEW
        )
        record = V10PresentationExchange(
            presentation_exchange_id="pxid",
            connection_id="conn_id",
            thread_id="thid",
            auto_present=True,
        )
        record.presentation_proposal_dict = presentation_proposal  # cover setter
        record.presentation_request_dict = None  # cover setter

        assert record.presentation_exchange_id == "pxid"

        assert record.record_value == {
            "connection_id": "conn_id",
            "initiator": None,
            "presentation_proposal_dict": presentation_proposal.serialize(),
            "role": None,
            "state": None,
            "auto_present": True,
            "auto_verify": False,
            "error_msg": None,
            "verified": None,
            "verified_msgs": None,
            "trace": False,
        }

        bx_record = BasexRecordImpl()
        assert record != bx_record

    async def test_save_error_state(self):
        session = InMemoryProfile.test_session()
        record = V10PresentationExchange(state=None)
        assert record._last_state is None
        await record.save_error_state(session)  # cover short circuit

        record.state = V10PresentationExchange.STATE_PROPOSAL_RECEIVED
        await record.save(session)

        with async_mock.patch.object(
            record, "save", async_mock.CoroutineMock()
        ) as mock_save, async_mock.patch.object(
            test_module.LOGGER, "exception", async_mock.MagicMock()
        ) as mock_log_exc:
            mock_save.side_effect = test_module.StorageError()
            await record.save_error_state(session, reason="testing")
            mock_log_exc.assert_called_once()
