from unittest import IsolatedAsyncioTestCase
from marshmallow.exceptions import ValidationError

from ..route_record import RouteRecordSchema


class TestConnRecord(IsolatedAsyncioTestCase):
    async def test_route_record_validation_fails_no_connection_wallet(self):
        schema = schema = RouteRecordSchema()

        with self.assertRaises(ValidationError):
            schema.validate_fields({})

        schema.validate_fields({"connection_id": "dummy"})
        schema.validate_fields({"wallet_id": "dummy"})
