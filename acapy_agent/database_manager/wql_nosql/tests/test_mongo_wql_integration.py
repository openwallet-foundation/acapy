import logging
import unittest

import pytest

try:
    from pymongo import MongoClient

    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False

from acapy_agent.database_manager.wql_nosql.encoders import encoder_factory
from acapy_agent.database_manager.wql_nosql.query import query_from_str
from acapy_agent.database_manager.wql_nosql.tags import (
    TagName,
    TagQuery,
    query_to_tagquery,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.skipif(not PYMONGO_AVAILABLE, reason="pymongo is not installed")
class TestMongoTagEncoder(unittest.TestCase):
    def setUp(self):
        """Set up MongoDB connection and ensure collection is clean."""
        self.db_uri = "mongodb://admin:securepassword@192.168.2.155:27017/acapy_test_db?authSource=admin"
        try:
            self.client = MongoClient(self.db_uri)
            self.db = self.client["acapy_test_db"]
            self.collection = self.db["items"]
            self.collection.drop()
            logger.info("Collection 'items' dropped in setUp")
        except Exception as e:
            logger.error(f"Failed to set up MongoDB connection: {e}")
            raise

        self.enc_name = lambda x: x
        self.enc_value = lambda x: x
        self.encoder = encoder_factory.get_encoder(
            "mongodb", self.enc_name, self.enc_value
        )

    def tearDown(self):
        """Clean up by dropping the collection and closing the client."""
        try:
            self.collection.drop()
            logger.info("Collection 'items' dropped in tearDown")
            self.client.close()
        except Exception as e:
            logger.error(f"Failed to tear down MongoDB connection: {e}")
            raise

    def run_query_and_verify(self, mongo_query, expected_ids, test_name):
        """Run a MongoDB query and verify the results against expected _ids."""
        results = self.collection.find(mongo_query)
        actual_ids = sorted([doc["_id"] for doc in results])
        self.assertEqual(
            actual_ids,
            expected_ids,
            f"{test_name} failed: Expected _ids {expected_ids}, got {actual_ids}",
        )

    def verify_round_trip(self, query, original_mongo_query):
        """Verify that converting TagQuery to WQL and back results in the same MongoDB query."""
        wql_str = query.to_wql_str()
        parsed_query = query_from_str(wql_str)
        parsed_tag_query = query_to_tagquery(parsed_query)
        parsed_mongo_query = self.encoder.encode_query(parsed_tag_query)
        self.assertEqual(
            original_mongo_query,
            parsed_mongo_query,
            f"Round-trip MongoDB query mismatch in {self._testMethodName}",
        )

    # Individual Operator Tests
    def test_eq_positive(self):
        query = TagQuery.eq(TagName("field"), "value")
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": "value"}
        self.assertEqual(mongo_query, expected_query, "Positive equality query mismatch")
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "field": "value"},
                {"_id": 2, "field": "other"},
                {"_id": 3, "field": "value"},
            ]
        )
        self.run_query_and_verify(mongo_query, [1, 3], "Positive equality")

    def test_eq_negated(self):
        query = TagQuery.not_(TagQuery.eq(TagName("field"), "value"))
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$ne": "value"}}
        self.assertEqual(mongo_query, expected_query, "Negated equality query mismatch")
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "field": "value"},
                {"_id": 2, "field": "other"},
                {"_id": 3, "field": "value"},
            ]
        )
        self.run_query_and_verify(mongo_query, [2], "Negated equality")

    def test_neq_positive(self):
        query = TagQuery.neq(TagName("field"), "value")
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$ne": "value"}}
        self.assertEqual(
            mongo_query, expected_query, "Positive inequality query mismatch"
        )
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "field": "value"},
                {"_id": 2, "field": "other"},
                {"_id": 3, "field": "different"},
            ]
        )
        self.run_query_and_verify(mongo_query, [2, 3], "Positive inequality")

    def test_neq_negated(self):
        query = TagQuery.not_(TagQuery.neq(TagName("field"), "value"))
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": "value"}
        self.assertEqual(mongo_query, expected_query, "Negated inequality query mismatch")
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "field": "value"},
                {"_id": 2, "field": "other"},
                {"_id": 3, "field": "value"},
            ]
        )
        self.run_query_and_verify(mongo_query, [1, 3], "Negated inequality")

    def test_gt_positive(self):
        query = TagQuery.gt(TagName("price"), "100")
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"price": {"$gt": "100"}}
        self.assertEqual(
            mongo_query, expected_query, "Positive greater-than query mismatch"
        )
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "price": "090"},
                {"_id": 2, "price": "100"},
                {"_id": 3, "price": "150"},
                {"_id": 4, "price": "200"},
            ]
        )
        self.run_query_and_verify(mongo_query, [3, 4], "Positive greater-than")

    def test_gt_negated(self):
        query = TagQuery.not_(TagQuery.gt(TagName("price"), "100"))
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"price": {"$not": {"$gt": "100"}}}
        self.assertEqual(
            mongo_query, expected_query, "Negated greater-than query mismatch"
        )
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "price": "090"},
                {"_id": 2, "price": "100"},
                {"_id": 3, "price": "150"},
                {"_id": 4, "price": "200"},
            ]
        )
        self.run_query_and_verify(mongo_query, [1, 2], "Negated greater-than")

    def test_gte_positive(self):
        query = TagQuery.gte(TagName("price"), "100")
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"price": {"$gte": "100"}}
        self.assertEqual(
            mongo_query, expected_query, "Positive greater-than-or-equal query mismatch"
        )
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "price": "090"},
                {"_id": 2, "price": "100"},
                {"_id": 3, "price": "150"},
                {"_id": 4, "price": "200"},
            ]
        )
        self.run_query_and_verify(
            mongo_query, [2, 3, 4], "Positive greater-than-or-equal"
        )

    def test_gte_negated(self):
        query = TagQuery.not_(TagQuery.gte(TagName("price"), "100"))
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"price": {"$not": {"$gte": "100"}}}
        self.assertEqual(
            mongo_query, expected_query, "Negated greater-than-or-equal query mismatch"
        )
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "price": "090"},
                {"_id": 2, "price": "100"},
                {"_id": 3, "price": "150"},
                {"_id": 4, "price": "200"},
            ]
        )
        self.run_query_and_verify(mongo_query, [1], "Negated greater-than-or-equal")

    def test_lt_positive(self):
        query = TagQuery.lt(TagName("price"), "100")
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"price": {"$lt": "100"}}
        self.assertEqual(mongo_query, expected_query, "Positive less-than query mismatch")
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "price": "090"},
                {"_id": 2, "price": "100"},
                {"_id": 3, "price": "150"},
                {"_id": 4, "price": "200"},
            ]
        )
        self.run_query_and_verify(mongo_query, [1], "Positive less-than")

    def test_lt_negated(self):
        query = TagQuery.not_(TagQuery.lt(TagName("price"), "100"))
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"price": {"$not": {"$lt": "100"}}}
        self.assertEqual(mongo_query, expected_query, "Negated less-than query mismatch")
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "price": "090"},
                {"_id": 2, "price": "100"},
                {"_id": 3, "price": "150"},
                {"_id": 4, "price": "200"},
            ]
        )
        self.run_query_and_verify(mongo_query, [2, 3, 4], "Negated less-than")

    def test_lte_positive(self):
        query = TagQuery.lte(TagName("price"), "100")
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"price": {"$lte": "100"}}
        self.assertEqual(
            mongo_query, expected_query, "Positive less-than-or-equal query mismatch"
        )
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "price": "090"},
                {"_id": 2, "price": "100"},
                {"_id": 3, "price": "150"},
                {"_id": 4, "price": "200"},
            ]
        )
        self.run_query_and_verify(mongo_query, [1, 2], "Positive less-than-or-equal")

    def test_lte_negated(self):
        query = TagQuery.not_(TagQuery.lte(TagName("price"), "100"))
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"price": {"$not": {"$lte": "100"}}}
        self.assertEqual(
            mongo_query, expected_query, "Negated less-than-or-equal query mismatch"
        )
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "price": "090"},
                {"_id": 2, "price": "100"},
                {"_id": 3, "price": "150"},
                {"_id": 4, "price": "200"},
            ]
        )
        self.run_query_and_verify(mongo_query, [3, 4], "Negated less-than-or-equal")

    def test_like_positive(self):
        query = TagQuery.like(TagName("field"), "pat")
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$regex": "pat"}}
        self.assertEqual(mongo_query, expected_query, "Positive LIKE query mismatch")
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "field": "pattern"},
                {"_id": 2, "field": "path"},
                {"_id": 3, "field": "other"},
                {"_id": 4, "field": "pat"},
            ]
        )
        self.run_query_and_verify(mongo_query, [1, 2, 4], "Positive LIKE")

    def test_like_negated(self):
        query = TagQuery.not_(TagQuery.like(TagName("field"), "pat"))
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$not": {"$regex": "pat"}}}
        self.assertEqual(mongo_query, expected_query, "Negated LIKE query mismatch")
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "field": "pattern"},
                {"_id": 2, "field": "path"},
                {"_id": 3, "field": "other"},
                {"_id": 4, "field": "pat"},
            ]
        )
        self.run_query_and_verify(mongo_query, [3], "Negated LIKE")

    def test_in_positive(self):
        query = TagQuery.in_(TagName("field"), ["a", "b"])
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$in": ["a", "b"]}}
        self.assertEqual(mongo_query, expected_query, "Positive IN query mismatch")
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "field": "a"},
                {"_id": 2, "field": "b"},
                {"_id": 3, "field": "c"},
                {"_id": 4, "field": "a"},
            ]
        )
        self.run_query_and_verify(mongo_query, [1, 2, 4], "Positive IN")

    def test_in_negated(self):
        query = TagQuery.not_(TagQuery.in_(TagName("field"), ["a", "b"]))
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$nin": ["a", "b"]}}
        self.assertEqual(mongo_query, expected_query, "Negated IN query mismatch")
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "field": "a"},
                {"_id": 2, "field": "b"},
                {"_id": 3, "field": "c"},
                {"_id": 4, "field": "d"},
            ]
        )
        self.run_query_and_verify(mongo_query, [3, 4], "Negated IN")

    def test_exist_positive(self):
        query = TagQuery.exist([TagName("field")])
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$exists": True}}
        self.assertEqual(mongo_query, expected_query, "Positive EXIST query mismatch")
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [{"_id": 1, "field": "value"}, {"_id": 2}, {"_id": 3, "field": "another"}]
        )
        self.run_query_and_verify(mongo_query, [1, 3], "Positive EXIST")

    def test_exist_negated(self):
        query = TagQuery.not_(TagQuery.exist([TagName("field")]))
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$exists": False}}
        self.assertEqual(mongo_query, expected_query, "Negated EXIST query mismatch")
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [{"_id": 1, "field": "value"}, {"_id": 2}, {"_id": 3, "field": "another"}]
        )
        self.run_query_and_verify(mongo_query, [2], "Negated EXIST")

    # Conjunction Tests
    def test_and_multiple(self):
        query = TagQuery.and_(
            [TagQuery.eq(TagName("f1"), "v1"), TagQuery.gt(TagName("f2"), "10")]
        )
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"$and": [{"f1": "v1"}, {"f2": {"$gt": "10"}}]}
        self.assertEqual(mongo_query, expected_query, "AND multiple query mismatch")
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "f1": "v1", "f2": "15"},
                {"_id": 2, "f1": "v1", "f2": "05"},
                {"_id": 3, "f1": "v2", "f2": "15"},
                {"_id": 4, "f1": "v1", "f2": "20"},
            ]
        )
        self.run_query_and_verify(mongo_query, [1, 4], "AND multiple")

    def test_or_multiple(self):
        query = TagQuery.or_(
            [TagQuery.eq(TagName("f1"), "v1"), TagQuery.gt(TagName("f2"), "10")]
        )
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"$or": [{"f1": "v1"}, {"f2": {"$gt": "10"}}]}
        self.assertEqual(mongo_query, expected_query, "OR multiple query mismatch")
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "f1": "v1", "f2": "15"},
                {"_id": 2, "f1": "v1", "f2": "05"},
                {"_id": 3, "f1": "v2", "f2": "15"},
                {"_id": 4, "f1": "v2", "f2": "05"},
            ]
        )
        self.run_query_and_verify(mongo_query, [1, 2, 3], "OR multiple")

    def test_nested_and_or(self):
        query = TagQuery.and_(
            [
                TagQuery.eq(TagName("f1"), "v1"),
                TagQuery.or_(
                    [TagQuery.gt(TagName("f2"), "10"), TagQuery.lt(TagName("f3"), "5")]
                ),
            ]
        )
        mongo_query = self.encoder.encode_query(query)
        expected_query = {
            "$and": [{"f1": "v1"}, {"$or": [{"f2": {"$gt": "10"}}, {"f3": {"$lt": "5"}}]}]
        }
        self.assertEqual(mongo_query, expected_query, "Nested AND/OR query mismatch")
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "f1": "v1", "f2": "15", "f3": "3"},
                {"_id": 2, "f1": "v1", "f2": "05", "f3": "4"},
                {"_id": 3, "f1": "v2", "f2": "15", "f3": "3"},
                {"_id": 4, "f1": "v1", "f2": "05", "f3": "6"},
            ]
        )
        self.run_query_and_verify(mongo_query, [1, 2], "Nested AND/OR")

    # Complex Query Tests
    def test_comparison_conjunction(self):
        query = TagQuery.and_(
            [
                TagQuery.eq(TagName("category"), "electronics"),
                TagQuery.gt(TagName("price"), "100"),
            ]
        )
        mongo_query = self.encoder.encode_query(query)
        expected_query = {
            "$and": [{"category": "electronics"}, {"price": {"$gt": "100"}}]
        }
        self.assertEqual(
            mongo_query, expected_query, "Comparison conjunction query mismatch"
        )
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "category": "electronics", "price": "150"},
                {"_id": 2, "category": "electronics", "price": "090"},
                {"_id": 3, "category": "books", "price": "120"},
                {"_id": 4, "category": "electronics", "price": "200"},
            ]
        )
        self.run_query_and_verify(mongo_query, [1, 4], "Comparison conjunction")

    def test_deeply_nested_not(self):
        query = TagQuery.not_(
            TagQuery.and_(
                [
                    TagQuery.or_(
                        [
                            TagQuery.eq(TagName("category"), "electronics"),
                            TagQuery.eq(TagName("sale"), "yes"),
                        ]
                    ),
                    TagQuery.not_(TagQuery.eq(TagName("stock"), "out")),
                ]
            )
        )
        mongo_query = self.encoder.encode_query(query)
        expected_query = {
            "$or": [
                {
                    "$and": [
                        {"category": {"$ne": "electronics"}},
                        {"sale": {"$ne": "yes"}},
                    ]
                },
                {"stock": "out"},
            ]
        }
        self.assertEqual(mongo_query, expected_query, "Deeply nested NOT query mismatch")
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "category": "electronics", "stock": "in"},
                {"_id": 2, "category": "electronics", "stock": "out"},
                {"_id": 3, "sale": "yes", "stock": "in"},
                {"_id": 4, "sale": "yes"},
            ]
        )
        self.run_query_and_verify(mongo_query, [2], "Deeply nested NOT")

    # Edge Case Tests
    def test_empty_query(self):
        query = TagQuery.and_([])
        mongo_query = self.encoder.encode_query(query)
        expected_query = {}
        self.assertEqual(mongo_query, expected_query, "Empty query mismatch")
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [{"_id": 1, "field": "value"}, {"_id": 2, "other": "data"}]
        )
        self.run_query_and_verify(mongo_query, [1, 2], "Empty query")

    def test_empty_in_list(self):
        query = TagQuery.in_(TagName("field"), [])
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$in": []}}
        self.assertEqual(mongo_query, expected_query, "Empty IN list query mismatch")
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [{"_id": 1, "field": "value"}, {"_id": 2, "field": "other"}]
        )
        self.run_query_and_verify(mongo_query, [], "Empty IN list")

    def test_multiple_exists(self):
        query = TagQuery.exist([TagName("f1"), TagName("f2")])
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"$and": [{"f1": {"$exists": True}}, {"f2": {"$exists": True}}]}
        self.assertEqual(mongo_query, expected_query, "Multiple EXISTS query mismatch")
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "f1": "v1", "f2": "v2"},
                {"_id": 2, "f1": "v1"},
                {"_id": 3, "f2": "v2"},
                {"_id": 4},
            ]
        )
        self.run_query_and_verify(mongo_query, [1], "Multiple EXISTS")

    def test_special_characters(self):
        query = TagQuery.eq(TagName("f1"), "val$ue")
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"f1": "val$ue"}
        self.assertEqual(mongo_query, expected_query, "Special characters query mismatch")
        self.verify_round_trip(query, mongo_query)
        self.collection.insert_many(
            [
                {"_id": 1, "f1": "val$ue"},
                {"_id": 2, "f1": "other"},
                {"_id": 3, "f1": "val$ue"},
            ]
        )
        self.run_query_and_verify(mongo_query, [1, 3], "Special characters")


def main():
    print("Running MongoTagEncoder tests...")
    unittest.main(argv=[""], exit=False)
    print("All tests completed.")


if __name__ == "__main__":
    main()
