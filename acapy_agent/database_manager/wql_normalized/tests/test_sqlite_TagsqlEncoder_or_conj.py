# pytest --maxfail=1 --disable-warnings --no-cov -s -vv acapy_agent/database_manager/wql_normalized/tests/test_sqlite_TagsqlEncoder_or_conj.py
# python -m unittest acapy_agent/database_manager/wql_normalized/tests/test_sqlite_TagsqlEncoder_or_conj.py

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
        """Set up encoding functions for tag names and values."""
        self.enc_name = lambda x: x  # No transformation for tag names
        self.enc_value = lambda x: x  # No transformation for tag values

    def test_or_conjunction(self):
        """Test encoding an OR conjunction TagQuery into an SQL statement."""
        # Define the query structure with neutral tag names
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

        encoder = encoder_factory.get_encoder("sqlite", self.enc_name, self.enc_value)

        query_str = encoder.encode_query(query)
        print(f"encoded query_str is :  {query_str}")

        # Expected SQL query for OR conjunction
        expected_query = (
            "((i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value = ?) "
            "AND i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value = ?)) "
            "OR (i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value = ?) "
            "AND i.id NOT IN (SELECT item_id FROM items_tags WHERE name = ? "
            "AND value = ?)))"
        )

        # Expected arguments based on the query without uppercase transformation
        expected_args = [
            "tag_a",
            "value_a",  # condition_1: tag_a = value_a
            "tag_b",
            "value_b",  # condition_1: tag_b = value_b
            "tag_a",
            "value_a",  # condition_2: tag_a = value_a
            "tag_b",
            "value_c",  # condition_2: NOT (tag_b = value_c)
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

        # Insert tags with original tag names and values
        print("INSERT INTO items_tags (item_id, name, value) VALUES")
        print("    (1, 'tag_a', 'value_a'),  -- Item 1: tag_a=value_a, tag_b=value_b")
        print("    (1, 'tag_b', 'value_b'),")
        print("    (2, 'tag_a', 'value_a'),  -- Item 2: tag_a=value_a, tag_b=value_c")
        print("    (2, 'tag_b', 'value_c'),")
        print("    (3, 'tag_a', 'value_d'),  -- Item 3: tag_a=value_d, tag_b=value_b")
        print("    (3, 'tag_b', 'value_b'),")
        print("    (4, 'tag_a', 'value_a');  -- Item 4: tag_a=value_a, no tag_b")

        # Complete SELECT statement with values inserted
        select_query = f"SELECT * FROM items i WHERE {query_str}"
        complete_select = replace_placeholders(select_query, encoder.arguments)
        print("\n-- Complete SELECT statement with values:")
        print(complete_select)

        # Add expected result for reference
        print("\n-- Expected result: Items 1 and 4")

        # Cleanup: Delete all inserted rows
        print("\n-- Cleanup")
        print("DELETE FROM items_tags;")
        print("DELETE FROM items;")

        """
        ### SQLite Insert Statements
        -- Create tables
        CREATE TABLE items (id INTEGER PRIMARY KEY);
        CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);

        -- Insert items
        INSERT INTO items (id) VALUES (1), (2), (3), (4);

        -- Insert tags with original tag names and values
        INSERT INTO items_tags (item_id, name, value) VALUES
            (1, 'tag_a', 'value_a'),  -- Item 1: tag_a=value_a, tag_b=value_b
            (1, 'tag_b', 'value_b'),
            (2, 'tag_a', 'value_a'),  -- Item 2: tag_a=value_a, tag_b=value_c
            (2, 'tag_b', 'value_c'),
            (3, 'tag_a', 'value_d'),  -- Item 3: tag_a=value_d, tag_b=value_b
            (3, 'tag_b', 'value_b'),
            (4, 'tag_a', 'value_a');  -- Item 4: tag_a=value_a, no tag_b

        ### Expected Result
        -- Running the query: SELECT * FROM items i WHERE {query_str}
        -- with parameters: {encoder.arguments}
        -- Logic:
        -- Query is: (tag_a = value_a AND tag_b = value_b) OR
        --           (tag_a = value_a AND NOT (tag_b = value_c))
        -- Item 1:
        --   (tag_a = value_a AND tag_b = value_b) -> true OR (true AND NOT false) -> true
        -- Item 2:
        --   (tag_a = value_a AND tag_b = value_b) -> false
        --   (tag_a = value_a AND NOT (tag_b = value_c)) -> true AND NOT true -> false
        --   false OR false -> false
        -- Item 3:
        --   (tag_a = value_a) -> false -> false OR false -> false
        -- Item 4:
        --   (tag_a = value_a AND tag_b = value_b) -> false (no tag_b)
        --   (tag_a = value_a AND NOT (tag_b = value_c)) -> true AND true
        --   (no tag_b = value_c) -> true
        --   false OR true -> true
        -- Expected items selected: 1 and 4
        """


if __name__ == "__main__":
    unittest.main()
