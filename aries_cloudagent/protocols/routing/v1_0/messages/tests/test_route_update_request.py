from unittest import mock, TestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import PROTOCOL_PACKAGE, ROUTE_UPDATE_REQUEST
from ...models.route_update import RouteUpdate, RouteUpdateSchema

from ..route_update_request import RouteUpdateRequest


class TestRouteUpdateRequest(TestCase):
    test_action = "create"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"

    def setUp(self):
        self.update = RouteUpdate(
            recipient_key=self.test_verkey, action=self.test_action
        )
        self.message = RouteUpdateRequest(updates=[self.update])

    def test_init(self):
        assert len(self.message.updates) == 1
        assert self.message.updates[0].recipient_key == self.test_verkey
        assert self.message.updates[0].action == self.test_action

    def test_type(self):
        assert self.message._type == DIDCommPrefix.qualify_current(ROUTE_UPDATE_REQUEST)

    @mock.patch(
        f"{PROTOCOL_PACKAGE}."
        "messages.route_update_request.RouteUpdateRequestSchema.load"
    )
    def test_deserialize(self, message_schema_load):
        obj = {"obj": "obj"}

        message = RouteUpdateRequest.deserialize(obj)
        message_schema_load.assert_called_once_with(obj)

        assert message is message_schema_load.return_value

    @mock.patch(
        f"{PROTOCOL_PACKAGE}"
        ".messages.route_update_request.RouteUpdateRequestSchema.dump"
    )
    def test_serialize(self, message_schema_dump):
        message_dict = self.message.serialize()
        message_schema_dump.assert_called_once_with(self.message)

        assert message_dict is message_schema_dump.return_value


class TestRouteQueryRequestSchema(TestCase):
    def test_make_model(self):
        message = RouteUpdateRequest(
            updates=[RouteUpdate(recipient_key="zzz", action="create")]
        )
        data = message.serialize()
        model_instance = RouteUpdateRequest.deserialize(data)
        assert isinstance(model_instance, RouteUpdateRequest)
