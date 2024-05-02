from unittest import IsolatedAsyncioTestCase

from .....didcomm_prefix import DIDCommPrefix

from .....didexchange.v1_0.message_types import ARIES_PROTOCOL as DIDEX_1_1

from ...messages.invitation import InvitationMessage

from ..invitation import InvitationRecord

TEST_DID = "did:sov:55GkHamhTU1ZbTbV2ab9DE"


class TestInvitationRecord(IsolatedAsyncioTestCase):
    def test_invitation_record(self):
        """Test invitation record."""
        invi_rec = InvitationRecord(invi_msg_id="12345")
        assert invi_rec.invitation_id is None  # not saved
        assert isinstance(invi_rec, InvitationRecord)
        assert invi_rec.record_value == {
            "invitation_url": None,
            "state": None,
            "trace": False,
            "oob_id": None,
        }

        another = InvitationRecord(invi_msg_id="99999")
        assert invi_rec != another


class TestInvitationRecordSchema(IsolatedAsyncioTestCase):
    def test_make_record(self):
        """Test making record."""
        invi = InvitationMessage(
            label="A label",
            handshake_protocols=[DIDCommPrefix.qualify_current(DIDEX_1_1)],
            services=[TEST_DID],
        )
        data = {
            "invitation_id": "0",
            "state": InvitationRecord.STATE_AWAIT_RESPONSE,
            "invitation": invi.serialize(),
        }
        model_instance = InvitationRecord.deserialize(data)
        assert isinstance(model_instance, InvitationRecord)

        assert data.items() <= model_instance.serialize().items()

        model_instance = InvitationRecord(
            invitation_id="0",
            state=InvitationRecord.STATE_AWAIT_RESPONSE,
        )
        model_instance.invitation = invi  # exercise setter
        assert data.items() <= model_instance.serialize().items()
        model_instance = InvitationRecord(
            invitation_id="0",
            state=InvitationRecord.STATE_AWAIT_RESPONSE,
            invitation=invi.serialize(),
        )
        assert data.items() <= model_instance.serialize().items()
