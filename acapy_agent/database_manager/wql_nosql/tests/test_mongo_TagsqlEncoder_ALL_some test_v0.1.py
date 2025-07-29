import unittest
import logging
from pymongo import MongoClient
from ..tags import TagQuery, TagName
from ..encoders import encoder_factory

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestMongoTagEncoder(unittest.TestCase):
    def setUp(self):
        """Set up MongoDB connection and ensure collection is clean."""
        self.db_uri = "mongodb://admin:securepassword@192.168.2.155:27017/acapy_test_db?authSource=admin"
        try:
            self.client = MongoClient(self.db_uri)
            self.db = self.client['acapy_test_db']
            self.collection = self.db['items']
            # Drop collection to ensure clean state
            self.collection.drop()
            logger.info("Collection 'items' dropped in setUp")
        except Exception as e:
            logger.error(f"Failed to set up MongoDB connection: {e}")
            raise

        # Encoding functions (identity functions)
        self.enc_name = lambda x: x
        self.enc_value = lambda x: x
        self.encoder = encoder_factory.get_encoder("mongodb", self.enc_name, self.enc_value)

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
        actual_ids = sorted([doc['_id'] for doc in results])
        self.assertEqual(actual_ids, expected_ids, f"{test_name} failed: Expected _ids {expected_ids}, got {actual_ids}")

    # Existing test methods
    def test_comparison_conjunction(self):
        """Test encoding a conjunction of comparison operations."""
        query = TagQuery.And([
            TagQuery.Eq(TagName("category"), "electronics"),
            TagQuery.Gt(TagName("price"), "100")
        ])
        mongo_query = self.encoder.encode_query(query)
        expected_query = {
            "$and": [
                {"category": "electronics"},
                {"price": {"$gt": "100"}}
            ]
        }
        self.assertEqual(mongo_query, expected_query, "Comparison conjunction query mismatch")

        # Insert sample documents
        self.collection.insert_many([
            {"_id": 1, "category": "electronics", "price": "150"},
            {"_id": 2, "category": "electronics", "price": "090"},
            {"_id": 3, "category": "books", "price": "120"},
            {"_id": 4, "category": "electronics", "price": "200"}
        ])

        # Verify actual results
        self.run_query_and_verify(mongo_query, [1, 4], "Comparison conjunction")

    def test_deeply_nested_not(self):
        """Test encoding a deeply nested NOT query."""
        query = TagQuery.Not(
            TagQuery.And([
                TagQuery.Or([
                    TagQuery.Eq(TagName("category"), "electronics"),
                    TagQuery.Eq(TagName("sale"), "yes")
                ]),
                TagQuery.Not(TagQuery.Eq(TagName("stock"), "out"))
            ])
        )
        mongo_query = self.encoder.encode_query(query)
        expected_query = {
            "$or": [
                {
                    "$and": [
                        {"category": {"$ne": "electronics"}},
                        {"sale": {"$ne": "yes"}}
                    ]
                },
                {"stock": "out"}
            ]
        }
        self.assertEqual(mongo_query, expected_query, "Deeply nested NOT query mismatch")

        # Insert sample documents
        self.collection.insert_many([
            {"_id": 1, "category": "electronics", "stock": "in"},
            {"_id": 2, "category": "electronics", "stock": "out"},
            {"_id": 3, "sale": "yes", "stock": "in"},
            {"_id": 4, "sale": "yes"}
        ])

        # Verify actual results
        self.run_query_and_verify(mongo_query, [2], "Deeply nested NOT")

    def test_negate_conj(self):
        """Test encoding a negated conjunction query."""
        condition_1 = TagQuery.And([
            TagQuery.Eq(TagName("category"), "electronics"),
            TagQuery.Eq(TagName("status"), "in_stock")
        ])
        condition_2 = TagQuery.And([
            TagQuery.Eq(TagName("category"), "electronics"),
            TagQuery.Not(TagQuery.Eq(TagName("status"), "sold_out"))
        ])
        query = TagQuery.Not(TagQuery.Or([condition_1, condition_2]))
        mongo_query = self.encoder.encode_query(query)
        expected_query = {
            "$and": [
                {"$or": [
                    {"category": {"$ne": "electronics"}},
                    {"status": {"$ne": "in_stock"}}
                ]},
                {"$or": [
                    {"category": {"$ne": "electronics"}},
                    {"status": "sold_out"}
                ]}
            ]
        }
        self.assertEqual(mongo_query, expected_query, "Negated conjunction query mismatch")

        # Insert sample documents
        self.collection.insert_many([
            {"_id": 1, "category": "electronics", "status": "in_stock"},
            {"_id": 2, "category": "electronics", "status": "sold_out"},
            {"_id": 3, "category": "books", "status": "in_stock"},
            {"_id": 4, "category": "clothing"}
        ])

        # Verify actual results
        self.run_query_and_verify(mongo_query, [2, 3, 4], "Negated conjunction")

    def test_in_and_exist_conjunction(self):
        """Test encoding an In and Exist conjunction."""
        query = TagQuery.And([
            TagQuery.In(TagName("color"), ["red", "blue"]),
            TagQuery.Exist([TagName("size")])
        ])
        mongo_query = self.encoder.encode_query(query)
        expected_query = {
            "$and": [
                {"color": {"$in": ["red", "blue"]}},
                {"size": {"$exists": True}}
            ]
        }
        self.assertEqual(mongo_query, expected_query, "In and Exist conjunction query mismatch")

        # Insert sample documents
        self.collection.insert_many([
            {"_id": 1, "color": "red", "size": "M"},
            {"_id": 2, "color": "blue"},
            {"_id": 3, "color": "green", "size": "L"},
            {"_id": 4, "size": "S"},
            {"_id": 5, "color": "blue", "size": "S"}
        ])

        # Verify actual results
        self.run_query_and_verify(mongo_query, [1, 5], "In and Exist conjunction")

    def test_or_conjunction(self):
        """Test encoding an OR conjunction query."""
        condition_1 = TagQuery.And([
            TagQuery.Eq(TagName("tag_a"), "value_a"),
            TagQuery.Eq(TagName("tag_b"), "value_b")
        ])
        condition_2 = TagQuery.And([
            TagQuery.Eq(TagName("tag_a"), "value_a"),
            TagQuery.Not(TagQuery.Eq(TagName("tag_b"), "value_c"))
        ])
        query = TagQuery.Or([condition_1, condition_2])
        mongo_query = self.encoder.encode_query(query)
        expected_query = {
            "$or": [
                {
                    "$and": [
                        {"tag_a": "value_a"},
                        {"tag_b": "value_b"}
                    ]
                },
                {
                    "$and": [
                        {"tag_a": "value_a"},
                        {"tag_b": {"$ne": "value_c"}}
                    ]
                }
            ]
        }
        self.assertEqual(mongo_query, expected_query, "OR conjunction query mismatch")

        # Insert sample documents
        self.collection.insert_many([
            {"_id": 1, "tag_a": "value_a", "tag_b": "value_b"},
            {"_id": 2, "tag_a": "value_a", "tag_b": "value_c"},
            {"_id": 3, "tag_a": "value_d", "tag_b": "value_b"},
            {"_id": 4, "tag_a": "value_a"}
        ])

        # Verify actual results
        self.run_query_and_verify(mongo_query, [1, 4], "OR conjunction")

    # New test methods for individual operators
    def test_eq_positive(self):
        """Test encoding a positive equality query."""
        query = TagQuery.Eq(TagName("field"), "value")
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": "value"}
        self.assertEqual(mongo_query, expected_query, "Positive equality query mismatch")

        # Insert sample documents
        self.collection.insert_many([
            {"_id": 1, "field": "value"},
            {"_id": 2, "field": "other"},
            {"_id": 3, "field": "value"}
        ])

        # Verify actual results
        self.run_query_and_verify(mongo_query, [1, 3], "Positive equality")

    def test_eq_negated(self):
        """Test encoding a negated equality query."""
        query = TagQuery.Not(TagQuery.Eq(TagName("field"), "value"))
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$ne": "value"}}
        self.assertEqual(mongo_query, expected_query, "Negated equality query mismatch")

    def test_neq_positive(self):
        """Test encoding a positive inequality query."""
        query = TagQuery.Neq(TagName("field"), "value")
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$ne": "value"}}
        self.assertEqual(mongo_query, expected_query, "Positive inequality query mismatch")

    def test_neq_negated(self):
        """Test encoding a negated inequality query."""
        query = TagQuery.Not(TagQuery.Neq(TagName("field"), "value"))
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": "value"}
        self.assertEqual(mongo_query, expected_query, "Negated inequality query mismatch")

    def test_gt_positive(self):
        """Test encoding a positive greater-than query."""
        query = TagQuery.Gt(TagName("field"), "10")
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$gt": "10"}}
        self.assertEqual(mongo_query, expected_query, "Positive greater-than query mismatch")

    def test_gt_negated(self):
        """Test encoding a negated greater-than query."""
        query = TagQuery.Not(TagQuery.Gt(TagName("field"), "10"))
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$not": {"$gt": "10"}}}
        self.assertEqual(mongo_query, expected_query, "Negated greater-than query mismatch")

    def test_gte_positive(self):
        """Test encoding a positive greater-than-or-equal query."""
        query = TagQuery.Gte(TagName("field"), "10")
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$gte": "10"}}
        self.assertEqual(mongo_query, expected_query, "Positive greater-than-or-equal query mismatch")

    def test_gte_negated(self):
        """Test encoding a negated greater-than-or-equal query."""
        query = TagQuery.Not(TagQuery.Gte(TagName("field"), "10"))
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$not": {"$gte": "10"}}}
        self.assertEqual(mongo_query, expected_query, "Negated greater-than-or-equal query mismatch")

    def test_lt_positive(self):
        """Test encoding a positive less-than query."""
        query = TagQuery.Lt(TagName("field"), "10")
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$lt": "10"}}
        self.assertEqual(mongo_query, expected_query, "Positive less-than query mismatch")

    def test_lt_negated(self):
        """Test encoding a negated less-than query."""
        query = TagQuery.Not(TagQuery.Lt(TagName("field"), "10"))
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$not": {"$lt": "10"}}}
        self.assertEqual(mongo_query, expected_query, "Negated less-than query mismatch")

    def test_lte_positive(self):
        """Test encoding a positive less-than-or-equal query."""
        query = TagQuery.Lte(TagName("field"), "10")
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$lte": "10"}}
        self.assertEqual(mongo_query, expected_query, "Positive less-than-or-equal query mismatch")

    def test_lte_negated(self):
        """Test encoding a negated less-than-or-equal query."""
        query = TagQuery.Not(TagQuery.Lte(TagName("field"), "10"))
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$not": {"$lte": "10"}}}
        self.assertEqual(mongo_query, expected_query, "Negated less-than-or-equal query mismatch")

    def test_like_positive(self):
        """Test encoding a positive LIKE query."""
        query = TagQuery.Like(TagName("field"), "pattern")
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$regex": "pattern"}}
        self.assertEqual(mongo_query, expected_query, "Positive LIKE query mismatch")

    def test_like_negated(self):
        """Test encoding a negated LIKE query."""
        query = TagQuery.Not(TagQuery.Like(TagName("field"), "pattern"))
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$not": {"$regex": "pattern"}}}
        self.assertEqual(mongo_query, expected_query, "Negated LIKE query mismatch")

    def test_in_positive(self):
        """Test encoding a positive IN query."""
        query = TagQuery.In(TagName("field"), ["a", "b"])
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$in": ["a", "b"]}}
        self.assertEqual(mongo_query, expected_query, "Positive IN query mismatch")

    def test_in_negated(self):
        """Test encoding a negated IN query."""
        query = TagQuery.Not(TagQuery.In(TagName("field"), ["a", "b"]))
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$nin": ["a", "b"]}}
        self.assertEqual(mongo_query, expected_query, "Negated IN query mismatch")

    def test_exist_positive(self):
        """Test encoding a positive EXIST query."""
        query = TagQuery.Exist([TagName("field")])
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$exists": True}}
        self.assertEqual(mongo_query, expected_query, "Positive EXIST query mismatch")

    def test_exist_negated(self):
        """Test encoding a negated EXIST query."""
        query = TagQuery.Not(TagQuery.Exist([TagName("field")]))
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$exists": False}}
        self.assertEqual(mongo_query, expected_query, "Negated EXIST query mismatch")

    # New test methods for conjunctions
    def test_and_multiple(self):
        """Test encoding an AND query with multiple subqueries."""
        query = TagQuery.And([
            TagQuery.Eq(TagName("f1"), "v1"),
            TagQuery.Gt(TagName("f2"), "10")
        ])
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"$and": [{"f1": "v1"}, {"f2": {"$gt": "10"}}]}
        self.assertEqual(mongo_query, expected_query, "AND multiple query mismatch")

    def test_or_multiple(self):
        """Test encoding an OR query with multiple subqueries."""
        query = TagQuery.Or([
            TagQuery.Eq(TagName("f1"), "v1"),
            TagQuery.Gt(TagName("f2"), "10")
        ])
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"$or": [{"f1": "v1"}, {"f2": {"$gt": "10"}}]}
        self.assertEqual(mongo_query, expected_query, "OR multiple query mismatch")

    def test_nested_and_or(self):
        """Test encoding a nested AND/OR query."""
        query = TagQuery.And([
            TagQuery.Eq(TagName("f1"), "v1"),
            TagQuery.Or([
                TagQuery.Gt(TagName("f2"), "10"),
                TagQuery.Lt(TagName("f3"), "5")
            ])
        ])
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"$and": [{"f1": "v1"}, {"$or": [{"f2": {"$gt": "10"}}, {"f3": {"$lt": "5"}}]}]}
        self.assertEqual(mongo_query, expected_query, "Nested AND/OR query mismatch")

    # New test methods for complex queries
    def test_mixed_operators(self):
        """Test encoding a query with mixed operators."""
        query = TagQuery.And([
            TagQuery.Eq(TagName("f1"), "v1"),
            TagQuery.Not(TagQuery.In(TagName("f2"), ["a", "b"])),
            TagQuery.Like(TagName("f3"), "pat")
        ])
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"$and": [{"f1": "v1"}, {"f2": {"$nin": ["a", "b"]}}, {"f3": {"$regex": "pat"}}]}
        self.assertEqual(mongo_query, expected_query, "Mixed operators query mismatch")

    # New test methods for edge cases
    def test_empty_query(self):
        """Test encoding an empty query."""
        query = TagQuery.And([])
        mongo_query = self.encoder.encode_query(query)
        expected_query = {}
        self.assertEqual(mongo_query, expected_query, "Empty query mismatch")

    def test_empty_in_list(self):
        """Test encoding an IN query with an empty list."""
        query = TagQuery.In(TagName("field"), [])
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"field": {"$in": []}}
        self.assertEqual(mongo_query, expected_query, "Empty IN list query mismatch")

    def test_multiple_exists(self):
        """Test encoding an EXIST query with multiple fields."""
        query = TagQuery.Exist([TagName("f1"), TagName("f2")])
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"$and": [{"f1": {"$exists": True}}, {"f2": {"$exists": True}}]}
        self.assertEqual(mongo_query, expected_query, "Multiple EXISTS query mismatch")

    def test_special_characters(self):
        """Test encoding a query with special characters in names and values."""
        query = TagQuery.Eq(TagName("f.1"), "val$ue")
        mongo_query = self.encoder.encode_query(query)
        expected_query = {"f.1": "val$ue"}
        self.assertEqual(mongo_query, expected_query, "Special characters query mismatch")

def main():
    """Run all test cases."""
    print("Running MongoTagEncoder tests...")
    unittest.main(argv=[''], exit=False)
    print("All tests completed.")

if __name__ == "__main__":
    main()