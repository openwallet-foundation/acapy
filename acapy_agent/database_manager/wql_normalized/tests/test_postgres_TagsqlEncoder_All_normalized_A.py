# pytest --maxfail=1 --disable-warnings --no-cov -s -vv acapy_agent/database_manager/wql_normalized/tests/test_postgres_TagsqlEncoder_All_normalized_A.py
# python -m unittest acapy_agent/database_manager/wql_normalized/tests/test_postgres_TagsqlEncoder_All_normalized_A.py -v

import logging
import os
import unittest

import psycopg
import pytest

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
    """Replace each '%s' in the query with the corresponding argument for logging.

    Properly quote arguments for SQL, escaping single quotes by doubling them.
    Example: 'O'Reilly' becomes 'O''Reilly'.
    """
    result = query
    for arg in args:
        escaped_arg = str(arg).replace("'", "''")  # Escape single quotes for SQL
        result = result.replace("%s", f"'{escaped_arg}'", 1)  # Replace one %s at a time
    return result


@pytest.mark.postgres
class TestPostgresTagEncoderNormalized(unittest.TestCase):
    """Test cases for the PostgresTagEncoder class in normalized mode (part A)."""

    def setUp(self):
        """Set up PostgreSQL database connection and encoder.

        Note: normalized=True causes column names to be prefixed with 't.' in SQL queries.
        """
        self.enc_name = lambda x: x  # No transformation for tag names
        self.enc_value = lambda x: x  # No transformation for tag values

        # Get PostgreSQL connection from environment variable or use default
        postgres_url = os.environ.get(
            "POSTGRES_URL", "postgres://myuser:mypass@localhost:5432/mydb2"
        )
        # Parse the URL to extract connection parameters
        import urllib.parse

        parsed = urllib.parse.urlparse(postgres_url)

        try:
            self.conn = psycopg.connect(
                host=parsed.hostname or "localhost",
                port=parsed.port or 5432,
                dbname=parsed.path.lstrip("/") if parsed.path else "mydb2",
                user=parsed.username or "myuser",
                password=parsed.password or "mypass",
            )
            self.conn.autocommit = True  # Enable autocommit for setup/teardown
            self.cursor = self.conn.cursor()
            # Create a normalized table with columns for test fields
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY,
                    field TEXT,
                    price TEXT
                )
            """)
            logger.info("Table 'items' created in setUp")
            self.encoder = encoder_factory.get_encoder(
                "postgresql", self.enc_name, self.enc_value, normalized=True
            )
        except Exception as e:
            logger.error(f"Failed to set up PostgreSQL database: {e}")
            raise

    def tearDown(self):
        """Clean up by dropping the table and closing the PostgreSQL connection."""
        try:
            self.cursor.execute("DROP TABLE IF EXISTS items")
            self.conn.commit()
            self.cursor.close()
            self.conn.close()
            logger.info("Table dropped and PostgreSQL connection closed in tearDown")
        except Exception as e:
            logger.error(f"Failed to tear down PostgreSQL connection: {e}")
            raise

    def run_query_and_verify(self, sql_query, params, expected_ids, test_name):
        """Run a PostgreSQL query and verify the results against expected IDs."""
        try:
            # Extract query string if sql_query is a tuple
            query = sql_query[0] if isinstance(sql_query, tuple) else sql_query
            logger.info(f"Raw query from encoder: {sql_query}")
            logger.info(
                f"Executing query: SELECT id FROM items AS t WHERE {query} with params: {params}"
            )
            self.cursor.execute(f"SELECT id FROM items AS t WHERE {query}", params)
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
        """Verify that converting TagQuery to WQL and back results in the same PostgreSQL query."""
        wql_str = query.to_wql_str()
        parsed_query = query_from_str(wql_str)
        parsed_tag_query = query_to_tagquery(parsed_query)
        parsed_sql_query = self.encoder.encode_query(parsed_tag_query)
        parsed_params = self.encoder.arguments
        parsed_sql_query_str = (
            parsed_sql_query[0]
            if isinstance(parsed_sql_query, tuple)
            else parsed_sql_query
        )
        self.assertEqual(
            (original_sql_query, original_params),
            (parsed_sql_query_str, parsed_params),
            f"Round-trip PostgreSQL query mismatch in {self._testMethodName}",
        )

    def test_eq_positive(self):
        query = TagQuery.eq(TagName("field"), "value")
        wql = query.to_wql_str()
        print(f"Test: Positive equality query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "t.field = %s"
        expected_params = ["value"]
        self.assertEqual(
            sql_query[0] if isinstance(sql_query, tuple) else sql_query,
            expected_query,
            "Positive equality query mismatch",
        )
        self.assertEqual(params, expected_params, "Positive equality params mismatch")
        self.verify_round_trip(query, expected_query, expected_params)
        self.cursor.executemany(
            "INSERT INTO items (id, field) VALUES (%s, %s) RETURNING id",
            [(1, "value"), (2, "other"), (3, "value")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, field TEXT);")
        print(
            "INSERT INTO items (id, field) VALUES "
            "(1, 'value'), "
            "(2, 'other'), "
            "(3, 'value');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {expected_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 3")
        print("\n-- Cleanup\nDROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [1, 3], "Positive equality")

    def test_eq_negated(self):
        query = TagQuery.not_(TagQuery.eq(TagName("field"), "value"))
        wql = query.to_wql_str()
        print(f"Test: Negated equality query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "NOT (t.field = %s)"
        expected_params = ["value"]
        self.assertEqual(
            sql_query[0] if isinstance(sql_query, tuple) else sql_query,
            expected_query,
            "Negated equality query mismatch",
        )
        self.assertEqual(params, expected_params, "Negated equality params mismatch")
        self.verify_round_trip(query, expected_query, expected_params)
        self.cursor.executemany(
            "INSERT INTO items (id, field) VALUES (%s, %s) RETURNING id",
            [(1, "value"), (2, "other"), (3, "value")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, field TEXT);")
        print(
            "INSERT INTO items (id, field) VALUES "
            "(1, 'value'), "
            "(2, 'other'), "
            "(3, 'value');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {expected_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Item 2")
        print("\n-- Cleanup\nDROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [2], "Negated equality")

    def test_neq_positive(self):
        query = TagQuery.neq(TagName("field"), "value")
        wql = query.to_wql_str()
        print(f"Test: Positive inequality query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "t.field != %s"
        expected_params = ["value"]
        self.assertEqual(
            sql_query[0] if isinstance(sql_query, tuple) else sql_query,
            expected_query,
            "Positive inequality query mismatch",
        )
        self.assertEqual(params, expected_params, "Positive inequality params mismatch")
        self.verify_round_trip(query, expected_query, expected_params)
        self.cursor.executemany(
            "INSERT INTO items (id, field) VALUES (%s, %s) RETURNING id",
            [(1, "value"), (2, "other"), (3, "different")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, field TEXT);")
        print(
            "INSERT INTO items (id, field) VALUES "
            "(1, 'value'), "
            "(2, 'other'), "
            "(3, 'different');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {expected_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 2, 3")
        print("\n-- Cleanup\nDROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [2, 3], "Positive inequality")

    def test_neq_negated(self):
        query = TagQuery.not_(TagQuery.neq(TagName("field"), "value"))
        wql = query.to_wql_str()
        print(f"Test: Negated inequality query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "NOT (t.field != %s)"
        expected_params = ["value"]
        self.assertEqual(
            sql_query[0] if isinstance(sql_query, tuple) else sql_query,
            expected_query,
            "Negated inequality query mismatch",
        )
        self.assertEqual(params, expected_params, "Negated inequality params mismatch")
        self.verify_round_trip(query, expected_query, expected_params)
        self.cursor.executemany(
            "INSERT INTO items (id, field) VALUES (%s, %s) RETURNING id",
            [(1, "value"), (2, "other"), (3, "value")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, field TEXT);")
        print(
            "INSERT INTO items (id, field) VALUES "
            "(1, 'value'), "
            "(2, 'other'), "
            "(3, 'value');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {expected_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 3")
        print("\n-- Cleanup\nDROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [1, 3], "Negated inequality")

    def test_gt_positive(self):
        query = TagQuery.gt(TagName("price"), "100")
        wql = query.to_wql_str()
        print(f"Test: Positive greater-than query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "t.price > %s"
        expected_params = ["100"]
        self.assertEqual(
            sql_query[0] if isinstance(sql_query, tuple) else sql_query,
            expected_query,
            "Positive greater-than query mismatch",
        )
        self.assertEqual(params, expected_params, "Positive greater-than params mismatch")
        self.verify_round_trip(query, expected_query, expected_params)
        self.cursor.executemany(
            "INSERT INTO items (id, price) VALUES (%s, %s) RETURNING id",
            [(1, "090"), (2, "100"), (3, "150"), (4, "200")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, price TEXT);")
        print(
            "INSERT INTO items (id, price) VALUES "
            "(1, '090'), "
            "(2, '100'), "
            "(3, '150'), "
            "(4, '200');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {expected_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 3, 4")
        print("\n-- Cleanup\nDROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [3, 4], "Positive greater-than")

    def test_gt_negated(self):
        query = TagQuery.not_(TagQuery.gt(TagName("price"), "100"))
        wql = query.to_wql_str()
        print(f"Test: Negated greater-than query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "NOT (t.price > %s)"
        expected_params = ["100"]
        self.assertEqual(
            sql_query[0] if isinstance(sql_query, tuple) else sql_query,
            expected_query,
            "Negated greater-than query mismatch",
        )
        self.assertEqual(params, expected_params, "Negated greater-than params mismatch")
        self.verify_round_trip(query, expected_query, expected_params)
        self.cursor.executemany(
            "INSERT INTO items (id, price) VALUES (%s, %s) RETURNING id",
            [(1, "090"), (2, "100"), (3, "150"), (4, "200")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, price TEXT);")
        print(
            "INSERT INTO items (id, price) VALUES "
            "(1, '090'), "
            "(2, '100'), "
            "(3, '150'), "
            "(4, '200');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {expected_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 2")
        print("\n-- Cleanup\nDROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [1, 2], "Negated greater-than")

    def test_gte_positive(self):
        query = TagQuery.gte(TagName("price"), "100")
        wql = query.to_wql_str()
        print(f"Test: Positive greater-than-or-equal query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "t.price >= %s"
        expected_params = ["100"]
        self.assertEqual(
            sql_query[0] if isinstance(sql_query, tuple) else sql_query,
            expected_query,
            "Positive greater-than-or-equal query mismatch",
        )
        self.assertEqual(
            params, expected_params, "Positive greater-than-or-equal params mismatch"
        )
        self.verify_round_trip(query, expected_query, expected_params)
        self.cursor.executemany(
            "INSERT INTO items (id, price) VALUES (%s, %s) RETURNING id",
            [(1, "090"), (2, "100"), (3, "150"), (4, "200")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, price TEXT);")
        print(
            "INSERT INTO items (id, price) VALUES "
            "(1, '090'), "
            "(2, '100'), "
            "(3, '150'), "
            "(4, '200');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {expected_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 2, 3, 4")
        print("\n-- Cleanup\nDROP TABLE items;")
        self.run_query_and_verify(
            sql_query, params, [2, 3, 4], "Positive greater-than-or-equal"
        )

    def test_gte_negated(self):
        query = TagQuery.not_(TagQuery.gte(TagName("price"), "100"))
        wql = query.to_wql_str()
        print(f"Test: Negated greater-than-or-equal query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "NOT (t.price >= %s)"
        expected_params = ["100"]
        self.assertEqual(
            sql_query[0] if isinstance(sql_query, tuple) else sql_query,
            expected_query,
            "Negated greater-than-or-equal query mismatch",
        )
        self.assertEqual(
            params, expected_params, "Negated greater-than-or-equal params mismatch"
        )
        self.verify_round_trip(query, expected_query, expected_params)
        self.cursor.executemany(
            "INSERT INTO items (id, price) VALUES (%s, %s) RETURNING id",
            [(1, "090"), (2, "100"), (3, "150"), (4, "200")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, price TEXT);")
        print(
            "INSERT INTO items (id, price) VALUES "
            "(1, '090'), "
            "(2, '100'), "
            "(3, '150'), "
            "(4, '200');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {expected_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Item 1")
        print("\n-- Cleanup\nDROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [1], "Negated greater-than-or-equal")

    def test_lt_positive(self):
        query = TagQuery.lt(TagName("price"), "100")
        wql = query.to_wql_str()
        print(f"Test: Positive less-than query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "t.price < %s"
        expected_params = ["100"]
        self.assertEqual(
            sql_query[0] if isinstance(sql_query, tuple) else sql_query,
            expected_query,
            "Positive less-than query mismatch",
        )
        self.assertEqual(params, expected_params, "Positive less-than params mismatch")
        self.verify_round_trip(query, expected_query, expected_params)
        self.cursor.executemany(
            "INSERT INTO items (id, price) VALUES (%s, %s) RETURNING id",
            [(1, "090"), (2, "100"), (3, "150"), (4, "200")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, price TEXT);")
        print(
            "INSERT INTO items (id, price) VALUES "
            "(1, '090'), "
            "(2, '100'), "
            "(3, '150'), "
            "(4, '200');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {expected_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Item 1")
        print("\n-- Cleanup\nDROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [1], "Positive less-than")

    def test_lt_negated(self):
        query = TagQuery.not_(TagQuery.lt(TagName("price"), "100"))
        wql = query.to_wql_str()
        print(f"Test: Negated less-than query\nWQL: {wql}")
        sql_query = self.encoder.encode_query(query)
        params = self.encoder.arguments
        expected_query = "NOT (t.price < %s)"
        expected_params = ["100"]
        self.assertEqual(
            sql_query[0] if isinstance(sql_query, tuple) else sql_query,
            expected_query,
            "Negated less-than query mismatch",
        )
        self.assertEqual(params, expected_params, "Negated less-than params mismatch")
        self.verify_round_trip(query, expected_query, expected_params)
        self.cursor.executemany(
            "INSERT INTO items (id, price) VALUES (%s, %s) RETURNING id",
            [(1, "090"), (2, "100"), (3, "150"), (4, "200")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, price TEXT);")
        print(
            "INSERT INTO items (id, price) VALUES "
            "(1, '090'), "
            "(2, '100'), "
            "(3, '150'), "
            "(4, '200');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {expected_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 2, 3, 4")
        print("\n-- Cleanup\nDROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [2, 3, 4], "Negated less-than")


def main():
    print("Running PostgresTagEncoder tests (part A)...")
    unittest.main(argv=[""], exit=False)
    print("All tests completed.")


if __name__ == "__main__":
    main()
