import pytest

from unittest import TestCase

from ......messaging.models.base import BaseModelError
from ......did.did_key import DIDKey
from ......wallet.key_type import ED25519

from .....connections.v1_0.message_types import ARIES_PROTOCOL as CONN_PROTO
from .....didcomm_prefix import DIDCommPrefix
from .....didexchange.v1_0.message_types import ARIES_PROTOCOL as DIDX_PROTO
from .....didexchange.v1_0.messages.request import DIDXRequest

from ...message_types import INVITATION

from .. import invitation as test_module
from ..invitation import HSProto, InvitationMessage, InvitationMessageSchema
from ..invitation import InvitationMessage, InvitationMessageSchema
from ..service import Service

TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
DID_COMM = "did-communication"


class TestHSProto(TestCase):
    """Test handshake protocol enum."""

    def test_get(self):
        assert HSProto.get(HSProto.RFC160) is HSProto.RFC160
        assert HSProto.get(23) is HSProto.RFC23
        assert HSProto.get("Old") is HSProto.RFC160
        assert HSProto.get(DIDCommPrefix.qualify_current(CONN_PROTO)) is HSProto.RFC160
        assert HSProto.get(DIDX_PROTO) is HSProto.RFC23
        assert HSProto.get("did-exchange") is HSProto.RFC23
        assert HSProto.get("RFC-23") is HSProto.RFC23
        assert HSProto.get("no such protocol") is None
        assert HSProto.get(None) is None

    def test_properties(self):
        assert HSProto.RFC160.rfc == 160
        assert HSProto.RFC23.name == DIDX_PROTO


