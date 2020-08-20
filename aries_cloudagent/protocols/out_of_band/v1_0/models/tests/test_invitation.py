import json

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ..invitation import Invitation, InvitationSchema


class TestInvitation(AsyncTestCase):
    def test_invitation(self):
        """Test invitation."""
        invi = Invitation(invitation_id="0")
        assert isinstance(invi, Invitation)
        assert invi.invitation_id == "0"
        assert invi.record_value == {
            "invitation_id": "0",
            "invitation": None,
            "state": None,
            "trace": False,
        }

        another = Invitation(invitation_id="1")
        assert invi != another


class TestInvitationSchema(AsyncTestCase):
    def test_make_model(self):
        """Test making model."""
        data = {
            "invitation_id": "0",
            "state": Invitation.STATE_AWAIT_RESPONSE,
            "invitation": {"sample": "value"},
        }
        model_instance = Invitation.deserialize(data)
        assert isinstance(model_instance, Invitation)
