from unittest import mock, TestCase

from asynctest import TestCase as AsyncTestCase

from ..keylist_query_paginate import KeylistQueryPaginate
from ....message_types import PROTOCOL_PACKAGE


test_limit_data = 1
test_offset_data = 1

class TestKeylistQueryPaginate(TestCase):
    def setUp(self):
        self.test_limit = test_limit_data
        self.test_offset = test_offset_data
        self.test_message = KeylistQueryPaginate(limit=self.test_limit, offset=self.test_offset)

    def test_init(self):
        """Test initialization."""
        assert self.test_message.limit == self.test_limit
        assert self.test_message.offset == self.test_offset

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.inner.keylist_query_paginate.KeylistQueryPaginateSchema.load")
    def test_deserialize(self, mock_keylist_query_paginate_schema_load):
        """
        Test deserialization.
        """
        obj = {"obj": "obj"}

        msg = KeylistQueryPaginate.deserialize(obj)
        mock_keylist_query_paginate_schema_load.assert_called_once_with(obj)

        assert msg is mock_keylist_query_paginate_schema_load.return_value

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.inner.keylist_query_paginate.KeylistQueryPaginateSchema.dump")
    def test_serialize(self, mock_keylist_query_paginate_schema_load):
        """
        Test serialization.
        """
        msg_dict = self.test_message.serialize()
        mock_keylist_query_paginate_schema_load.assert_called_once_with(self.test_message)

        assert msg_dict is mock_keylist_query_paginate_schema_load.return_value


class TestKeylistQueryPaginateSchema(AsyncTestCase):
    """Test keylist query paginate schema."""

    async def test_make_model(self):
        keylist_query_paginate = KeylistQueryPaginate(limit=test_limit_data, offset=test_offset_data)
        data = keylist_query_paginate.serialize()
        model_instance = KeylistQueryPaginate.deserialize(data)
        assert type(model_instance) is type(keylist_query_paginate)