import json
import unittest

from acapy_agent.database_manager.wql_nosql.encoders import encoder_factory
from acapy_agent.database_manager.wql_nosql.tags import TagName, TagQuery


class TestMongoTagEncoder(unittest.TestCase):
    def test_deeply_nested_not(self):
        # Define the query: NOT ((category = "electronics" OR sale = "yes") AND NOT (stock = "out"))
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

        # Encoding functions (identity functions as no transformation needed)
        def enc_name(x):
            return x

        def enc_value(x):
            return x

        # Get the MongoDB encoder
        encoder = encoder_factory.get_encoder("mongodb", enc_name, enc_value)

        # Encode the query into a MongoDB query document
        mongo_query = encoder.encode_query(query)

        # Print the generated query for debugging
        print("\nGenerated MongoDB Query:")
        print(json.dumps(mongo_query, indent=2))

        # Expected MongoDB query: (category != "electronics" AND sale != "yes") OR stock = "out"
        expected_query = {
            "$or": [
                {
                    "$and": [
                        {"category": {"$ne": "electronics"}},
                        {"sale": {"$ne": "yes"}},
                    ]
                },
                {"stock": "out"},  # Updated to shorthand notation
            ]
        }

        # Print the expected query for comparison
        print("\nExpected MongoDB Query:")
        print(json.dumps(expected_query, indent=2))

        # Assert that the generated query matches the expected query
        self.assertEqual(mongo_query, expected_query)

        # Manual testing instructions for verification in MongoDB
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
        print("       { _id: 1, category: 'electronics', stock: 'in' },")
        print("       { _id: 2, category: 'electronics', stock: 'out' },")
        print("       { _id: 3, sale: 'yes', stock: 'in' },")
        print("       { _id: 4, sale: 'yes' }")
        print("   ])")
        print("   ```")
        print("4. Run the query:")
        print("   ```javascript")
        print(f"   db.items.find({json.dumps(mongo_query)})")
        print("   ```")
        print("5. Expected result: Only document with _id: 2")
        print(
            "   - _id: 1 excluded: (category = 'electronics' AND stock != 'out') -> false"
        )
        print("   - _id: 2 included: stock = 'out' -> true")
        print("   - _id: 3 excluded: (sale = 'yes' AND stock != 'out') -> false")
        print("   - _id: 4 excluded: (sale = 'yes' AND no stock) -> false")
        print("6. Clean up (optional):")
        print("   ```javascript")
        print("   db.items.drop()")
        print("   ```")


if __name__ == "__main__":
    unittest.main()
