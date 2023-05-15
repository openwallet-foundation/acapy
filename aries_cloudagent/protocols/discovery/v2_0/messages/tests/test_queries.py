from unittest import mock, TestCase
from marshmallow import ValidationError

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import QUERIES, PROTOCOL_PACKAGE
from ..queries import Queries, QueryItem

TEST_QUERY_PROTOCOL = "https://didcomm.org/tictactoe/1.*"
TEST_QUERY_GOAL_CODE = "aries.*"


class TestQueries(TestCase):
    def test_init(self):
        test_queries = [
            QueryItem(feature_type="protocol", match=TEST_QUERY_PROTOCOL),
            QueryItem(feature_type="goal-code", match=TEST_QUERY_GOAL_CODE),
        ]
        queries = Queries(queries=test_queries)
        assert queries.queries[0].feature_type == "protocol"
        assert queries.queries[0].match == TEST_QUERY_PROTOCOL
        assert queries.queries[1].feature_type == "goal-code"
        assert queries.queries[1].match == TEST_QUERY_GOAL_CODE
        test_queries = [
            QueryItem(feature_type="protocol", match=TEST_QUERY_PROTOCOL),
        ]
        queries = Queries(queries=test_queries)
        assert queries.queries[0].feature_type == "protocol"
        assert queries.queries[0].match == TEST_QUERY_PROTOCOL

    def test_type(self):
        test_queries = [
            QueryItem(feature_type="protocol", match=TEST_QUERY_PROTOCOL),
            QueryItem(feature_type="goal-code", match=TEST_QUERY_GOAL_CODE),
        ]
        queries = Queries(queries=test_queries)
        assert queries._type == DIDCommPrefix.qualify_current(QUERIES)

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.queries.QueriesSchema.load")
    def test_deserialize(self, mock_queries_schema_dump):
        obj = {"obj": "obj"}

        query = Queries.deserialize(obj)
        mock_queries_schema_dump.assert_called_once_with(obj)

        assert query is mock_queries_schema_dump.return_value

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.queries.QueriesSchema.dump")
    def test_serialize(self, mock_queries_schema_dump):
        test_queries = [
            QueryItem(feature_type="protocol", match=TEST_QUERY_PROTOCOL),
            QueryItem(feature_type="goal-code", match=TEST_QUERY_GOAL_CODE),
        ]
        queries = Queries(queries=test_queries)

        queries_dict = queries.serialize()
        mock_queries_schema_dump.assert_called_once_with(queries)

        assert queries_dict is mock_queries_schema_dump.return_value


class TestQuerySchema(TestCase):
    test_queries = [
        QueryItem(feature_type="protocol", match=TEST_QUERY_PROTOCOL),
        QueryItem(feature_type="goal-code", match=TEST_QUERY_GOAL_CODE),
    ]
    queries = Queries(queries=test_queries)

    def test_make_model(self):
        data = self.queries.serialize()
        model_instance = Queries.deserialize(data)
        assert isinstance(model_instance, Queries)
