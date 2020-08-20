from unittest import mock, TestCase
from asynctest import TestCase as AsyncTestCase

from ..inner.keylist_query_paginate import KeylistQueryPaginate
from ..keylist_query import KeylistQuery
from ...message_types import KEYLIST_QUERY, PROTOCOL_PACKAGE

test_filter_data = {
            "routing_key": [
                "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV",
                "2wUJCoyzkJz1tTxehfT7Usq5FgJz3EQHBQC7b2mXxbRZ"
            ]
        }
test_limit_data = 1
test_offset_data = 1
test_paginate_data = KeylistQueryPaginate(limit=test_limit_data, offset=test_offset_data)

class TestKeylistQuery(TestCase):
    def setUp(self):
        self.test_message = KeylistQuery(filter=test_filter_data, paginate=test_paginate_data)

    def test_init(self):
        """Test initialization."""
        assert self.test_message.filter == test_filter_data
        assert self.test_message.paginate == test_paginate_data

    def test_type(self):
        """Test type."""
        assert self.test_message._type == KEYLIST_QUERY

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.keylist_query.KeylistQuerySchema.load")
    def test_deserialize(self, mock_keylist_query_schema_load):
        """
        Test deserialization.
        """
        obj = {"obj": "obj"}

        msg = KeylistQuery.deserialize(obj)
        mock_keylist_query_schema_load.assert_called_once_with(obj)

        assert msg is mock_keylist_query_schema_load.return_value

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.keylist_query.KeylistQuerySchema.dump")
    def test_serialize(self, mock_keylist_query_schema_load):
        """
        Test serialization.
        """
        msg_dict = self.test_message.serialize()
        mock_keylist_query_schema_load.assert_called_once_with(self.test_message)

        assert msg_dict is mock_keylist_query_schema_load.return_value


class TestKeylistQuerySchema(AsyncTestCase):
    """Test keylist query schema."""

    async def test_make_model(self):
        keylist_query = KeylistQuery(filter=test_filter_data, paginate=test_paginate_data)
        data = keylist_query.serialize()
        model_instance = KeylistQuery.deserialize(data)
        assert type(model_instance) is type(keylist_query)
