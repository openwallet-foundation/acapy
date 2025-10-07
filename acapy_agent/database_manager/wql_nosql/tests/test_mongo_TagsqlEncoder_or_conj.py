"""Test cases for the MongoTagEncoder class handling OR conjunctions in MongoDB queries."""

import json
import unittest

from acapy_agent.database_manager.wql_nosql.encoders import encoder_factory
from acapy_agent.database_manager.wql_nosql.tags import TagName, TagQuery


class TestMongoTagEncoder(unittest.TestCase):
    def test_or_conjunction(self):
        # Define the query: (tag_a = "value_a" AND tag_b = "value_b") OR (tag_a = "value_a" AND tag_b != "value_c")
        condition_1 = TagQuery.and_(
            [
                TagQuery.eq(TagName("tag_a"), "value_a"),
                TagQuery.eq(TagName("tag_b"), "value_b"),
            ]
        )
        condition_2 = TagQuery.and_(
            [
                TagQuery.eq(TagName("tag_a"), "value_a"),
                TagQuery.not_(TagQuery.eq(TagName("tag_b"), "value_c")),
            ]
        )
        query = TagQuery.or_([condition_1, condition_2])

        # Encoding functions (identity functions)
        def enc_name(x):
            return x

        def enc_value(x):
            return x

        # Get the MongoDB encoder
        encoder = encoder_factory.get_encoder("mongodb", enc_name, enc_value)

        # Encode the query
        mongo_query = encoder.encode_query(query)

        # Print the generated query for debugging
        print("\nGenerated MongoDB Query:")
        print(json.dumps(mongo_query, indent=2))

        # Expected MongoDB query
        expected_query = {
            "$or": [
                {"$and": [{"tag_a": "value_a"}, {"tag_b": "value_b"}]},
                {"$and": [{"tag_a": "value_a"}, {"tag_b": {"$ne": "value_c"}}]},
            ]
        }

        # Print the expected query for comparison
        print("\nExpected MongoDB Query:")
        print(json.dumps(expected_query, indent=2))

        # Assert equality
        self.assertEqual(mongo_query, expected_query)

        # Manual testing instructions
        print("\n### Manual Testing Instructions with mongosh")
        print("To verify the query manually, follow these steps:")
        print("1. Start mongosh:")
        print("   ```bash")
        print("   mongosh")
        print("   ```")
        print("2. Switch to a test database:")
        print("   ```javascript")
        print("   use test_db")
        print("   ```")
        print("3. Insert sample documents:")
        print("   ```javascript")
        print("   db.items.drop()")
        print("   db.items.insertMany([")
        print("       { _id: 1, tag_a: 'value_a', tag_b: 'value_b' },")
        print("       { _id: 2, tag_a: 'value_a', tag_b: 'value_c' },")
        print("       { _id: 3, tag_a: 'value_d', tag_b: 'value_b' },")
        print("       { _id: 4, tag_a: 'value_a' }")
        print("   ])")
        print("   ```")
        print("4. Run the query:")
        print("   ```javascript")
        print(f"   db.items.find({json.dumps(mongo_query)})")
        print("   ```")
        print("5. Expected result: Documents with _id: 1 and 4")
        print(
            "   - _id: 1 matches first condition (tag_a = 'value_a' AND tag_b = 'value_b')"
        )
        print(
            "   - _id: 4 matches second condition (tag_a = 'value_a' AND tag_b != 'value_c')"
        )
        print("6. Clean up (optional):")
        print("   ```javascript")
        print("   db.items.drop()")
        print("   ```")


if __name__ == "__main__":
    unittest.main()
