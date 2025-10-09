"""Test cases for the MongoTagEncoder class handling conjunctions in MongoDB queries."""

import json
import unittest

from acapy_agent.database_manager.wql_nosql.encoders import encoder_factory
from acapy_agent.database_manager.wql_nosql.tags import TagName, TagQuery


class TestMongoTagEncoder(unittest.TestCase):
    def test_comparison_conjunction(self):
        """Test encoding a conjunction of comparison operations into a MongoDB query."""
        # Define the query: category == "electronics" AND price > "100"
        query = TagQuery.and_(
            [
                TagQuery.eq(TagName("category"), "electronics"),
                TagQuery.gt(TagName("price"), "100"),
            ]
        )

        # Set up encoding functions with identity transformations
        def enc_name(x):
            return x  # No transformation for tag names

        def enc_value(x):
            return x  # No transformation for tag values

        # Encode the query using MongoTagEncoder
        encoder = encoder_factory.get_encoder("mongodb", enc_name, enc_value)
        mongo_query = encoder.encode_query(query)

        # Print the generated query for debugging
        print("\nGenerated MongoDB Query:")
        print(json.dumps(mongo_query, indent=2))

        # Define the expected MongoDB query
        # Note: Since price is stored as a string, the comparison is lexicographical
        expected_query = {
            "$and": [{"category": "electronics"}, {"price": {"$gt": "100"}}]
        }

        # Print the expected query for comparison
        print("\nExpected MongoDB Query:")
        print(json.dumps(expected_query, indent=2))

        # Assert that the generated query matches the expected query
        self.assertEqual(mongo_query, expected_query)

        # Provide instructions for manual testing with mongosh
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
        print("   db.items.drop()  // Clear existing collection")
        print("   db.items.insertMany([")
        print("       { _id: 1, category: 'electronics', price: '150' },")
        print("       { _id: 2, category: 'electronics', price: '090' },")
        print("       { _id: 3, category: 'books', price: '120' },")
        print("       { _id: 4, category: 'electronics', price: '200' }")
        print("   ])")
        print("   ```")
        print("4. Run the generated query:")
        print("   ```javascript")
        print(f"   db.items.find({json.dumps(mongo_query)})")
        print("   ```")
        print("5. Expected result: Documents with _id: 1 and 4")
        print(
            "   - _id: 1: category='electronics', price='150' > '100' (lexicographical)"
        )
        print(
            "   - _id: 2: category='electronics', price='090' < '100' (lexicographical)"
        )
        print("   - _id: 3: category='books', price='120' (category mismatch)")
        print(
            "   - _id: 4: category='electronics', price='200' > '100' (lexicographical)"
        )

        # Clean up instructions
        print("6. Clean up (optional):")
        print("   ```javascript")
        print("   db.items.drop()")
        print("   ```")


if __name__ == "__main__":
    unittest.main()
