"""Test cases for the TagSqlEncoder class handling deeply nested queries with NOT."""

import unittest

from acapy_agent.database_manager.wql_nosql.encoders import encoder_factory
from acapy_agent.database_manager.wql_nosql.tags import TagName, TagQuery


def replace_placeholders(query, args):
    """Replace each '?' in the query with the corresponding argument.

    Properly quote arguments for SQL, escaping single quotes by doubling them.
    Example: 'O'Reilly' becomes 'O''Reilly'.
    """
    parts = query.split("?")
    if len(parts) - 1 != len(args):
        raise ValueError("Number of placeholders does not match number of arguments")
    result = parts[0]
    for part, arg in zip(parts[1:], args):
        escaped_arg = arg.replace("'", "''")  # Escape single quotes for SQL
        result += f"'{escaped_arg}'" + part
    return result


class TestTagSqlEncoder(unittest.TestCase):
    """Test cases for the TagSqlEncoder class."""

    def setUp(self):
        """Set up encoding functions for tag names and values."""
        self.enc_name = lambda x: x  # No transformation for tag names
        self.enc_value = lambda x: x  # No transformation for tag values

    def test_deeply_nested_not(self):
        """Test encoding a deeply nested TagQuery with NOT into an SQL statement."""
        # Define a deeply nested query with NOT
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

        encoder = encoder_factory.get_encoder("sqlite", self.enc_name, self.enc_value)
        query_str = encoder.encode_query(query)
        print(f"encoded query_str is :  {query_str}")

        # Expected SQL query for the deeply nested NOT query
        expected_query = (
            "((i.id NOT IN (SELECT item_id FROM items_tags WHERE name = ? "
            "AND value = ?) "
            "AND i.id NOT IN (SELECT item_id FROM items_tags WHERE name = ? "
            "AND value = ?)) "
            "OR i.id IN (SELECT item_id FROM items_tags WHERE name = ? "
            "AND value = ?))"
        )

        # Expected arguments based on the query
        expected_args = [
            "category",
            "electronics",  # From OR: category = electronics
            "sale",
            "yes",  # From OR: sale = yes
            "stock",
            "out",  # From NOT (stock = out)
        ]

        self.assertEqual(query_str, expected_query)
        self.assertEqual(encoder.arguments, expected_args)

        # Print complete SQL statements for copying and running
        print("\n### Complete SQL Statements for Testing")

        # Create tables
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")

        # Insert items with meaningful names
        print("INSERT INTO items (id, name) VALUES")
        print("    (1, 'Laptop'),")
        print("    (2, 'Phone'),")
        print("    (3, 'Chair'),")
        print("    (4, 'TV');")

        # Insert tags with meaningful arguments
        print("INSERT INTO items_tags (item_id, name, value) VALUES")
        print("    (1, 'category', 'electronics'),  -- Item 1: electronics, in stock")
        print("    (1, 'stock', 'in'),")
        print("    (2, 'category', 'electronics'),  -- Item 2: electronics, out of stock")
        print("    (2, 'stock', 'out'),")
        print("    (3, 'sale', 'yes'),              -- Item 3: on sale, in stock")
        print("    (3, 'stock', 'in'),")
        print("    (4, 'sale', 'yes');              -- Item 4: on sale, no stock tag")

        # Complete SELECT statement with values inserted
        select_query = f"SELECT * FROM items i WHERE {query_str}"
        complete_select = replace_placeholders(select_query, encoder.arguments)
        print("\n-- Complete SELECT statement with values:")
        print(complete_select)

        # Add expected result for reference
        print("\n-- Expected result: Items 2")

        # Cleanup: Delete all inserted rows
        print("\n-- Cleanup")
        print("DELETE FROM items_tags;")
        print("DELETE FROM items;")

        """
        ### Query Logic Explanation
        -- Query: NOT ((category = 'electronics' OR sale = 'yes') AND NOT (stock = 'out'))
        -- Equivalent to: (category != 'electronics' AND sale != 'yes') OR stock = 'out'
        -- Item 1:
        --   (category = 'electronics' OR sale = 'yes') -> true
        --   NOT (stock = 'out') -> true
        --   NOT (true AND true) -> false
        -- Item 2:
        --   (category = 'electronics' OR sale = 'yes') -> true
        --   NOT (stock = 'out') -> false
        --   NOT (true AND false) -> true
        -- Item 3:
        --   (category = 'electronics' OR sale = 'yes') -> false OR true -> true
        --   NOT (stock = 'out') -> true
        --   NOT (true AND true) -> false
        --   But: (category != 'electronics' AND sale != 'yes')
        --   -> false OR stock = 'out' -> true
        -- Item 4:
        --   (category = 'electronics' OR sale = 'yes') -> true
        --   NOT (stock = 'out') -> true (no stock tag)
        --   NOT (true AND true) -> false
        --   But: stock = 'out' is false, so true via OR condition
        -- Expected items: 2, 3, and 4
        """


if __name__ == "__main__":
    unittest.main()
