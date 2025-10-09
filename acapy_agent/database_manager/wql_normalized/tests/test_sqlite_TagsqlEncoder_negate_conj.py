# pytest --maxfail=1 --disable-warnings --no-cov -s -vv acapy_agent/database_manager/wql_normalized/tests/test_sqlite_TagsqlEncoder_negate_conj.py
# python -m unittest acapy_agent/database_manager/wql_normalized/tests/test_sqlite_TagsqlEncoder_negate_conj.py


"""Test cases for the TagSqlEncoder class handling negated conjunctions in SQL queries."""

import unittest

from acapy_agent.database_manager.wql_normalized.encoders import encoder_factory
from acapy_agent.database_manager.wql_normalized.tags import TagName, TagQuery


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
        """A setUp method to initialize the enc_name and enc_value attributes."""
        self.enc_name = lambda x: x
        self.enc_value = lambda x: x

    def test_negate_conj(self):
        """Test encoding a negated conjunction TagQuery into an SQL statement."""
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

        encoder = encoder_factory.get_encoder("sqlite", self.enc_name, self.enc_value)

        query_str = encoder.encode_query(query)
        print(f"encoded query_str is :  {query_str}")

        expected_query = (
            "NOT ((i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value = ?) "
            "AND i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value = ?)) "
            "OR (i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value = ?) "
            "AND i.id NOT IN (SELECT item_id FROM items_tags WHERE name = ? AND value = ?)))"
        )

        expected_args = [
            "category",
            "electronics",  # From NOT (category = electronics) in condition_1
            "status",
            "in_stock",  # From NOT (status = in_stock) in condition_1
            "category",
            "electronics",  # From NOT (category = electronics) in condition_2
            "status",
            "sold_out",  # From status = sold_out in condition_2
        ]

        self.assertEqual(query_str, expected_query)
        self.assertEqual(encoder.arguments, expected_args)

        # Print complete SQL statements for copying and running
        print("\n### Complete SQL Statements for Testing")

        # Create tables
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")

        # Insert items
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")

        # Insert tags
        print("INSERT INTO items_tags (item_id, name, value) VALUES")
        print("    (1, 'category', 'electronics'),  -- Item 1: electronics, in_stock")
        print("    (1, 'status', 'in_stock'),")
        print("    (2, 'category', 'electronics'),  -- Item 2: electronics, sold_out")
        print("    (2, 'status', 'sold_out'),")
        print("    (3, 'category', 'books'),        -- Item 3: books, in_stock")
        print("    (3, 'status', 'in_stock'),")
        print("    (4, 'category', 'clothing');     -- Item 4: clothing, no status")

        # Complete SELECT statement with values inserted
        select_query = f"SELECT * FROM items i WHERE {query_str}"
        complete_select = replace_placeholders(select_query, encoder.arguments)
        print("\n-- Complete SELECT statement with values:")
        print(complete_select)

        # Add expected result for reference
        print("\n-- Expected result: Items 2,3 and 4")
        # Comments with insert statements and expected results

        # Cleanup: Delete all inserted rows
        print("\n-- Cleanup")
        print("DELETE FROM items_tags;")
        print("DELETE FROM items;")


if __name__ == "__main__":
    unittest.main()
