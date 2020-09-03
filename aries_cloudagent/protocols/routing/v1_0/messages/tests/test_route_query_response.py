from unittest import mock, TestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import PROTOCOL_PACKAGE, ROUTE_QUERY_RESPONSE
from ...models.paginated import Paginated, PaginatedSchema
from ...models.route_record import RouteRecord

from ..route_query_response import RouteQueryResponse


class TestRouteQueryResponse(TestCase):
    test_start = 10
    test_end = 15
    test_limit = 5
    test_total = 20
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_route_id = "route-id"
    test_conn_id = "conn-id"

    def setUp(self):
        self.paginated = Paginated(
            start=self.test_start,
            end=self.test_end,
            limit=self.test_limit,
            total=self.test_total,
        )
        self.record = RouteRecord(
            record_id=self.test_route_id,
            connection_id=self.test_conn_id,
            recipient_key=self.test_verkey,
        )
        self.message = RouteQueryResponse(
            routes=[self.record], paginated=self.paginated
        )

    def test_init(self):
        assert len(self.message.routes) == 1
        assert self.message.routes[0].record_id == self.test_route_id
        assert self.message.routes[0].connection_id == self.test_conn_id
        assert self.message.routes[0].recipient_key == self.test_verkey
        assert self.message.paginated.start == self.test_start
        assert self.message.paginated.end == self.test_end
        assert self.message.paginated.limit == self.test_limit
        assert self.message.paginated.total == self.test_total

    def test_type(self):
        assert self.message._type == DIDCommPrefix.qualify_current(ROUTE_QUERY_RESPONSE)

    @mock.patch(
        f"{PROTOCOL_PACKAGE}."
        "messages.route_query_response.RouteQueryResponseSchema.load"
    )
    def test_deserialize(self, message_schema_load):
        obj = {"obj": "obj"}

        message = RouteQueryResponse.deserialize(obj)
        message_schema_load.assert_called_once_with(obj)

        assert message is message_schema_load.return_value

    @mock.patch(
        f"{PROTOCOL_PACKAGE}."
        "messages.route_query_response.RouteQueryResponseSchema.dump"
    )
    def test_serialize(self, message_schema_dump):
        message_dict = self.message.serialize()
        message_schema_dump.assert_called_once_with(self.message)

        assert message_dict is message_schema_dump.return_value


class TestRouteQueryResponseSchema(TestCase):
    def test_make_model(self):
        message = RouteQueryResponse(
            routes=[RouteRecord(record_id="a", connection_id="b", recipient_key="c")],
            paginated=Paginated(),
        )
        data = message.serialize()
        model_instance = RouteQueryResponse.deserialize(data)
        assert isinstance(model_instance, RouteQueryResponse)
