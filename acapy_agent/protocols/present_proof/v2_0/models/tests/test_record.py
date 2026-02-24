from unittest import IsolatedAsyncioTestCase

from ......messaging.decorators.attach_decorator import AttachDecorator
from ......messaging.models.base_record import BaseExchangeRecord, BaseExchangeSchema
from ......tests import mock
from ......utils.testing import create_test_profile
from ...message_types import ATTACHMENT_FORMAT, PRES_20, PRES_20_PROPOSAL, PRES_20_REQUEST
from ...messages.pres import V20Pres
from ...messages.pres_format import V20PresFormat
from ...messages.pres_proposal import V20PresProposal
from ...messages.pres_request import V20PresRequest
from .. import pres_exchange as test_module
from ..pres_exchange import V20PresExRecord

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
INDY_PROOF = {
    "proof": {"proofs": []},
    "requested_proof": {
        "revealed_attrs": {},
        "self_attested_attrs": {},
        "unrevealed_attrs": {},
        "predicates": {},
    },
    "identifiers": [],
}


class BasexRecordImpl(BaseExchangeRecord):
    class Meta:
        schema_class = "BasexRecordImplSchema"

    RECORD_TYPE = "record"


class BasexRecordImplSchema(BaseExchangeSchema):
    class Meta:
        model_class = BasexRecordImpl


class TestRecord(IsolatedAsyncioTestCase):
    async def test_record(self):
        pres_proposal = V20PresProposal(
            comment="Hello World",
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_PROPOSAL][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            proposals_attach=[AttachDecorator.data_base64(INDY_PROOF_REQ, ident="indy")],
        )
        record = V20PresExRecord(
            pres_ex_id="pxid",
            thread_id="thid",
            connection_id="conn_id",
            initiator="init",
            role="role",
            state="state",
            verified="false",
            auto_present=True,
            error_msg="error",
            auto_remove=True,
        )
        record.pres_proposal = pres_proposal  # cover setter

        assert record.pres_ex_id == "pxid"

        assert record.record_value == {
            "connection_id": "conn_id",
            "initiator": "init",
            "role": "role",
            "state": "state",
            "pres_proposal": pres_proposal.serialize(),
            "verified": "false",
            "verified_msgs": None,
            "auto_present": True,
            "auto_verify": False,
            "error_msg": "error",
            "trace": False,
            "auto_remove": True,
            "auto_remove_on_failure": False,
        }

        bx_record = BasexRecordImpl()
        assert record != bx_record

    async def test_save_error_state(self):
        self.profile = await create_test_profile()
        record = V20PresExRecord(state=None)
        assert record._last_state is None
        async with self.profile.session() as session:
            await record.save_error_state(session)  # cover short circuit

            record.state = V20PresExRecord.STATE_PROPOSAL_RECEIVED
            await record.save(session)

            with (
                mock.patch.object(record, "save", mock.CoroutineMock()) as mock_save,
                mock.patch.object(
                    test_module.LOGGER, "exception", mock.MagicMock()
                ) as mock_log_exc,
            ):
                mock_save.side_effect = test_module.StorageError()
                await record.save_error_state(session, reason="testing")
                mock_log_exc.assert_called_once()

    # BUG #3802: ensure webhook payloads omit legacy pres_* fields when by_format exists
    async def test_emit_event_strips_legacy_pres_fields(self):
        settings = {
            "wallet.type": "askar",
            "auto_provision": True,
            "wallet.key": "5BngFuBpS4wjFfVFCtPqoix3ZXG2XR8XJ7qosUzMak7R",
            "wallet.key_derivation_method": "RAW",
            "debug.webhooks": True,
        }
        self.profile = await create_test_profile(settings=settings)
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(mapping=INDY_PROOF_REQ, ident="indy")
            ],
        )
        pres_proposal = V20PresProposal(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_PROPOSAL][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            proposals_attach=[
                AttachDecorator.data_base64(mapping=INDY_PROOF_REQ, ident="indy")
            ],
        )
        pres = V20Pres(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20][V20PresFormat.Format.INDY.api],
                )
            ],
            presentations_attach=[
                AttachDecorator.data_base64(mapping=INDY_PROOF, ident="indy")
            ],
        )
        record = V20PresExRecord(
            pres_ex_id="pxid",
            thread_id="thid",
            connection_id="conn_id",
            initiator="init",
            role="role",
            state=V20PresExRecord.STATE_PRESENTATION_RECEIVED,
            pres_proposal=pres_proposal,
            pres_request=pres_request,
            pres=pres,
        )

        async with self.profile.session() as session:
            session.emit_event = mock.CoroutineMock()
            await record.emit_event(session)

            payload = session.emit_event.call_args.args[1]
            assert "by_format" in payload
            for key in ("pres", "pres_proposal", "pres_request"):
                assert key not in payload and key in payload["by_format"]
