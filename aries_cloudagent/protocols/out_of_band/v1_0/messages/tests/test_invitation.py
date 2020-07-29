import pytest

from unittest import mock, TestCase

from asynctest import TestCase as AsyncTestCase

from ......messaging.models.base import BaseModelError

from ...message_types import INVITATION, PROTOCOL_PACKAGE

from .. import invitation as test_module
from ..invitation import Invitation, InvitationSchema
from ..service import Service

TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"


class TestInvitation(TestCase):
    def test_init(self):
        """Test initialization."""
        invi = Invitation(comment="Hello", label="A label", service=["service"])
        assert invi.service_dids == ["service"]
        assert not invi.service_blocks
        assert invi._type == INVITATION

        service = Service(_id="abc123", _type="a-type", did="My service")
        invi = Invitation(comment="Hello", label="A label", service=[service])
        assert invi.service_blocks == [service]
        assert invi._type == INVITATION

    def test_wrap_serde(self):
        """Test conversion of aries message to attachment decorator."""
        msg = {"aries": "message"}
        deco = Invitation.wrap_message(msg)
        assert deco.ident == "request-0"

        obj_x = {"label": "label", "service": ["sample-did"]}
        with pytest.raises(BaseModelError):
            Invitation.deserialize(obj_x)

        invi_schema = InvitationSchema()
        with pytest.raises(test_module.ValidationError):
            invi_schema.validate_fields(obj_x)

        service = Service(
            _id="#inline",
            _type="did-communication",
            recipient_keys=[TEST_VERKEY],
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

        service = Service(_id="#inline", _type="did-communication", did=TEST_DID)
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
