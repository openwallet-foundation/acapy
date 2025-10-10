# pytest --maxfail=1 --disable-warnings --no-cov -s -vv acapy_agent/database_manager/wql_normalized/tests/test_sqlite_TagsqlEncoder_All_key_value.py
# python -m unittest acapy_agent/database_manager/wql_normalized/tests/test_sqlite_TagsqlEncoder_All_key_value.py -v
import logging
import sqlite3
import unittest

from acapy_agent.database_manager.wql_normalized.encoders import encoder_factory
from acapy_agent.database_manager.wql_normalized.query import query_from_str
from acapy_agent.database_manager.wql_normalized.tags import (
    TagName,
    TagQuery,
    query_to_tagquery,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
        escaped_arg = str(arg).replace("'", "''")  # Escape single quotes for SQL
        result += f"'{escaped_arg}'" + part
    return result


class TestSqliteTagEncoderNonNormalized(unittest.TestCase):
    """Test cases for the SqliteTagEncoder class in non-normalized mode."""

    def setUp(self):
        """Set up SQLite in-memory database and encoder."""
        self.enc_name = lambda x: x  # Return tag names as strings
        self.enc_value = lambda x: x  # Return tag values as strings
        try:
            self.conn = sqlite3.connect(":memory:")
            self.cursor = self.conn.cursor()
            # Create tables for key-value pair structure
            self.cursor.execute("""
                CREATE TABLE items (
                    id INTEGER PRIMARY KEY
                )
            """)
            self.cursor.execute("""
                CREATE TABLE items_tags (
                    item_id INTEGER,
                    name TEXT,
                    value TEXT,
                    FOREIGN KEY(item_id) REFERENCES items(id)
                )
            """)
            self.conn.commit()
            logger.info("Tables 'items' and 'items_tags' created in setUp")
            self.encoder = encoder_factory.get_encoder(
                "sqlite", self.enc_name, self.enc_value, normalized=False
            )
        except Exception as e:
            logger.error(f"Failed to set up SQLite database: {e}")
            raise

    def tearDown(self):
        """Clean up by closing the SQLite connection."""
        try:
            self.conn.close()
            logger.info("SQLite connection closed in tearDown")
        except Exception as e:
            logger.error(f"Failed to tear down SQLite connection: {e}")
            raise

    def run_query_and_verify(self, sql_query, params, expected_ids, test_name):
        try:
            self.cursor.execute(f"SELECT i.id FROM items i WHERE {sql_query}", params)
            actual_ids = sorted([row[0] for row in self.cursor.fetchall()])
            self.assertEqual(
                actual_ids,
                expected_ids,
                f"{test_name} failed: Expected IDs {expected_ids}, got {actual_ids}",
            )
        except Exception as e:
            logger.error(f"Query execution failed in {test_name}: {e}")
            raise

    def verify_round_trip(self, query, original_sql_query, original_params):
        """Verify that converting TagQuery to WQL and back results in the same SQLite query."""
        wql_str = query.to_wql_str()
        parsed_query = query_from_str(wql_str)
        parsed_tag_query = query_to_tagquery(parsed_query)
        parsed_sql_query = self.encoder.encode_query(parsed_tag_query)
        parsed_params = self.encoder.arguments
        self.assertEqual(
            (original_sql_query, original_params),
            (parsed_sql_query, parsed_params),
            f"Round-trip SQLite query mismatch in {self._testMethodName}",
        )

    # Individual Operator Tests
    def test_eq_positive(self):
        query = TagQuery.eq(TagName("field"), "value")
        wql = query.to_wql_str()
        print(f"Test: Positive equality query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = (
            "i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value = ?)"
        )
        expected_params = ["field", "value"]
        self.assertEqual(sql_query, expected_query, "Positive equality query mismatch")
        self.assertEqual(params, expected_params, "Positive equality params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany("INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,)])
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [(1, "field", "value"), (2, "field", "other"), (3, "field", "value")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'field', 'value'), "
            "(2, 'field', 'other'), "
            "(3, 'field', 'value');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 3")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1, 3], "Positive equality")

    def test_eq_negated(self):
        query = TagQuery.not_(TagQuery.eq(TagName("field"), "value"))
        wql = query.to_wql_str()
        print(f"Test: Negated equality query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = (
            "i.id NOT IN (SELECT item_id FROM items_tags WHERE name = ? AND value = ?)"
        )
        expected_params = ["field", "value"]
        self.assertEqual(sql_query, expected_query, "Negated equality query mismatch")
        self.assertEqual(params, expected_params, "Negated equality params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany("INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,)])
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [(1, "field", "value"), (2, "field", "other"), (3, "field", "value")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'field', 'value'), "
            "(2, 'field', 'other'), "
            "(3, 'field', 'value');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Item 2")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [2], "Negated equality")

    def test_neq_positive(self):
        query = TagQuery.neq(TagName("field"), "value")
        wql = query.to_wql_str()
        print(f"Test: Positive inequality query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = (
            "i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value != ?)"
        )
        expected_params = ["field", "value"]
        self.assertEqual(sql_query, expected_query, "Positive inequality query mismatch")
        self.assertEqual(params, expected_params, "Positive inequality params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany("INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,)])
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [(1, "field", "value"), (2, "field", "other"), (3, "field", "different")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'field', 'value'), "
            "(2, 'field', 'other'), "
            "(3, 'field', 'different');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 2, 3")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [2, 3], "Positive inequality")

    def test_neq_negated(self):
        query = TagQuery.not_(TagQuery.neq(TagName("field"), "value"))
        wql = query.to_wql_str()
        print(f"Test: Negated inequality query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = (
            "i.id NOT IN (SELECT item_id FROM items_tags WHERE name = ? AND value != ?)"
        )
        expected_params = ["field", "value"]
        self.assertEqual(sql_query, expected_query, "Negated inequality query mismatch")
        self.assertEqual(params, expected_params, "Negated inequality params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany("INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,)])
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [(1, "field", "value"), (2, "field", "other"), (3, "field", "value")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'field', 'value'), "
            "(2, 'field', 'other'), "
            "(3, 'field', 'value');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 3")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1, 3], "Negated inequality")

    def test_gt_positive(self):
        query = TagQuery.gt(TagName("price"), "100")
        wql = query.to_wql_str()
        print(f"Test: Positive greater-than query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = (
            "i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value > ?)"
        )
        expected_params = ["price", "100"]
        self.assertEqual(
            sql_query, expected_query, "Positive greater-than query mismatch"
        )
        self.assertEqual(params, expected_params, "Positive greater-than params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [
                (1, "price", "090"),
                (2, "price", "100"),
                (3, "price", "150"),
                (4, "price", "200"),
            ],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'price', '090'), "
            "(2, 'price', '100'), "
            "(3, 'price', '150'), "
            "(4, 'price', '200');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 3, 4")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [3, 4], "Positive greater-than")

    def test_gt_negated(self):
        query = TagQuery.not_(TagQuery.gt(TagName("price"), "100"))
        wql = query.to_wql_str()
        print(f"Test: Negated greater-than query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = (
            "i.id NOT IN (SELECT item_id FROM items_tags WHERE name = ? AND value > ?)"
        )
        expected_params = ["price", "100"]
        self.assertEqual(sql_query, expected_query, "Negated greater-than query mismatch")
        self.assertEqual(params, expected_params, "Negated greater-than params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [
                (1, "price", "090"),
                (2, "price", "100"),
                (3, "price", "150"),
                (4, "price", "200"),
            ],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'price', '090'), "
            "(2, 'price', '100'), "
            "(3, 'price', '150'), "
            "(4, 'price', '200');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 2")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1, 2], "Negated greater-than")

    def test_gte_positive(self):
        query = TagQuery.gte(TagName("price"), "100")
        wql = query.to_wql_str()
        print(f"Test: Positive greater-than-or-equal query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = (
            "i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value >= ?)"
        )
        expected_params = ["price", "100"]
        self.assertEqual(
            sql_query, expected_query, "Positive greater-than-or-equal query mismatch"
        )
        self.assertEqual(
            params, expected_params, "Positive greater-than-or-equal params mismatch"
        )
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [
                (1, "price", "090"),
                (2, "price", "100"),
                (3, "price", "150"),
                (4, "price", "200"),
            ],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'price', '090'), "
            "(2, 'price', '100'), "
            "(3, 'price', '150'), "
            "(4, 'price', '200');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 2, 3, 4")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(
            sql_query, params, [2, 3, 4], "Positive greater-than-or-equal"
        )

    def test_gte_negated(self):
        query = TagQuery.not_(TagQuery.gte(TagName("price"), "100"))
        wql = query.to_wql_str()
        print(f"Test: Negated greater-than-or-equal query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = (
            "i.id NOT IN (SELECT item_id FROM items_tags WHERE name = ? AND value >= ?)"
        )
        expected_params = ["price", "100"]
        self.assertEqual(
            sql_query, expected_query, "Negated greater-than-or-equal query mismatch"
        )
        self.assertEqual(
            params, expected_params, "Negated greater-than-or-equal params mismatch"
        )
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [
                (1, "price", "090"),
                (2, "price", "100"),
                (3, "price", "150"),
                (4, "price", "200"),
            ],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'price', '090'), "
            "(2, 'price', '100'), "
            "(3, 'price', '150'), "
            "(4, 'price', '200');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Item 1")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1], "Negated greater-than-or-equal")

    def test_lt_positive(self):
        query = TagQuery.lt(TagName("price"), "100")
        wql = query.to_wql_str()
        print(f"Test: Positive less-than query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = (
            "i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value < ?)"
        )
        expected_params = ["price", "100"]
        self.assertEqual(sql_query, expected_query, "Positive less-than query mismatch")
        self.assertEqual(params, expected_params, "Positive less-than params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [
                (1, "price", "090"),
                (2, "price", "100"),
                (3, "price", "150"),
                (4, "price", "200"),
            ],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'price', '090'), "
            "(2, 'price', '100'), "
            "(3, 'price', '150'), "
            "(4, 'price', '200');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Item 1")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1], "Positive less-than")

    def test_lt_negated(self):
        query = TagQuery.not_(TagQuery.lt(TagName("price"), "100"))
        wql = query.to_wql_str()
        print(f"Test: Negated less-than query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = (
            "i.id NOT IN (SELECT item_id FROM items_tags WHERE name = ? AND value < ?)"
        )
        expected_params = ["price", "100"]
        self.assertEqual(sql_query, expected_query, "Negated less-than query mismatch")
        self.assertEqual(params, expected_params, "Negated less-than params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [
                (1, "price", "090"),
                (2, "price", "100"),
                (3, "price", "150"),
                (4, "price", "200"),
            ],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'price', '090'), "
            "(2, 'price', '100'), "
            "(3, 'price', '150'), "
            "(4, 'price', '200');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 2, 3, 4")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [2, 3, 4], "Negated less-than")

    def test_lte_positive(self):
        query = TagQuery.lte(TagName("price"), "100")
        wql = query.to_wql_str()
        print(f"Test: Positive less-than-or-equal query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = (
            "i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value <= ?)"
        )
        expected_params = ["price", "100"]
        self.assertEqual(
            sql_query, expected_query, "Positive less-than-or-equal query mismatch"
        )
        self.assertEqual(
            params, expected_params, "Positive less-than-or-equal params mismatch"
        )
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [
                (1, "price", "090"),
                (2, "price", "100"),
                (3, "price", "150"),
                (4, "price", "200"),
            ],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'price', '090'), "
            "(2, 'price', '100'), "
            "(3, 'price', '150'), "
            "(4, 'price', '200');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 2")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(
            sql_query, params, [1, 2], "Positive less-than-or-equal"
        )

    def test_lte_negated(self):
        query = TagQuery.not_(TagQuery.lte(TagName("price"), "100"))
        wql = query.to_wql_str()
        print(f"Test: Negated less-than-or-equal query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = (
            "i.id NOT IN (SELECT item_id FROM items_tags WHERE name = ? AND value <= ?)"
        )
        expected_params = ["price", "100"]
        self.assertEqual(
            sql_query, expected_query, "Negated less-than-or-equal query mismatch"
        )
        self.assertEqual(
            params, expected_params, "Negated less-than-or-equal params mismatch"
        )
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [
                (1, "price", "090"),
                (2, "price", "100"),
                (3, "price", "150"),
                (4, "price", "200"),
            ],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'price', '090'), "
            "(2, 'price', '100'), "
            "(3, 'price', '150'), "
            "(4, 'price', '200');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 3, 4")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [3, 4], "Negated less-than-or-equal")

    def test_like_positive(self):
        query = TagQuery.like(TagName("field"), "%pat%")
        wql = query.to_wql_str()
        print(f"Test: Positive LIKE query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = (
            "i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value LIKE ?)"
        )
        expected_params = ["field", "%pat%"]
        self.assertEqual(sql_query, expected_query, "Positive LIKE query mismatch")
        self.assertEqual(params, expected_params, "Positive LIKE params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [
                (1, "field", "pattern"),
                (2, "field", "path"),
                (3, "field", "other"),
                (4, "field", "pat"),
            ],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'field', 'pattern'), "
            "(2, 'field', 'path'), "
            "(3, 'field', 'other'), "
            "(4, 'field', 'pat');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 2, 4")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1, 2, 4], "Positive LIKE")

    def test_like_negated(self):
        query = TagQuery.not_(TagQuery.like(TagName("field"), "%pat%"))
        wql = query.to_wql_str()
        print(f"Test: Negated LIKE query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = (
            "i.id NOT IN (SELECT item_id FROM items_tags WHERE name = ? AND value LIKE ?)"
        )
        expected_params = ["field", "%pat%"]
        self.assertEqual(sql_query, expected_query, "Negated LIKE query mismatch")
        self.assertEqual(params, expected_params, "Negated LIKE params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [
                (1, "field", "pattern"),
                (2, "field", "path"),
                (3, "field", "other"),
                (4, "field", "pat"),
            ],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'field', 'pattern'), "
            "(2, 'field', 'path'), "
            "(3, 'field', 'other'), "
            "(4, 'field', 'pat');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Item 3")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [3], "Negated LIKE")

    def test_in_positive(self):
        query = TagQuery.in_(TagName("field"), ["a", "b"])
        wql = query.to_wql_str()
        print(f"Test: Positive IN query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = (
            "i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value IN (?, ?))"
        )
        expected_params = ["field", "a", "b"]
        self.assertEqual(sql_query, expected_query, "Positive IN query mismatch")
        self.assertEqual(params, expected_params, "Positive IN params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [(1, "field", "a"), (2, "field", "b"), (3, "field", "c"), (4, "field", "a")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'field', 'a'), "
            "(2, 'field', 'b'), "
            "(3, 'field', 'c'), "
            "(4, 'field', 'a');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 2, 4")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1, 2, 4], "Positive IN")

    def test_in_negated(self):
        query = TagQuery.not_(TagQuery.in_(TagName("field"), ["a", "b"]))
        wql = query.to_wql_str()
        print(f"Test: Negated IN query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value NOT IN (?, ?))"
        expected_params = ["field", "a", "b"]
        self.assertEqual(sql_query, expected_query, "Negated IN query mismatch")
        self.assertEqual(params, expected_params, "Negated IN params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [(1, "field", "a"), (2, "field", "b"), (3, "field", "c"), (4, "field", "d")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'field', 'a'), "
            "(2, 'field', 'b'), "
            "(3, 'field', 'c'), "
            "(4, 'field', 'd');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 3, 4")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [3, 4], "Negated IN")

    def test_exist_positive(self):
        query = TagQuery.exist([TagName("field")])
        wql = query.to_wql_str()
        print(f"Test: Positive EXIST query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "i.id IN (SELECT item_id FROM items_tags WHERE name = ?)"
        expected_params = ["field"]
        self.assertEqual(sql_query, expected_query, "Positive EXIST query mismatch")
        self.assertEqual(params, expected_params, "Positive EXIST params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany("INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,)])
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [(1, "field", "value"), (3, "field", "another")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'field', 'value'), "
            "(3, 'field', 'another');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 3")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1, 3], "Positive EXIST")

    def test_exist_negated(self):
        query = TagQuery.not_(TagQuery.exist([TagName("field")]))
        wql = query.to_wql_str()
        print(f"Test: Negated EXIST query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "i.id NOT IN (SELECT item_id FROM items_tags WHERE name = ?)"
        expected_params = ["field"]
        self.assertEqual(sql_query, expected_query, "Negated EXIST query mismatch")
        self.assertEqual(params, expected_params, "Negated EXIST params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany("INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,)])
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [(1, "field", "value"), (3, "field", "another")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'field', 'value'), "
            "(3, 'field', 'another');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Item 2")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [2], "Negated EXIST")

    def test_and_multiple(self):
        query = TagQuery.and_(
            [TagQuery.eq(TagName("f1"), "v1"), TagQuery.gt(TagName("f2"), "10")]
        )
        wql = query.to_wql_str()
        print(f"Test: AND query with multiple subqueries\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "(i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value = ?) AND i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value > ?))"
        expected_params = ["f1", "v1", "f2", "10"]
        self.assertEqual(sql_query, expected_query, "AND multiple query mismatch")
        self.assertEqual(params, expected_params, "AND multiple params mismatch")
        self.verify_round_trip(query, sql_query, params)

        # Insert items into the items table
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,), (4,)]
        )

        # Insert tags into the items_tags table
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [
                (1, "f1", "v1"),  # Item 1: satisfies "f1" = "v1"
                (1, "f2", "15"),  # Item 1: satisfies "f2" > "10"
                (2, "f1", "05"),  # Item 2: does not satisfy "f1" = "v1"
                (3, "f2", "15"),  # Item 3: does not have "f1" = "v1"
                (4, "f1", "v1"),  # Item 4: satisfies "f1" = "v1"
                (4, "f2", "20"),  # Item 4: satisfies "f2" > "10"
            ],
        )
        self.conn.commit()

        # Print statements for debugging
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'f1', 'v1'), (1, 'f2', '15'), (2, 'f1', '05'), (3, 'f2', '15'), "
            "(4, 'f1', 'v1'), (4, 'f2', '20');"
        )
        select_query = f"SELECT i.id FROM items i WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 4")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")

        # Run the query and verify results
        self.run_query_and_verify(sql_query, params, [1, 4], "AND multiple")

    def test_or_multiple(self):
        query = TagQuery.or_(
            [TagQuery.eq(TagName("f1"), "v1"), TagQuery.gt(TagName("f2"), "10")]
        )
        wql = query.to_wql_str()
        print(f"Test: OR query with multiple subqueries\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "(i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value = ?) OR i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value > ?))"
        expected_params = ["f1", "v1", "f2", "10"]
        self.assertEqual(sql_query, expected_query, "OR multiple query mismatch")
        self.assertEqual(params, expected_params, "OR multiple params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [
                (1, "f1", "v1"),
                (1, "f2", "15"),
                (2, "f1", "v1"),
                (2, "f2", "05"),
                (3, "f1", "v2"),
                (3, "f2", "15"),
                (4, "f1", "v2"),
                (4, "f2", "05"),
            ],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'f1', 'v1'), (1, 'f2', '15'), "
            "(2, 'f1', 'v1'), (2, 'f2', '05'), "
            "(3, 'f1', 'v2'), (3, 'f2', '15'), "
            "(4, 'f1', 'v2'), (4, 'f2', '05');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 2, 3")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1, 2, 3], "OR multiple")

    def test_nested_and_or(self):
        query = TagQuery.and_(
            [
                TagQuery.eq(TagName("f1"), "v1"),
                TagQuery.or_(
                    [TagQuery.gt(TagName("f2"), "10"), TagQuery.lt(TagName("f3"), "5")]
                ),
            ]
        )
        wql = query.to_wql_str()
        print(f"Test: Nested AND/OR query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "(i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value = ?) AND (i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value > ?) OR i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value < ?)))"
        expected_params = ["f1", "v1", "f2", "10", "f3", "5"]
        self.assertEqual(sql_query, expected_query, "Nested AND/OR query mismatch")
        self.assertEqual(params, expected_params, "Nested AND/OR params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [
                (1, "f1", "v1"),
                (1, "f2", "15"),
                (1, "f3", "3"),
                (2, "f1", "v1"),
                (2, "f2", "05"),
                (2, "f3", "4"),
                (3, "f1", "v2"),
                (3, "f2", "15"),
                (3, "f3", "3"),
                (4, "f1", "v1"),
                (4, "f2", "05"),
                (4, "f3", "6"),
            ],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'f1', 'v1'), (1, 'f2', '15'), (1, 'f3', '3'), "
            "(2, 'f1', 'v1'), (2, 'f2', '05'), (2, 'f3', '4'), "
            "(3, 'f1', 'v2'), (3, 'f2', '15'), (3, 'f3', '3'), "
            "(4, 'f1', 'v1'), (4, 'f2', '05'), (4, 'f3', '6');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 2")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1, 2], "Nested AND/OR")

    def test_comparison_conjunction(self):
        query = TagQuery.and_(
            [
                TagQuery.eq(TagName("category"), "electronics"),
                TagQuery.gt(TagName("price"), "100"),
            ]
        )
        wql = query.to_wql_str()
        print(f"Test: Comparison conjunction query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "(i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value = ?) AND i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value > ?))"
        expected_params = ["category", "electronics", "price", "100"]
        self.assertEqual(
            sql_query, expected_query, "Comparison conjunction query mismatch"
        )
        self.assertEqual(
            params, expected_params, "Comparison conjunction params mismatch"
        )
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [
                (1, "category", "electronics"),
                (1, "price", "150"),
                (2, "category", "electronics"),
                (2, "price", "090"),
                (3, "category", "books"),
                (3, "price", "120"),
                (4, "category", "electronics"),
                (4, "price", "200"),
            ],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'category', 'electronics'), (1, 'price', '150'), "
            "(2, 'category', 'electronics'), (2, 'price', '090'), "
            "(3, 'category', 'books'), (3, 'price', '120'), "
            "(4, 'category', 'electronics'), (4, 'price', '200');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 4")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1, 4], "Comparison conjunction")

    def test_deeply_nested_not(self):
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
        wql = query.to_wql_str()
        print(f"Test: Deeply nested NOT query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "NOT ((i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value = ?) OR i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value = ?)) AND i.id NOT IN (SELECT item_id FROM items_tags WHERE name = ? AND value = ?))"
        expected_params = ["category", "electronics", "sale", "yes", "stock", "out"]
        self.assertEqual(sql_query, expected_query, "Deeply nested NOT query mismatch")
        self.assertEqual(params, expected_params, "Deeply nested NOT params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [
                (1, "category", "electronics"),
                (1, "stock", "in"),
                (2, "category", "electronics"),
                (2, "stock", "out"),
                (3, "sale", "yes"),
                (3, "stock", "in"),
                (4, "sale", "yes"),
            ],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'category', 'electronics'), (1, 'stock', 'in'), "
            "(2, 'category', 'electronics'), (2, 'stock', 'out'), "
            "(3, 'sale', 'yes'), (3, 'stock', 'in'), "
            "(4, 'sale', 'yes');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Item 2")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [2], "Deeply nested NOT")

    def test_and_or_not_complex_case(self):
        query = TagQuery.not_(
            TagQuery.and_(
                [
                    TagQuery.eq(TagName("username"), "alice"),
                    TagQuery.or_(
                        [
                            TagQuery.gt(TagName("age"), "30"),
                            TagQuery.not_(TagQuery.lte(TagName("height"), "180")),
                            TagQuery.and_(
                                [
                                    TagQuery.lt(TagName("score"), "100"),
                                    TagQuery.not_(
                                        TagQuery.gte(
                                            TagName("timestamp"), "2021-01-01T00:00:00"
                                        )
                                    ),
                                ]
                            ),
                        ]
                    ),
                    TagQuery.not_(TagQuery.like(TagName("secret_code"), "abc123")),
                    TagQuery.and_(
                        [
                            TagQuery.eq(TagName("occupation"), "developer"),
                            TagQuery.not_(TagQuery.neq(TagName("status"), "active")),
                        ]
                    ),
                ]
            )
        )
        wql = query.to_wql_str()
        print(f"Test: Complex AND/OR/NOT query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "NOT (i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value = ?) AND (i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value > ?) OR i.id NOT IN (SELECT item_id FROM items_tags WHERE name = ? AND value <= ?) OR (i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value < ?) AND i.id NOT IN (SELECT item_id FROM items_tags WHERE name = ? AND value >= ?))) AND i.id NOT IN (SELECT item_id FROM items_tags WHERE name = ? AND value LIKE ?) AND (i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value = ?) AND i.id NOT IN (SELECT item_id FROM items_tags WHERE name = ? AND value != ?)))"
        expected_params = [
            "username",
            "alice",
            "age",
            "30",
            "height",
            "180",
            "score",
            "100",
            "timestamp",
            "2021-01-01T00:00:00",
            "secret_code",
            "abc123",
            "occupation",
            "developer",
            "status",
            "active",
        ]
        self.assertEqual(sql_query, expected_query, "Complex AND/OR/NOT query mismatch")
        self.assertEqual(params, expected_params, "Complex AND/OR/NOT params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (?)",
            [(1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,), (10,), (11,), (12,)],
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [
                (1, "username", "bob"),
                (1, "age", "25"),
                (1, "height", "170"),
                (1, "score", "150"),
                (1, "timestamp", "2021-02-01T00:00:00"),
                (1, "secret_code", "xyz789"),
                (1, "occupation", "engineer"),
                (1, "status", "inactive"),
                (2, "username", "alice"),
                (2, "age", "35"),
                (2, "height", "190"),
                (2, "score", "90"),
                (2, "timestamp", "2020-12-01T00:00:00"),
                (2, "secret_code", "def456"),
                (2, "occupation", "developer"),
                (2, "status", "active"),
                (3, "username", "charlie"),
                (3, "age", "28"),
                (3, "height", "175"),
                (3, "score", "120"),
                (3, "timestamp", "2021-03-01T00:00:00"),
                (3, "secret_code", "ghi789"),
                (3, "occupation", "manager"),
                (3, "status", "active"),
                (4, "username", "alice"),
                (4, "age", "32"),
                (4, "height", "185"),
                (4, "score", "95"),
                (4, "timestamp", "2020-11-01T00:00:00"),
                (4, "secret_code", "abc123"),
                (4, "occupation", "developer"),
                (4, "status", "inactive"),
                (5, "username", "eve"),
                (5, "age", "40"),
                (5, "height", "160"),
                (5, "score", "85"),
                (5, "timestamp", "2021-01-15T00:00:00"),
                (5, "secret_code", "abc123"),
                (5, "occupation", "analyst"),
                (5, "status", "active"),
                (6, "username", "frank"),
                (6, "age", "29"),
                (6, "height", "182"),
                (6, "score", "105"),
                (6, "timestamp", "2020-12-15T00:00:00"),
                (6, "secret_code", "jkl012"),
                (6, "occupation", "developer"),
                (6, "status", "active"),
                (7, "username", "alice"),
                (7, "age", "33"),
                (7, "height", "195"),
                (7, "score", "88"),
                (7, "timestamp", "2020-10-01T00:00:00"),
                (7, "secret_code", "mno345"),
                (7, "occupation", "developer"),
                (7, "status", "active"),
                (8, "username", "hank"),
                (8, "age", "27"),
                (8, "height", "165"),
                (8, "score", "110"),
                (8, "timestamp", "2021-04-01T00:00:00"),
                (8, "secret_code", "pqr678"),
                (8, "occupation", "designer"),
                (8, "status", "inactive"),
                (9, "username", "alice"),
                (9, "age", "36"),
                (9, "height", "188"),
                (9, "score", "92"),
                (9, "timestamp", "2020-09-01T00:00:00"),
                (9, "secret_code", "stu901"),
                (9, "occupation", "developer"),
                (9, "status", "active"),
                (10, "username", "jack"),
                (10, "age", "31"),
                (10, "height", "179"),
                (10, "score", "115"),
                (10, "timestamp", "2021-05-01T00:00:00"),
                (10, "secret_code", "vwx234"),
                (10, "occupation", "teacher"),
                (10, "status", "active"),
                (11, "username", "kara"),
                (11, "age", "26"),
                (11, "height", "170"),
                (11, "score", "130"),
                (11, "timestamp", "2021-06-01T00:00:00"),
                (11, "secret_code", "yza567"),
                (11, "occupation", "developer"),
                (11, "status", "inactive"),
                (12, "username", "alice"),
                (12, "age", "34"),
                (12, "height", "192"),
                (12, "score", "87"),
                (12, "timestamp", "2020-08-01T00:00:00"),
                (12, "secret_code", "bcd890"),
                (12, "occupation", "developer"),
                (12, "status", "active"),
            ],
        )
        self.conn.commit()
        expected_ids = [1, 3, 4, 5, 6, 8, 10, 11]
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print(
            "INSERT INTO items (id) VALUES (1), (2), (3), (4), (5), (6), (7), (8), (9), (10), (11), (12);"
        )
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'username', 'bob'), (1, 'age', '25'), (1, 'height', '170'), (1, 'score', '150'), (1, 'timestamp', '2021-02-01T00:00:00'), (1, 'secret_code', 'xyz789'), (1, 'occupation', 'engineer'), (1, 'status', 'inactive'), "
            "(2, 'username', 'alice'), (2, 'age', '35'), (2, 'height', '190'), (2, 'score', '90'), (2, 'timestamp', '2020-12-01T00:00:00'), (2, 'secret_code', 'def456'), (2, 'occupation', 'developer'), (2, 'status', 'active'), "
            "(3, 'username', 'charlie'), (3, 'age', '28'), (3, 'height', '175'), (3, 'score', '120'), (3, 'timestamp', '2021-03-01T00:00:00'), (3, 'secret_code', 'ghi789'), (3, 'occupation', 'manager'), (3, 'status', 'active'), "
            "(4, 'username', 'alice'), (4, 'age', '32'), (4, 'height', '185'), (4, 'score', '95'), (4, 'timestamp', '2020-11-01T00:00:00'), (4, 'secret_code', 'abc123'), (4, 'occupation', 'developer'), (4, 'status', 'inactive'), "
            "(5, 'username', 'eve'), (5, 'age', '40'), (5, 'height', '160'), (5, 'score', '85'), (5, 'timestamp', '2021-01-15T00:00:00'), (5, 'secret_code', 'abc123'), (5, 'occupation', 'analyst'), (5, 'status', 'active'), "
            "(6, 'username', 'frank'), (6, 'age', '29'), (6, 'height', '182'), (6, 'score', '105'), (6, 'timestamp', '2020-12-15T00:00:00'), (6, 'secret_code', 'jkl012'), (6, 'occupation', 'developer'), (6, 'status', 'active'), "
            "(7, 'username', 'alice'), (7, 'age', '33'), (7, 'height', '195'), (7, 'score', '88'), (7, 'timestamp', '2020-10-01T00:00:00'), (7, 'secret_code', 'mno345'), (7, 'occupation', 'developer'), (7, 'status', 'active'), "
            "(8, 'username', 'hank'), (8, 'age', '27'), (8, 'height', '165'), (8, 'score', '110'), (8, 'timestamp', '2021-04-01T00:00:00'), (8, 'secret_code', 'pqr678'), (8, 'occupation', 'designer'), (8, 'status', 'inactive'), "
            "(9, 'username', 'alice'), (9, 'age', '36'), (9, 'height', '188'), (9, 'score', '92'), (9, 'timestamp', '2020-09-01T00:00:00'), (9, 'secret_code', 'stu901'), (9, 'occupation', 'developer'), (9, 'status', 'active'), "
            "(10, 'username', 'jack'), (10, 'age', '31'), (10, 'height', '179'), (10, 'score', '115'), (10, 'timestamp', '2021-05-01T00:00:00'), (10, 'secret_code', 'vwx234'), (10, 'occupation', 'teacher'), (10, 'status', 'active'), "
            "(11, 'username', 'kara'), (11, 'age', '26'), (11, 'height', '170'), (11, 'score', '130'), (11, 'timestamp', '2021-06-01T00:00:00'), (11, 'secret_code', 'yza567'), (11, 'occupation', 'developer'), (11, 'status', 'inactive'), "
            "(12, 'username', 'alice'), (12, 'age', '34'), (12, 'height', '192'), (12, 'score', '87'), (12, 'timestamp', '2020-08-01T00:00:00'), (12, 'secret_code', 'bcd890'), (12, 'occupation', 'developer'), (12, 'status', 'active');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print(f"\n-- Expected result: Items {expected_ids}")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(
            sql_query, params, expected_ids, "Complex AND/OR/NOT query"
        )

    def test_empty_query(self):
        query = TagQuery.and_([])
        wql = query.to_wql_str()
        print(f"Test: Empty query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "1=1"
        expected_params = []
        self.assertEqual(sql_query, expected_query, "Empty query mismatch")
        self.assertEqual(params, expected_params, "Empty query params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany("INSERT INTO items (id) VALUES (?)", [(1,), (2,)])
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [(1, "field", "value"), (2, "field", "data")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'field', 'value'), "
            "(2, 'field', 'data');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 2")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1, 2], "Empty query")

    def test_empty_in_list(self):
        query = TagQuery.in_(TagName("field"), [])
        wql = query.to_wql_str()
        print(f"Test: Empty IN list query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = (
            "i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value IN ())"
        )
        expected_params = ["field"]
        self.assertEqual(sql_query, expected_query, "Empty IN list query mismatch")
        self.assertEqual(params, expected_params, "Empty IN list params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany("INSERT INTO items (id) VALUES (?)", [(1,), (2,)])
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [(1, "field", "value"), (2, "field", "other")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'field', 'value'), "
            "(2, 'field', 'other');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: No items")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [], "Empty IN list")

    def test_multiple_exists(self):
        query = TagQuery.exist([TagName("f1"), TagName("f2")])
        wql = query.to_wql_str()
        print(f"Test: Multiple EXISTS query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "(i.id IN (SELECT item_id FROM items_tags WHERE name = ?) AND i.id IN (SELECT item_id FROM items_tags WHERE name = ?))"
        expected_params = ["f1", "f2"]
        self.assertEqual(sql_query, expected_query, "Multiple EXISTS query mismatch")
        self.assertEqual(params, expected_params, "Multiple EXISTS params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [(1, "f1", "v1"), (1, "f2", "v2"), (2, "f1", "v1"), (3, "f2", "v2")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'f1', 'v1'), (1, 'f2', 'v2'), "
            "(2, 'f1', 'v1'), "
            "(3, 'f2', 'v2');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Item 1")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1], "Multiple EXISTS")

    def test_special_characters(self):
        query = TagQuery.eq(TagName("f1"), "val$ue")
        wql = query.to_wql_str()
        print(f"Test: Special characters query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = (
            "i.id IN (SELECT item_id FROM items_tags WHERE name = ? AND value = ?)"
        )
        expected_params = ["f1", "val$ue"]
        self.assertEqual(sql_query, expected_query, "Special characters query mismatch")
        self.assertEqual(params, expected_params, "Special characters params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany("INSERT INTO items (id) VALUES (?)", [(1,), (2,), (3,)])
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (?, ?, ?)",
            [(1, "f1", "val$ue"), (2, "f1", "other"), (3, "f1", "val$ue")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY);")
        print("CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT);")
        print("INSERT INTO items (id) VALUES (1), (2), (3);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'f1', 'val$ue'), "
            "(2, 'f1', 'other'), "
            "(3, 'f1', 'val$ue');"
        )
        select_query = f"SELECT id FROM items WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 3")
        print("\n-- Cleanup\nDELETE FROM items_tags; DELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1, 3], "Special characters")


def main():
    print("Running SqliteTagEncoder non-normalized tests...")
    unittest.main(argv=[""], exit=False)
    print("All tests completed.")


if __name__ == "__main__":
    main()
