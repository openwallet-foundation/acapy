# pytest --maxfail=1 --disable-warnings --no-cov -s -vv acapy_agent/database_manager/wql_normalized/tests/test_sqlite_TagsqlEncoder_All_normalized.py
# python -m unittest acapy_agent/database_manager/wql_normalized/tests/test_sqlite_TagsqlEncoder_All_normalized.py -v

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


class TestSqliteTagEncoderNormalized(unittest.TestCase):
    """Test cases for the SqliteTagEncoder class in normalized mode."""

    def setUp(self):
        """Set up SQLite in-memory database and encoder.

        Note: normalized=True causes column names to be prefixed with 't.' in SQL queries.
        """
        self.enc_name = lambda x: x  # No transformation for tag names
        self.enc_value = lambda x: x  # No transformation for tag values
        try:
            self.conn = sqlite3.connect(":memory:")
            self.cursor = self.conn.cursor()
            # Create a normalized table with columns for all test fields
            self.cursor.execute("""
                CREATE TABLE items (
                    id INTEGER PRIMARY KEY,
                    field TEXT,
                    price TEXT,
                    category TEXT,
                    sale TEXT,
                    stock TEXT,
                    f1 TEXT,
                    f2 TEXT,
                    f3 TEXT,
                    username TEXT,
                    age TEXT,
                    height TEXT,
                    score TEXT,
                    timestamp TEXT,
                    secret_code TEXT,
                    occupation TEXT,
                    status TEXT
                )
            """)
            self.conn.commit()
            logger.info("Table 'items' created in setUp")
            self.encoder = encoder_factory.get_encoder(
                "sqlite", self.enc_name, self.enc_value, normalized=True
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
        """Run an SQLite query and verify the results against expected IDs."""
        try:
            self.cursor.execute(f"SELECT id FROM items AS t WHERE {sql_query}", params)
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
        expected_query = "t.field = ?"
        expected_params = ["value"]
        self.assertEqual(sql_query, expected_query, "Positive equality query mismatch")
        self.assertEqual(params, expected_params, "Positive equality params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, field) VALUES (?, ?)",
            [(1, "value"), (2, "other"), (3, "value")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, field TEXT);")
        print(
            "INSERT INTO items (id, field) VALUES "
            "(1, 'value'), "
            "(2, 'other'), "
            "(3, 'value');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 3")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1, 3], "Positive equality")

    def test_eq_negated(self):
        query = TagQuery.not_(TagQuery.eq(TagName("field"), "value"))
        wql = query.to_wql_str()
        print(f"Test: Negated equality query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "NOT (t.field = ?)"
        expected_params = ["value"]
        self.assertEqual(sql_query, expected_query, "Negated equality query mismatch")
        self.assertEqual(params, expected_params, "Negated equality params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, field) VALUES (?, ?)",
            [(1, "value"), (2, "other"), (3, "value")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, field TEXT);")
        print(
            "INSERT INTO items (id, field) VALUES "
            "(1, 'value'), "
            "(2, 'other'), "
            "(3, 'value');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Item 2")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [2], "Negated equality")

    def test_neq_positive(self):
        query = TagQuery.neq(TagName("field"), "value")
        wql = query.to_wql_str()
        print(f"Test: Positive inequality query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "t.field != ?"
        expected_params = ["value"]
        self.assertEqual(sql_query, expected_query, "Positive inequality query mismatch")
        self.assertEqual(params, expected_params, "Positive inequality params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, field) VALUES (?, ?)",
            [(1, "value"), (2, "other"), (3, "different")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, field TEXT);")
        print(
            "INSERT INTO items (id, field) VALUES "
            "(1, 'value'), "
            "(2, 'other'), "
            "(3, 'different');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 2, 3")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [2, 3], "Positive inequality")

    def test_neq_negated(self):
        query = TagQuery.not_(TagQuery.neq(TagName("field"), "value"))
        wql = query.to_wql_str()
        print(f"Test: Negated inequality query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "NOT (t.field != ?)"
        expected_params = ["value"]
        self.assertEqual(sql_query, expected_query, "Negated inequality query mismatch")
        self.assertEqual(params, expected_params, "Negated inequality params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, field) VALUES (?, ?)",
            [(1, "value"), (2, "other"), (3, "value")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, field TEXT);")
        print(
            "INSERT INTO items (id, field) VALUES "
            "(1, 'value'), "
            "(2, 'other'), "
            "(3, 'value');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 3")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1, 3], "Negated inequality")

    def test_gt_positive(self):
        query = TagQuery.gt(TagName("price"), "100")
        wql = query.to_wql_str()
        print(f"Test: Positive greater-than query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "t.price > ?"
        expected_params = ["100"]
        self.assertEqual(
            sql_query, expected_query, "Positive greater-than query mismatch"
        )
        self.assertEqual(params, expected_params, "Positive greater-than params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, price) VALUES (?, ?)",
            [(1, "090"), (2, "100"), (3, "150"), (4, "200")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, price TEXT);")
        print(
            "INSERT INTO items (id, price) VALUES "
            "(1, '090'), "
            "(2, '100'), "
            "(3, '150'), "
            "(4, '200');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 3, 4")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [3, 4], "Positive greater-than")

    def test_gt_negated(self):
        query = TagQuery.not_(TagQuery.gt(TagName("price"), "100"))
        wql = query.to_wql_str()
        print(f"Test: Negated greater-than query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "NOT (t.price > ?)"
        expected_params = ["100"]
        self.assertEqual(sql_query, expected_query, "Negated greater-than query mismatch")
        self.assertEqual(params, expected_params, "Negated greater-than params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, price) VALUES (?, ?)",
            [(1, "090"), (2, "100"), (3, "150"), (4, "200")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, price TEXT);")
        print(
            "INSERT INTO items (id, price) VALUES "
            "(1, '090'), "
            "(2, '100'), "
            "(3, '150'), "
            "(4, '200');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 2")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1, 2], "Negated greater-than")

    def test_gte_positive(self):
        query = TagQuery.gte(TagName("price"), "100")
        wql = query.to_wql_str()
        print(f"Test: Positive greater-than-or-equal query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "t.price >= ?"
        expected_params = ["100"]
        self.assertEqual(
            sql_query, expected_query, "Positive greater-than-or-equal query mismatch"
        )
        self.assertEqual(
            params, expected_params, "Positive greater-than-or-equal params mismatch"
        )
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, price) VALUES (?, ?)",
            [(1, "090"), (2, "100"), (3, "150"), (4, "200")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, price TEXT);")
        print(
            "INSERT INTO items (id, price) VALUES "
            "(1, '090'), "
            "(2, '100'), "
            "(3, '150'), "
            "(4, '200');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 2, 3, 4")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(
            sql_query, params, [2, 3, 4], "Positive greater-than-or-equal"
        )

    def test_gte_negated(self):
        query = TagQuery.not_(TagQuery.gte(TagName("price"), "100"))
        wql = query.to_wql_str()
        print(f"Test: Negated greater-than-or-equal query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "NOT (t.price >= ?)"
        expected_params = ["100"]
        self.assertEqual(
            sql_query, expected_query, "Negated greater-than-or-equal query mismatch"
        )
        self.assertEqual(
            params, expected_params, "Negated greater-than-or-equal params mismatch"
        )
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, price) VALUES (?, ?)",
            [(1, "090"), (2, "100"), (3, "150"), (4, "200")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, price TEXT);")
        print(
            "INSERT INTO items (id, price) VALUES "
            "(1, '090'), "
            "(2, '100'), "
            "(3, '150'), "
            "(4, '200');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Item 1")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1], "Negated greater-than-or-equal")

    def test_lt_positive(self):
        query = TagQuery.lt(TagName("price"), "100")
        wql = query.to_wql_str()
        print(f"Test: Positive less-than query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "t.price < ?"
        expected_params = ["100"]
        self.assertEqual(sql_query, expected_query, "Positive less-than query mismatch")
        self.assertEqual(params, expected_params, "Positive less-than params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, price) VALUES (?, ?)",
            [(1, "090"), (2, "100"), (3, "150"), (4, "200")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, price TEXT);")
        print(
            "INSERT INTO items (id, price) VALUES "
            "(1, '090'), "
            "(2, '100'), "
            "(3, '150'), "
            "(4, '200');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Item 1")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1], "Positive less-than")

    def test_lt_negated(self):
        query = TagQuery.not_(TagQuery.lt(TagName("price"), "100"))
        wql = query.to_wql_str()
        print(f"Test: Negated less-than query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "NOT (t.price < ?)"
        expected_params = ["100"]
        self.assertEqual(sql_query, expected_query, "Negated less-than query mismatch")
        self.assertEqual(params, expected_params, "Negated less-than params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, price) VALUES (?, ?)",
            [(1, "090"), (2, "100"), (3, "150"), (4, "200")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, price TEXT);")
        print(
            "INSERT INTO items (id, price) VALUES "
            "(1, '090'), "
            "(2, '100'), "
            "(3, '150'), "
            "(4, '200');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 2, 3, 4")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [2, 3, 4], "Negated less-than")

    def test_lte_positive(self):
        query = TagQuery.lte(TagName("price"), "100")
        wql = query.to_wql_str()
        print(f"Test: Positive less-than-or-equal query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "t.price <= ?"
        expected_params = ["100"]
        self.assertEqual(
            sql_query, expected_query, "Positive less-than-or-equal query mismatch"
        )
        self.assertEqual(
            params, expected_params, "Positive less-than-or-equal params mismatch"
        )
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, price) VALUES (?, ?)",
            [(1, "090"), (2, "100"), (3, "150"), (4, "200")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, price TEXT);")
        print(
            "INSERT INTO items (id, price) VALUES "
            "(1, '090'), "
            "(2, '100'), "
            "(3, '150'), "
            "(4, '200');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 2")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(
            sql_query, params, [1, 2], "Positive less-than-or-equal"
        )

    def test_lte_negated(self):
        query = TagQuery.not_(TagQuery.lte(TagName("price"), "100"))
        wql = query.to_wql_str()
        print(f"Test: Negated less-than-or-equal query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "NOT (t.price <= ?)"
        expected_params = ["100"]
        self.assertEqual(
            sql_query, expected_query, "Negated less-than-or-equal query mismatch"
        )
        self.assertEqual(
            params, expected_params, "Negated less-than-or-equal params mismatch"
        )
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, price) VALUES (?, ?)",
            [(1, "090"), (2, "100"), (3, "150"), (4, "200")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, price TEXT);")
        print(
            "INSERT INTO items (id, price) VALUES "
            "(1, '090'), "
            "(2, '100'), "
            "(3, '150'), "
            "(4, '200');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 3, 4")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [3, 4], "Negated less-than-or-equal")

    def test_like_positive(self):
        query = TagQuery.like(
            TagName("field"), "%pat%"
        )  # Use %pat% for substring matching
        wql = query.to_wql_str()
        print(f"Test: Positive LIKE query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "t.field LIKE ?"
        expected_params = ["%pat%"]
        self.assertEqual(sql_query, expected_query, "Positive LIKE query mismatch")
        self.assertEqual(params, expected_params, "Positive LIKE params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, field) VALUES (?, ?)",
            [(1, "pattern"), (2, "path"), (3, "other"), (4, "pat")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, field TEXT);")
        print(
            "INSERT INTO items (id, field) VALUES "
            "(1, 'pattern'), "
            "(2, 'path'), "
            "(3, 'other'), "
            "(4, 'pat');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 2, 4")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1, 2, 4], "Positive LIKE")

    def test_like_negated(self):
        query = TagQuery.not_(
            TagQuery.like(TagName("field"), "%pat%")
        )  # Use %pat% for substring matching
        wql = query.to_wql_str()
        print(f"Test: Negated LIKE query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "NOT (t.field LIKE ?)"
        expected_params = ["%pat%"]
        self.assertEqual(sql_query, expected_query, "Negated LIKE query mismatch")
        self.assertEqual(params, expected_params, "Negated LIKE params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, field) VALUES (?, ?)",
            [(1, "pattern"), (2, "path"), (3, "other"), (4, "pat")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, field TEXT);")
        print(
            "INSERT INTO items (id, field) VALUES "
            "(1, 'pattern'), "
            "(2, 'path'), "
            "(3, 'other'), "
            "(4, 'pat');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Item 3")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [3], "Negated LIKE")

    def test_in_positive(self):
        query = TagQuery.in_(TagName("field"), ["a", "b"])
        wql = query.to_wql_str()
        print(f"Test: Positive IN query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "t.field IN (?, ?)"
        expected_params = ["a", "b"]
        self.assertEqual(sql_query, expected_query, "Positive IN query mismatch")
        self.assertEqual(params, expected_params, "Positive IN params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, field) VALUES (?, ?)",
            [(1, "a"), (2, "b"), (3, "c"), (4, "a")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, field TEXT);")
        print(
            "INSERT INTO items (id, field) VALUES (1, 'a'), (2, 'b'), (3, 'c'), (4, 'a');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 2, 4")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1, 2, 4], "Positive IN")

    def test_in_negated(self):
        query = TagQuery.not_(TagQuery.in_(TagName("field"), ["a", "b"]))
        wql = query.to_wql_str()
        print(f"Test: Negated IN query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "t.field NOT IN (?, ?)"
        expected_params = ["a", "b"]
        self.assertEqual(sql_query, expected_query, "Negated IN query mismatch")
        self.assertEqual(params, expected_params, "Negated IN params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, field) VALUES (?, ?)",
            [(1, "a"), (2, "b"), (3, "c"), (4, "d")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, field TEXT);")
        print(
            "INSERT INTO items (id, field) VALUES (1, 'a'), (2, 'b'), (3, 'c'), (4, 'd');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 3, 4")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [3, 4], "Negated IN")

    def test_exist_positive(self):
        query = TagQuery.exist([TagName("field")])
        wql = query.to_wql_str()
        print(f"Test: Positive EXIST query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "t.field IS NOT NULL"
        expected_params = []
        self.assertEqual(sql_query, expected_query, "Positive EXIST query mismatch")
        self.assertEqual(params, expected_params, "Positive EXIST params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, field) VALUES (?, ?)",
            [(1, "value"), (2, None), (3, "another")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, field TEXT);")
        print(
            "INSERT INTO items (id, field) VALUES "
            "(1, 'value'), "
            "(2, NULL), "
            "(3, 'another');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 3")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1, 3], "Positive EXIST")

    def test_exist_negated(self):
        query = TagQuery.not_(TagQuery.exist([TagName("field")]))
        wql = query.to_wql_str()
        print(f"Test: Negated EXIST query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "t.field IS NULL"
        expected_params = []
        self.assertEqual(sql_query, expected_query, "Negated EXIST query mismatch")
        self.assertEqual(params, expected_params, "Negated EXIST params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, field) VALUES (?, ?)",
            [(1, "value"), (2, None), (3, "another")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, field TEXT);")
        print(
            "INSERT INTO items (id, field) VALUES "
            "(1, 'value'), "
            "(2, NULL), "
            "(3, 'another');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Item 2")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [2], "Negated EXIST")

    # Conjunction Tests
    def test_and_multiple(self):
        query = TagQuery.and_(
            [TagQuery.eq(TagName("f1"), "v1"), TagQuery.gt(TagName("f2"), "10")]
        )
        wql = query.to_wql_str()
        print(f"Test: AND query with multiple subqueries\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "(t.f1 = ? AND t.f2 > ?)"
        expected_params = ["v1", "10"]
        self.assertEqual(sql_query, expected_query, "AND multiple query mismatch")
        self.assertEqual(params, expected_params, "AND multiple params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, f1, f2) VALUES (?, ?, ?)",
            [(1, "v1", "15"), (2, "v1", "05"), (3, "v2", "15"), (4, "v1", "20")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, f1 TEXT, f2 TEXT);")
        print(
            "INSERT INTO items (id, f1, f2) VALUES "
            "(1, 'v1', '15'), "
            "(2, 'v1', '05'), "
            "(3, 'v2', '15'), "
            "(4, 'v1', '20');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 4")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1, 4], "AND multiple")

    def test_or_multiple(self):
        query = TagQuery.or_(
            [TagQuery.eq(TagName("f1"), "v1"), TagQuery.gt(TagName("f2"), "10")]
        )
        wql = query.to_wql_str()
        print(f"Test: OR query with multiple subqueries\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "(t.f1 = ? OR t.f2 > ?)"
        expected_params = ["v1", "10"]
        self.assertEqual(sql_query, expected_query, "OR multiple query mismatch")
        self.assertEqual(params, expected_params, "OR multiple params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, f1, f2) VALUES (?, ?, ?)",
            [(1, "v1", "15"), (2, "v1", "05"), (3, "v2", "15"), (4, "v2", "05")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, f1 TEXT, f2 TEXT);")
        print(
            "INSERT INTO items (id, f1, f2) VALUES "
            "(1, 'v1', '15'), "
            "(2, 'v1', '05'), "
            "(3, 'v2', '15'), "
            "(4, 'v2', '05');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 2, 3")
        print("\n-- Cleanup\nDELETE FROM items;")
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
        expected_query = "(t.f1 = ? AND (t.f2 > ? OR t.f3 < ?))"
        expected_params = ["v1", "10", "5"]
        self.assertEqual(sql_query, expected_query, "Nested AND/OR query mismatch")
        self.assertEqual(params, expected_params, "Nested AND/OR params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, f1, f2, f3) VALUES (?, ?, ?, ?)",
            [
                (1, "v1", "15", "3"),
                (2, "v1", "05", "4"),
                (3, "v2", "15", "3"),
                (4, "v1", "05", "6"),
            ],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, f1 TEXT, f2 TEXT, f3 TEXT);")
        print(
            "INSERT INTO items (id, f1, f2, f3) VALUES "
            "(1, 'v1', '15', '3'), "
            "(2, 'v1', '05', '4'), "
            "(3, 'v2', '15', '3'), "
            "(4, 'v1', '05', '6');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 2")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1, 2], "Nested AND/OR")

    # Complex Query Tests
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
        expected_query = "(t.category = ? AND t.price > ?)"
        expected_params = ["electronics", "100"]
        self.assertEqual(
            sql_query, expected_query, "Comparison conjunction query mismatch"
        )
        self.assertEqual(
            params, expected_params, "Comparison conjunction params mismatch"
        )
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, category, price) VALUES (?, ?, ?)",
            [
                (1, "electronics", "150"),
                (2, "electronics", "090"),
                (3, "books", "120"),
                (4, "electronics", "200"),
            ],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, category TEXT, price TEXT);")
        print(
            "INSERT INTO items (id, category, price) VALUES "
            "(1, 'electronics', '150'), "
            "(2, 'electronics', '090'), "
            "(3, 'books', '120'), "
            "(4, 'electronics', '200');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 4")
        print("\n-- Cleanup\nDELETE FROM items;")
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
        expected_query = "NOT ((t.category = ? OR t.sale = ?) AND NOT (t.stock = ?))"
        expected_params = ["electronics", "yes", "out"]
        self.assertEqual(sql_query, expected_query, "Deeply nested NOT query mismatch")
        self.assertEqual(params, expected_params, "Deeply nested NOT params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, category, sale, stock) VALUES (?, ?, ?, ?)",
            [
                (1, "electronics", None, "in"),
                (2, "electronics", None, "out"),
                (3, None, "yes", "in"),
                (4, None, "yes", None),
            ],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print(
            "CREATE TABLE items (id INTEGER PRIMARY KEY, category TEXT, sale TEXT, stock TEXT);"
        )
        print(
            "INSERT INTO items (id, category, sale, stock) VALUES "
            "(1, 'electronics', NULL, 'in'), "
            "(2, 'electronics', NULL, 'out'), "
            "(3, NULL, 'yes', 'in'), "
            "(4, NULL, 'yes', NULL);"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Item 2")
        print("\n-- Cleanup\nDELETE FROM items;")
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
        expected_query = "NOT (t.username = ? AND (t.age > ? OR NOT (t.height <= ?) OR (t.score < ? AND NOT (t.timestamp >= ?))) AND NOT (t.secret_code LIKE ?) AND (t.occupation = ? AND NOT (t.status != ?)))"
        expected_params = [
            "alice",
            "30",
            "180",
            "100",
            "2021-01-01T00:00:00",
            "abc123",
            "developer",
            "active",
        ]
        self.assertEqual(sql_query, expected_query, "Complex AND/OR/NOT query mismatch")
        self.assertEqual(params, expected_params, "Complex AND/OR/NOT params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, username, age, height, score, timestamp, secret_code, occupation, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    1,
                    "bob",
                    "25",
                    "170",
                    "150",
                    "2021-02-01T00:00:00",
                    "xyz789",
                    "engineer",
                    "inactive",
                ),
                (
                    2,
                    "alice",
                    "35",
                    "190",
                    "90",
                    "2020-12-01T00:00:00",
                    "def456",
                    "developer",
                    "active",
                ),
                (
                    3,
                    "charlie",
                    "28",
                    "175",
                    "120",
                    "2021-03-01T00:00:00",
                    "ghi789",
                    "manager",
                    "active",
                ),
                (
                    4,
                    "alice",
                    "32",
                    "185",
                    "95",
                    "2020-11-01T00:00:00",
                    "abc123",
                    "developer",
                    "inactive",
                ),
                (
                    5,
                    "eve",
                    "40",
                    "160",
                    "85",
                    "2021-01-15T00:00:00",
                    "abc123",
                    "analyst",
                    "active",
                ),
                (
                    6,
                    "frank",
                    "29",
                    "182",
                    "105",
                    "2020-12-15T00:00:00",
                    "jkl012",
                    "developer",
                    "active",
                ),
                (
                    7,
                    "alice",
                    "33",
                    "195",
                    "88",
                    "2020-10-01T00:00:00",
                    "mno345",
                    "developer",
                    "active",
                ),
                (
                    8,
                    "hank",
                    "27",
                    "165",
                    "110",
                    "2021-04-01T00:00:00",
                    "pqr678",
                    "designer",
                    "inactive",
                ),
                (
                    9,
                    "alice",
                    "36",
                    "188",
                    "92",
                    "2020-09-01T00:00:00",
                    "stu901",
                    "developer",
                    "active",
                ),
                (
                    10,
                    "jack",
                    "31",
                    "179",
                    "115",
                    "2021-05-01T00:00:00",
                    "vwx234",
                    "teacher",
                    "active",
                ),
                (
                    11,
                    "kara",
                    "26",
                    "170",
                    "130",
                    "2021-06-01T00:00:00",
                    "yza567",
                    "developer",
                    "inactive",
                ),
                (
                    12,
                    "alice",
                    "34",
                    "192",
                    "87",
                    "2020-08-01T00:00:00",
                    "bcd890",
                    "developer",
                    "active",
                ),
            ],
        )
        self.conn.commit()
        expected_ids = [
            1,
            3,
            4,
            5,
            6,
            8,
            10,
            11,
        ]  # bob, charlie, dave, eve, frank, hank, jack, kara
        print("\n### Complete SQL Statements for Testing")
        print(
            "CREATE TABLE items (id INTEGER PRIMARY KEY, username TEXT, age TEXT, height TEXT, score TEXT, timestamp TEXT, secret_code TEXT, occupation TEXT, status TEXT);"
        )
        print(
            "INSERT INTO items (id, username, age, height, score, timestamp, secret_code, occupation, status) VALUES "
            "(1, 'bob', '25', '170', '150', '2021-02-01T00:00:00', 'xyz789', 'engineer', 'inactive'), "
            "(2, 'alice', '35', '190', '90', '2020-12-01T00:00:00', 'def456', 'developer', 'active'), "
            "(3, 'charlie', '28', '175', '120', '2021-03-01T00:00:00', 'ghi789', 'manager', 'active'), "
            "(4, 'alice', '32', '185', '95', '2020-11-01T00:00:00', 'abc123', 'developer', 'inactive'), "
            "(5, 'eve', '40', '160', '85', '2021-01-15T00:00:00', 'abc123', 'analyst', 'active'), "
            "(6, 'frank', '29', '182', '105', '2020-12-15T00:00:00', 'jkl012', 'developer', 'active'), "
            "(7, 'alice', '33', '195', '88', '2020-10-01T00:00:00', 'mno345', 'developer', 'active'), "
            "(8, 'hank', '27', '165', '110', '2021-04-01T00:00:00', 'pqr678', 'designer', 'inactive'), "
            "(9, 'alice', '36', '188', '92', '2020-09-01T00:00:00', 'stu901', 'developer', 'active'), "
            "(10, 'jack', '31', '179', '115', '2021-05-01T00:00:00', 'vwx234', 'teacher', 'active'), "
            "(11, 'kara', '26', '170', '130', '2021-06-01T00:00:00', 'yza567', 'developer', 'inactive'), "
            "(12, 'alice', '34', '192', '87', '2020-08-01T00:00:00', 'bcd890', 'developer', 'active');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print(f"\n-- Expected result: Items {expected_ids}")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(
            sql_query, params, expected_ids, "Complex AND/OR/NOT query"
        )

    # Edge Case Tests
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
        self.cursor.executemany(
            "INSERT INTO items (id, field) VALUES (?, ?)", [(1, "value"), (2, "data")]
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, field TEXT);")
        print("INSERT INTO items (id, field) VALUES (1, 'value'), (2, 'data');")
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 2")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1, 2], "Empty query")

    def test_multiple_exists(self):
        query = TagQuery.exist([TagName("f1"), TagName("f2")])
        wql = query.to_wql_str()
        print(f"Test: Multiple EXISTS query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "(t.f1 IS NOT NULL AND t.f2 IS NOT NULL)"
        expected_params = []
        self.assertEqual(sql_query, expected_query, "Multiple EXISTS query mismatch")
        self.assertEqual(params, expected_params, "Multiple EXISTS params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, f1, f2) VALUES (?, ?, ?)",
            [(1, "v1", "v2"), (2, "v1", None), (3, None, "v2"), (4, None, None)],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, f1 TEXT, f2 TEXT);")
        print(
            "INSERT INTO items (id, f1, f2) VALUES "
            "(1, 'v1', 'v2'), "
            "(2, 'v1', NULL), "
            "(3, NULL, 'v2'), "
            "(4, NULL, NULL);"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Item 1")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1], "Multiple EXISTS")

    def test_special_characters(self):
        query = TagQuery.eq(TagName("f1"), "val$ue")
        wql = query.to_wql_str()
        print(f"Test: Special characters query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "t.f1 = ?"
        expected_params = ["val$ue"]
        self.assertEqual(sql_query, expected_query, "Special characters query mismatch")
        self.assertEqual(params, expected_params, "Special characters params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, f1) VALUES (?, ?)",
            [(1, "val$ue"), (2, "other"), (3, "val$ue")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id INTEGER PRIMARY KEY, f1 TEXT);")
        print(
            "INSERT INTO items (id, f1) VALUES "
            "(1, 'val$ue'), "
            "(2, 'other'), "
            "(3, 'val$ue');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 3")
        print("\n-- Cleanup\nDELETE FROM items;")
        self.run_query_and_verify(sql_query, params, [1, 3], "Special characters")


def main():
    print("Running SqliteTagEncoder tests...")
    unittest.main(argv=[""], exit=False)
    print("All tests completed.")


if __name__ == "__main__":
    main()
