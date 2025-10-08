"""Test cases for the TagSqlEncoder class handling conjunctions in SQL queries.

Disabled by default to keep CI lean; enable locally with
ENABLE_WQL_SQLITE_TESTS=1 if you want to run them.
"""

import os

import pytest

if not os.getenv("ENABLE_WQL_SQLITE_TESTS"):
    pytest.skip(
        "WQL SQLite encoder tests disabled by default; set ENABLE_WQL_SQLITE_TESTS=1",
        allow_module_level=True,
    )

import unittest

from acapy_agent.database_manager.wql_nosql.encoders import TagSqlEncoder
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

    def test_comparison_conjunction(self):
        """Test encoding a conjunction of comparison operations into an SQL statement."""
        query = TagQuery.and_(
            [
                TagQuery.eq(TagName("category"), "electronics"),
                TagQuery.gt(TagName("price"), "100"),
            ]
        )

        encoder = TagSqlEncoder(self.enc_name, self.enc_value, "sqlite")
        query_str = encoder.encode_query(query)
        print(f"encoded query_str is :  {query_str}")

        expected_query = (
            "(i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value = ?) "
            "AND i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value > ?))"
        )

        expected_args = ["category", "electronics", "price", "100"]

        self.assertEqual(query_str, expected_query)
        self.assertEqual(encoder.arguments, expected_args)

        print("\n### Complete SQL Statements for Testing")

        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")

        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")

        print("INSERT INTO items_tags (item_id, name, value) VALUES")
        print("    (1, 'category', 'electronics'),  -- Item 1: electronics, price=150")
        print("    (1, 'price', '150'),")
        print("    (2, 'category', 'electronics'),  -- Item 2: electronics, price=090")
        print("    (2, 'price', '090'),")
        print("    (3, 'category', 'books'),        -- Item 3: books, price=120")
        print("    (3, 'price', '120'),")
        print("    (4, 'category', 'electronics'),  -- Item 4: electronics, price=200")
        print("    (4, 'price', '200');")

        select_query = f"SELECT * FROM items i WHERE {query_str}"
        complete_select = replace_placeholders(select_query, encoder.arguments)
        print("\n-- Complete SELECT statement with values:")
        print(complete_select)

        print("\n-- Expected result: Items 1 and 4")

        print("\n-- Cleanup")
        print("DELETE FROM items_tags;")
        print("DELETE FROM items;")

        """
        ### SQLite Insert Statements
        CREATE TABLE items (id INTEGER PRIMARY KEY);
        CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);

        INSERT INTO items (id) VALUES (1), (2), (3), (4);

        INSERT INTO items_tags (item_id, name, value) VALUES
            (1, 'category', 'electronics'),
            (1, 'price', '150'),
            (2, 'category', 'electronics'),
            (2, 'price', '090'),
            (3, 'category', 'books'),
            (3, 'price', '120'),
            (4, 'category', 'electronics'),
            (4, 'price', '200');

        ### Expected Result
        Query: category = 'electronics' AND price > '100'
        - Item 1: 'electronics', '150' > '100' -> true
        - Item 2: 'electronics', '090' < '100' -> false
        - Item 3: 'books', '120' -> false
        - Item 4: 'electronics', '200' > '100' -> true
        Expected items: 1 and 4
        """


if __name__ == "__main__":
    unittest.main()
