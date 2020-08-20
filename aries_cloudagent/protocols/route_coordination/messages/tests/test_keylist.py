from unittest import mock, TestCase
from asynctest import TestCase as AsyncTestCase

from ..inner.keylist_query_paginate import KeylistQueryPaginate
from ..keylist import KeylistQueryResponse
from ...message_types import KEYLIST, PROTOCOL_PACKAGE

test_keys_data = ["dummy","dummy"]
test_limit_data = 1
test_offset_data = 1
test_pagination_data = KeylistQueryPaginate(limit=test_limit_data, offset=test_offset_data)

class TestKeylist(TestCase):
    def setUp(self):
        self.test_message = KeylistQueryResponse(keys=test_keys_data, pagination=test_pagination_data)

    def test_init(self):
        """Test initialization."""
        assert self.test_message.keys == test_keys_data
        assert self.test_message.pagination == test_pagination_data

    def test_type(self):
        """Test type."""
        assert self.test_message._type == KEYLIST

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.keylist.KeylistQueryResponseSchema.load")
    def test_deserialize(self, mock_keylist_schema_load):
        """
        Test deserialization.
        """
        obj = {"obj": "obj"}

        msg = KeylistQueryResponse.deserialize(obj)
        mock_keylist_schema_load.assert_called_once_with(obj)

        assert msg is mock_keylist_schema_load.return_value

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.keylist.KeylistQueryResponseSchema.dump")
    def test_serialize(self, mock_keylist_schema_load):
        """
        Test serialization.
        """
        msg_dict = self.test_message.serialize()
        mock_keylist_schema_load.assert_called_once_with(self.test_message)

        assert msg_dict is mock_keylist_schema_load.return_value


class TestKeylistSchema(AsyncTestCase):
    """Test keylist schema."""

    async def test_make_model(self):
        keylist = KeylistQueryResponse(keys=test_keys_data, pagination=test_pagination_data)
        data = keylist.serialize()
        model_instance = KeylistQueryResponse.deserialize(data)
        assert type(model_instance) is type(keylist)
