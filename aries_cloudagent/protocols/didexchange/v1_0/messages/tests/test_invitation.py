from unittest import mock, TestCase

from ......messaging.models.base import BaseModelError

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import CONN23_INVITATION
from ..invitation import Conn23Invitation


class TestConn23Invitation(TestCase):
    label = "Label"
    did = "did:sov:QmWbsNYhMrjHiqZDTUTEJs"
    endpoint_url = "https://example.com/endpoint"
    endpoint_did = "did:sov:A2wBhNYhMrjHiqZDTUYH7u"
    image_url = "https://example.com/image.jpg"
    key = "8HH5gYEeNc3z7PYXmd54d4x6qAfCNrqQqEB3nS7Zfu7K"

    def test_init(self):
        invitation = Conn23Invitation(
            label=TestConn23Invitation.label,
            recipient_keys=[TestConn23Invitation.key],
            endpoint=TestConn23Invitation.endpoint_url,
        )
        assert invitation.label == TestConn23Invitation.label
        assert invitation.recipient_keys == [TestConn23Invitation.key]
        assert invitation.endpoint == TestConn23Invitation.endpoint_url

        invitation = Conn23Invitation(
            label=TestConn23Invitation.label,
            did=TestConn23Invitation.did,
        )
        assert invitation.did == TestConn23Invitation.did

    def test_type(self):
        invitation = Conn23Invitation(
            label=TestConn23Invitation.label,
            recipient_keys=[TestConn23Invitation.key],
            endpoint=TestConn23Invitation.endpoint_url,
        )

        assert invitation._type == DIDCommPrefix.qualify_current(CONN23_INVITATION)

    @mock.patch(
        "aries_cloudagent.protocols.didexchange.v1_0.messages."
        "invitation.Conn23InvitationSchema.load"
    )
    def test_deserialize(self, mock_invitation_schema_load):
        obj = {"obj": "obj"}

        invitation = Conn23Invitation.deserialize(obj)
        mock_invitation_schema_load.assert_called_once_with(obj)

        assert invitation is mock_invitation_schema_load.return_value

    @mock.patch(
        "aries_cloudagent.protocols.didexchange.v1_0.messages."
        "invitation.Conn23InvitationSchema.dump"
    )
    def test_serialize(self, mock_invitation_schema_dump):
        invitation = Conn23Invitation(
            label=TestConn23Invitation.label,
            recipient_keys=[TestConn23Invitation.key],
            endpoint=TestConn23Invitation.endpoint_url,
        )

        invitation_dict = invitation.serialize()
        mock_invitation_schema_dump.assert_called_once_with(invitation)

        assert invitation_dict is mock_invitation_schema_dump.return_value

    def test_url_round_trip(self):
        invitation = Conn23Invitation(
            label=TestConn23Invitation.label,
            recipient_keys=[TestConn23Invitation.key],
            endpoint=TestConn23Invitation.endpoint_url,
        )
        url = invitation.to_url()
        assert isinstance(url, str)
        invitation = Conn23Invitation.from_url(url)
        assert isinstance(invitation, Conn23Invitation)

    def test_from_no_url(self):
        url = "http://aries.ca/no_ci"
        assert Conn23Invitation.from_url(url) is None


class TestConn23InvitationSchema(TestCase):

    invitation = Conn23Invitation(label="label", did="did:sov:QmWbsNYhMrjHiqZDTUTEJs")

    def test_make_model(self):
        data = TestConn23Invitation.invitation.serialize()
        model_instance = Conn23Invitation.deserialize(data)
        assert isinstance(model_instance, Conn23Invitation)

    def test_make_model_x(self):
        x_conns = [
            Conn23Invitation(
                label="did-and-recip-keys",
                did="did:sov:QmWbsNYhMrjHiqZDTUTEJs",
                recipient_keys=["8HH5gYEeNc3z7PYXmd54d4x6qAfCNrqQqEB3nS7Zfu7K"],
            ),
            Conn23Invitation(
                label="did-and-endpoint",
                did="did:sov:QmWbsNYhMrjHiqZDTUTEJs",
                endpoint="https://example.com/endpoint",
            ),
            Conn23Invitation(
                label="no-did-no-recip-keys",
                endpoint="https://example.com/endpoint",
            ),
            Conn23Invitation(
                label="no-did-no-endpoint",
                recipient_keys=["8HH5gYEeNc3z7PYXmd54d4x6qAfCNrqQqEB3nS7Zfu7K"],
            ),
        ]
        for x_conn in x_conns:
            data = x_conn.serialize()
            with self.assertRaises(BaseModelError):
                Conn23Invitation.deserialize(data)
