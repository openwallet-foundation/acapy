from unittest import mock, TestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import PROTOCOL_PACKAGE, ROUTE_UPDATE_RESPONSE
from ...models.route_updated import RouteUpdated, RouteUpdatedSchema
from ..route_update_response import RouteUpdateResponse


class TestRouteUpdateResponse(TestCase):
    test_action = "create"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_result = "success"

    def setUp(self):
        self.updated = RouteUpdated(
            recipient_key=self.test_verkey,
            action=self.test_action,
            result=self.test_result,
        )
        self.message = RouteUpdateResponse(updated=[self.updated])

    def test_init(self):
        assert len(self.message.updated) == 1
        assert self.message.updated[0].recipient_key == self.test_verkey
        assert self.message.updated[0].action == self.test_action
        assert self.message.updated[0].result == self.test_result

    def test_type(self):
        assert self.message._type == DIDCommPrefix.qualify_current(
            ROUTE_UPDATE_RESPONSE
        )

    @mock.patch(
        f"{PROTOCOL_PACKAGE}."
        "messages.route_update_response.RouteUpdateResponseSchema.load"
    )
    def test_deserialize(self, message_schema_load):
        obj = {"obj": "obj"}

        message = RouteUpdateResponse.deserialize(obj)
        message_schema_load.assert_called_once_with(obj)

        assert message is message_schema_load.return_value

    @mock.patch(
        f"{PROTOCOL_PACKAGE}."
        "messages.route_update_response.RouteUpdateResponseSchema.dump"
    )
    def test_serialize(self, message_schema_dump):
        message_dict = self.message.serialize()
        message_schema_dump.assert_called_once_with(self.message)

        assert message_dict is message_schema_dump.return_value


class TestRouteQueryRequestSchema(TestCase):
    def test_make_model(self):
        message = RouteUpdateResponse(
            updated=[
                RouteUpdated(recipient_key="zzz", action="create", result="success")
            ]
        )
        data = message.serialize()
        model_instance = RouteUpdateResponse.deserialize(data)
        assert isinstance(model_instance, RouteUpdateResponse)
