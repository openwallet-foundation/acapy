"""Test cases for the MongoTagEncoder class handling negated conjunctions in MongoDB queries."""

import json
import unittest

from acapy_agent.database_manager.wql_nosql.encoders import encoder_factory
from acapy_agent.database_manager.wql_nosql.tags import TagName, TagQuery


class TestMongoTagEncoder(unittest.TestCase):
    def test_negate_conj(self):
        # Define a negated conjunction query: NOT (OR (condition_1, condition_2))
        condition_1 = TagQuery.and_(
            [
                TagQuery.eq(TagName("category"), "electronics"),
                TagQuery.eq(TagName("status"), "in_stock"),
            ]
        )
        condition_2 = TagQuery.and_(
            [
                TagQuery.eq(TagName("category"), "electronics"),
                TagQuery.not_(TagQuery.eq(TagName("status"), "sold_out")),
            ]
        )
        query = TagQuery.not_(TagQuery.or_([condition_1, condition_2]))

        def enc_name(x):
            return x  # No transformation for tag names

        def enc_value(x):
            return x  # No transformation for tag values

        # Encode the query
        encoder = encoder_factory.get_encoder("mongodb", enc_name, enc_value)
        mongo_query = encoder.encode_query(query)

        # Print the generated query for debugging
        print("\nGenerated MongoDB Query:")
        print(json.dumps(mongo_query, indent=2))

        # Expected MongoDB query: AND (NOT condition_1, NOT condition_2)
        # NOT condition_1: OR (category != "electronics", status != "in_stock")
        # NOT condition_2: OR (category != "electronics", status == "sold_out")
        expected_query = {
            "$and": [
                {
                    "$or": [
                        {"category": {"$ne": "electronics"}},
                        {"status": {"$ne": "in_stock"}},
                    ]
                },
                {"$or": [{"category": {"$ne": "electronics"}}, {"status": "sold_out"}]},
            ]
        }

        # Print the expected query for comparison
        print("\nExpected MongoDB Query:")
        print(json.dumps(expected_query, indent=2))

        self.assertEqual(mongo_query, expected_query)

        # Instructions for manual testing with mongosh
        print("\n### Manual Testing Instructions with mongosh")
        print("To verify the query manually, follow these steps:")
        print("1. Open a terminal and start mongosh:")
        print("   ```bash")
        print("   mongosh")
        print("   ```")
        print("2. Switch to or create a test database:")
        print("   ```javascript")
        print("   use test_db")
        print("   ```")
        print("3. Create a collection and insert sample documents:")
        print("   ```javascript")
        print("   db.items.drop()")  # Clear existing collection
        print("   db.items.insertMany([")
        print("       { _id: 1, category: 'electronics', status: 'in_stock' },")
        print("       { _id: 2, category: 'electronics', status: 'sold_out' },")
        print("       { _id: 3, category: 'books', status: 'in_stock' },")
        print("       { _id: 4, category: 'clothing' }")
        print(")]")
        print("   ```")
        print("4. Run the generated query:")
        print("   ```javascript")
        print(f"   db.items.find({json.dumps(mongo_query)})")
        print("   ```")
        print("5. Expected result: Documents with _id: 2, 3, and 4")
        print("   - _id: 1 is excluded (matches condition_1)")
        print("   - _id: 2 matches (electronics and sold_out)")
        print("   - _id: 3 matches (not electronics)")
        print("   - _id: 4 matches (not electronics)")
        print("6. Clean up (optional):")
        print("   ```javascript")
        print("   db.items.drop()")
        print("   ```")


if __name__ == "__main__":
    unittest.main()
