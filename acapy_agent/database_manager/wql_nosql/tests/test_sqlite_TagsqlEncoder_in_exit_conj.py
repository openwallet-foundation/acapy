"""Test cases for TagSqlEncoder with In and Exist conjunctions."""

import unittest

from acapy_agent.database_manager.wql_nosql.encoders import encoder_factory
from acapy_agent.database_manager.wql_nosql.tags import TagName, TagQuery


def replace_placeholders(query, args):
    """Replace each '?' in the query with the corresponding argument."""
    parts = query.split("?")
    if len(parts) - 1 != len(args):
        raise ValueError("Mismatch in placeholders and arguments")
    result = parts[0]
    for part, arg in zip(parts[1:], args):
        escaped_arg = arg.replace("'", "''")
        result += f"'{escaped_arg}'" + part
    return result


class TestTagSqlEncoder(unittest.TestCase):
    """Test cases for the TagSqlEncoder class."""

    def setUp(self):
        """Set up encoding functions for tag names and values."""
        self.enc_name = lambda x: x  # No transformation for names
        self.enc_value = lambda x: x  # No transformation for values

    def test_in_and_exist_conjunction(self):
        """Test encoding an In and Exist conjunction into SQL."""
        # Query: color in ['red', 'blue'] AND size exists
        query = TagQuery.and_(
            [
                TagQuery.in_(TagName("color"), ["red", "blue"]),
                TagQuery.exist([TagName("size")]),
            ]
        )

        encoder = encoder_factory.get_encoder("sqlite", self.enc_name, self.enc_value)
        query_str = encoder.encode_query(query)
        # Optional: Uncomment the next line for debugging
        # print(f"encoded query_str is: {query_str}")

        # Expected SQL for the And conjunction
        expected_query = (
            "(i.id IN (SELECT item_id FROM items_tags WHERE name = ? "
            "AND value IN (?, ?)) "
            "AND i.id IN (SELECT item_id FROM items_tags WHERE name = ?))"
        )

        # Expected arguments in order
        expected_args = ["color", "red", "blue", "size"]

        self.assertEqual(query_str, expected_query)
        self.assertEqual(encoder.arguments, expected_args)

        # Generate the complete SELECT statement with values
        select_query = f"SELECT * FROM items i WHERE {query_str}"
        complete_select = replace_placeholders(select_query, encoder.arguments)

        # Print the complete SQL script as a single cohesive block
        print("\n### Complete SQL Script (Copy from here to the end)")
        print("""
-- Drop tables if they exist to ensure a clean slate
DROP TABLE IF EXISTS items_tags;
DROP TABLE IF EXISTS items;

-- Create tables for items and their tags
CREATE TABLE items (id INTEGER PRIMARY KEY);
CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);

-- Insert sample items
INSERT INTO items (id) VALUES (1), (2), (3), (4), (5);

-- Insert tags for each item
INSERT INTO items_tags (item_id, name, value) VALUES
    (1, 'color', 'red'),   -- Item 1: red, size M
    (1, 'size', 'M'),
    (2, 'color', 'blue'),  -- Item 2: blue, no size
    (3, 'color', 'green'), -- Item 3: green, size L
    (3, 'size', 'L'),
    (4, 'size', 'S'),      -- Item 4: no color, size S
    (5, 'color', 'blue'),  -- Item 5: blue, size S
    (5, 'size', 'S');

-- Select items where color is 'red' or 'blue' AND size exists
""")
        print(complete_select + ";")
        print("""
-- Expected result: Should return items 1 and 5
-- Item 1 has color 'red' and size 'M'
-- Item 5 has color 'blue' and size 'S'
""")


if __name__ == "__main__":
    unittest.main()