class TestInvitationMessage(TestCase):
    def test_init(self):
        """Test initialization message."""
        invi_msg = InvitationMessage(
            comment="Hello",
            label="A label",
            handshake_protocols=[DIDCommPrefix.qualify_current(DIDX_PROTO)],
            services=[TEST_DID],
        )
        assert invi_msg.services == [TEST_DID]
        assert "out-of-band/1.1/invitation" in invi_msg._type

        service = Service(_id="#inline", _type=DID_COMM, did=TEST_DID)
        invi_msg = InvitationMessage(
            comment="Hello",
            label="A label",
            handshake_protocols=[DIDCommPrefix.qualify_current(DIDX_PROTO)],
            services=[service],
            version="1.0",
        )
        assert invi_msg.services == [service]
        assert "out-of-band/1.0/invitation" in invi_msg._type

    def test_wrap_serde(self):
        """Test conversion of aries message to attachment decorator."""
        msg = {"aries": "message"}
        deco = InvitationMessage.wrap_message(msg)
        assert deco.ident == "request-0"

        obj_x = {"label": "label", "services": ["sample-did"]}
        with pytest.raises(BaseModelError):
            InvitationMessage.deserialize(obj_x)

        invi_schema = InvitationMessageSchema()
        with pytest.raises(test_module.ValidationError):
            invi_schema.validate_fields(obj_x)

        service = Service(
            _id="#inline",
            _type=DID_COMM,
            recipient_keys=[DIDKey.from_public_key_b58(TEST_VERKEY, ED25519).did],
            service_endpoint="http://1.2.3.4:8080/service",
        )
        data_deser = {
            "label": "label",
            "requests~attach": [deco.serialize()],
            "services": [{"a": service.serialize()}],
        }
        assert "services" in data_deser

        data_ser = invi_schema.post_dump(data_deser)
        assert "services" in data_ser

        service = Service(_id="#inline", _type=DID_COMM, did=TEST_DID)
        data_deser = {
            "label": "label",
            "requests~attach": [deco.serialize()],
            "services": [TEST_DID],
        }
        assert "services" in data_deser

        data_ser = invi_schema.post_dump(data_deser)
        assert "services" in data_ser

    def test_url_round_trip(self):
        service = Service(
            _id="#inline",
            _type=DID_COMM,
            recipient_keys=[DIDKey.from_public_key_b58(TEST_VERKEY, ED25519).did],
            service_endpoint="http://1.2.3.4:8080/service",
        )
        invi_msg = InvitationMessage(
            comment="Hello",
            label="A label",
            handshake_protocols=[DIDCommPrefix.qualify_current(DIDX_PROTO)],
            services=[service],
        )

        url = invi_msg.to_url()
        assert isinstance(url, str)
        invi_msg_rebuilt = InvitationMessage.from_url(url)
        assert isinstance(invi_msg_rebuilt, InvitationMessage)
        assert invi_msg_rebuilt.serialize() == invi_msg.serialize()

    def test_from_no_url(self):
        url = "http://aries.ca/no_ci"
        assert InvitationMessage.from_url(url) is None

    def test_invalid_invi_wrong_type_services(self):
        msg = {"aries": "message"}
        deco = InvitationMessage.wrap_message(msg)
        obj_x = {
            "label": "label",
            "requests~attach": [deco.serialize()],
            "services": [123],
        }

        errs = InvitationMessageSchema().validate(obj_x)
        assert errs and "services" in errs

    def test_assign_msg_type_version_to_model_inst(self):
        test_msg = InvitationMessage()
        assert "1.1" in test_msg._type
        assert "1.1" in InvitationMessage.Meta.message_type
        test_msg = InvitationMessage(version="1.2")
        assert "1.2" in test_msg._type
        assert "1.1" in InvitationMessage.Meta.message_type
        test_req = DIDXRequest()
        assert "1.0" in test_req._type
        assert "1.2" in test_msg._type
        assert "1.1" in InvitationMessage.Meta.message_type

    def test_goal_and_code_model(self):
        test_msg = InvitationMessage()
        assert test_msg.goal is None
        assert test_msg.goal_code is None
        test_msg = InvitationMessage(goal="pass test", goal_code="pytest.pass")
        assert test_msg.goal == "pass test"
        assert test_msg.goal_code == "pytest.pass"

    def test_mutual_inclusive_goal_and_goal_code(self):
        msg = {"aries": "message"}
        deco = InvitationMessage.wrap_message(msg)

        # populate both goal and goal_code - good
        obj_x = {
            "label": "label",
            "requests~attach": [deco.serialize()],
            "goal_code": "pytest.pass",
            "goal": "pass test",
        }

        errs = InvitationMessageSchema().validate(obj_x)
        assert errs == {}

        # do not include goal and goal_code - good
        obj_x = {
            "label": "label",
            "requests~attach": [deco.serialize()],
        }

        errs = InvitationMessageSchema().validate(obj_x)
        assert errs == {}

        # no value for both goal and goal_code - good
        obj_x = {
            "label": "label",
            "requests~attach": [deco.serialize()],
            "goal_code": "",
            "goal": "",
        }

        errs = InvitationMessageSchema().validate(obj_x)
        assert errs == {}

        errs = InvitationMessageSchema().validate(obj_x)
        assert errs == {}

        # populate only goal - bad
        obj_x = {
            "label": "label",
            "requests~attach": [deco.serialize()],
            "goal": "pass test",
        }

        errs = InvitationMessageSchema().validate(obj_x)
        assert errs and len(errs)
        assert errs and errs["_schema"]
        assert len(errs["_schema"]) == 1
        assert "goal" in errs["_schema"][0]

        # populate only goal_code - bad
        obj_x = {
            "label": "label",
            "requests~attach": [deco.serialize()],
            "goal_code": "pytest.pass",
        }

        errs = InvitationMessageSchema().validate(obj_x)
        assert errs and len(errs)
        assert errs and errs["_schema"]
        assert len(errs["_schema"]) == 1
        assert "goal_code" in errs["_schema"][0]

        # goal and goal code cannot be set to null/none
        obj_x = {
            "label": "label",
            "requests~attach": [deco.serialize()],
            "goal_code": None,
            "goal": None,
        }

        errs = InvitationMessageSchema().validate(obj_x)
        assert len(errs) == 2
        assert errs["goal"]
        assert errs["goal_code"]
