# """Test cases for MongoTagEncoder with In and Exist conjunctions."""

import json
import unittest

from acapy_agent.database_manager.wql_nosql.encoders import encoder_factory
from acapy_agent.database_manager.wql_nosql.tags import TagName, TagQuery


class TestMongoTagEncoder(unittest.TestCase):
    """Test cases for the MongoTagEncoder class."""

    def test_in_and_exist_conjunction(self):
        """Test encoding an In and Exist conjunction into MongoDB query."""
        # Define the query: color in ['red', 'blue'] AND size exists
        query = TagQuery.and_(
            [
                TagQuery.in_(TagName("color"), ["red", "blue"]),
                TagQuery.exist([TagName("size")]),
            ]
        )

        # Set up encoding functions
        def enc_name(x):
            return x  # No transformation for names

        def enc_value(x):
            return x  # No transformation for values

        # Get the encoder for MongoDB
        encoder = encoder_factory.get_encoder("mongodb", enc_name, enc_value)

        # Encode the query
        mongo_query = encoder.encode_query(query)

        # Print the generated query for debugging
        print("\nGenerated MongoDB Query:")
        print(json.dumps(mongo_query, indent=2))

        # Define the expected MongoDB query
        expected_query = {
            "$and": [{"color": {"$in": ["red", "blue"]}}, {"size": {"$exists": True}}]
        }

        # Print the expected query for comparison
        print("\nExpected MongoDB Query:")
        print(json.dumps(expected_query, indent=2))

        # Assert that the generated query matches the expected query
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
        print("   db.items.drop()  // Clear existing collection")
        print("   db.items.insertMany([")
        print("       { _id: 1, color: 'red', size: 'M' },")
        print("       { _id: 2, color: 'blue' },")
        print("       { _id: 3, color: 'green', size: 'L' },")
        print("       { _id: 4, size: 'S' },")
        print("       { _id: 5, color: 'blue', size: 'S' }")
        print("   ])")
        print("   ```")
        print("4. Run the generated query:")
        print("   ```javascript")
        print(f"   db.items.find({json.dumps(mongo_query)})")
        print("   ```")
        print("5. Expected result: Documents with _id: 1 and 5")
        print("   - _id: 1: color='red' (in ['red', 'blue']), size='M' (exists)")
        print("   - _id: 5: color='blue' (in ['red', 'blue']), size='S' (exists)")
        print("6. Clean up (optional):")
        print("   ```javascript")
        print("   db.items.drop()")
        print("   ```")


if __name__ == "__main__":
    unittest.main()
