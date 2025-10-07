# pytest --maxfail=1 --disable-warnings --no-cov -s -vv acapy_agent/database_manager/wql_normalized/tests/test_sqlite_TagsqlEncoder_compare_conj_normalized.py
# python -m unittest acapy_agent/database_manager/wql_normalized/tests/test_sqlite_TagsqlEncoder_compare_conj_normalized.py

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


class TestTagSqlEncoderNormalized(unittest.TestCase):
    """Test cases for the TagSqlEncoder class in normalized mode."""

    def setUp(self):
        """Set up encoding functions for tag names and values."""
        self.enc_name = lambda x: x  # No transformation for tag names
        self.enc_value = lambda x: x  # No transformation for tag values

    def test_comparison_conjunction_normalized(self):
        """Test encoding a conjunction of comparison operations into an SQL statement for normalized tables."""
        query = TagQuery.and_(
            [
                TagQuery.eq(TagName("category"), "electronics"),
                TagQuery.gt(TagName("price"), "100"),
            ]
        )

        # Initialize encoder with normalized=True
        # Initialize encoder with normalized=True
        encoder = encoder_factory.get_encoder(
            "sqlite", self.enc_name, self.enc_value, normalized=True
        )
        query_str = encoder.encode_query(query)
        print(f"encoded query_str is :  {query_str}")

        # Expected SQL uses direct column references (SUB QUERY needs t. )
        expected_query = "(t.category = ? AND t.price > ?)"
        expected_args = ["electronics", "100"]

        self.assertEqual(query_str, expected_query)
        self.assertEqual(encoder.arguments, expected_args)

        print("\n### Complete SQL Statements for Testing")

        # Define a normalized table structure
        print(
            "CREATE TABLE connection (id INTEGER PRIMARY KEY, category TEXT, price TEXT);"
        )

        # Insert test data
        print(
            "INSERT INTO connection (id, category, price) VALUES "
            "(1, 'electronics', '150'), "
            "(2, 'electronics', '090'), "
            "(3, 'books', '120'), "
            "(4, 'electronics', '200');"
        )

        # Generate and print the complete SELECT statement
        select_query = f"SELECT * FROM connection WHERE {query_str}"
        complete_select = replace_placeholders(select_query, encoder.arguments)
        print("\n-- Complete SELECT statement with values:")
        print(complete_select)

        print("\n-- Expected result: Items 1 and 4")

        print("\n-- Cleanup")
        print("DELETE FROM connection;")

        """
        ### SQLite Insert Statements for Normalized Table
        CREATE TABLE connection (
            id INTEGER PRIMARY KEY,
            category TEXT,
            price TEXT
        );

        INSERT INTO connection (id, category, price) VALUES
            (1, 'electronics', '150'),
            (2, 'electronics', '090'),
            (3, 'books', '120'),
            (4, 'electronics', '200');

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
