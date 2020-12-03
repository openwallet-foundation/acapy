import pytest

from unittest import mock, TestCase

from asynctest import TestCase as AsyncTestCase

from ......messaging.models.base import BaseModelError
from ......wallet.util import naked_to_did_key

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import INVITATION, PROTOCOL_PACKAGE

from .. import invitation as test_module
from ..invitation import InvitationMessage, InvitationMessageSchema
from ..service import Service

TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
DID_COMM = "did-communication"


class TestInvitationMessage(TestCase):
    def test_init(self):
        """Test initialization message."""
        invi = InvitationMessage(
            comment="Hello",
            label="A label",
            handshake_protocols=[DIDCommPrefix.qualify_current(INVITATION)],
            service=[TEST_DID],
        )
        assert invi.service_dids == [TEST_DID]
        assert not invi.service_blocks
        assert invi._type == DIDCommPrefix.qualify_current(INVITATION)

        service = Service(_id="#inline", _type=DID_COMM, did=TEST_DID)
        invi_msg = InvitationMessage(
            comment="Hello",
            label="A label",
            handshake_protocols=[DIDCommPrefix.qualify_current(INVITATION)],
            service=[service],
        )
        assert invi_msg.service_blocks == [service]
        assert invi_msg._type == DIDCommPrefix.qualify_current(INVITATION)

    def test_wrap_serde(self):
        """Test conversion of aries message to attachment decorator."""
        msg = {"aries": "message"}
        deco = InvitationMessage.wrap_message(msg)
        assert deco.ident == "request-0"

        obj_x = {"label": "label", "service": ["sample-did"]}
        with pytest.raises(BaseModelError):
            InvitationMessage.deserialize(obj_x)

        invi_schema = InvitationMessageSchema()
        with pytest.raises(test_module.ValidationError):
            invi_schema.validate_fields(obj_x)

        service = Service(
            _id="#inline",
            _type=DID_COMM,
            recipient_keys=[naked_to_did_key(TEST_VERKEY)],
            service_endpoint="http://1.2.3.4:8080/service",
        )
        data_deser = invi_schema.pre_load(
            {
                "label": "label",
                "request~attach": [deco.serialize()],
                "service": [{"a": service.serialize()}],
            }
        )
        assert "service" not in data_deser

        data_ser = invi_schema.post_dump(data_deser)
        assert "service" in data_ser

        service = Service(_id="#inline", _type=DID_COMM, did=TEST_DID)
        data_deser = invi_schema.pre_load(
            {
                "label": "label",
                "request~attach": [deco.serialize()],
                "service": [TEST_DID],
            }
        )
        assert "service" not in data_deser

        data_ser = invi_schema.post_dump(data_deser)
        assert "service" in data_ser

    def test_url_round_trip(self):
        service = Service(
            _id="#inline",
            _type=DID_COMM,
            recipient_keys=[naked_to_did_key(TEST_VERKEY)],
            service_endpoint="http://1.2.3.4:8080/service",
        )
        invi_msg = InvitationMessage(
            comment="Hello",
            label="A label",
            handshake_protocols=[DIDCommPrefix.qualify_current(INVITATION)],
            service=[service],
        )

        url = invi_msg.to_url()
        assert isinstance(url, str)
        invi_msg_rebuilt = InvitationMessage.from_url(url)
        assert isinstance(invi_msg_rebuilt, InvitationMessage)
        assert invi_msg_rebuilt.serialize() == invi_msg.serialize()

    def test_from_no_url(self):
        url = "http://aries.ca/no_ci"
        assert InvitationMessage.from_url(url) is None
