# pytest --maxfail=1 --disable-warnings --no-cov -s -vv acapy_agent/database_manager/wql_normalized/tests/test_postgres_TagsqlEncoder_All_normalized_B.py
# python -m unittest acapy_agent/database_manager/wql_normalized/tests/test_postgres_TagsqlEncoder_All_normalized_B.py -v

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
    """Test cases for the PostgresTagEncoder class in normalized mode (part B)."""

    def setUp(self):
        """Set up PostgreSQL database connection and encoder."""
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
                user="myuser",
                password="mypass",
            )
            self.conn.autocommit = True  # Enable autocommit for setup/teardown
            self.cursor = self.conn.cursor()
            # Create a normalized table with columns for all test fields
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY,
                    field TEXT,
                    category TEXT,
                    price TEXT,
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
            query = sql_query[0] if isinstance(sql_query, tuple) else sql_query
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
        parsed_sql_query, parsed_params = self.encoder.encode_query(parsed_tag_query)
        self.assertEqual(
            (original_sql_query, original_params),
            (parsed_sql_query, parsed_params),
            f"Round-trip PostgreSQL query mismatch in {self._testMethodName}",
        )

    def test_like_positive(self):
        query = TagQuery.like(TagName("field"), "%pat%")
        wql = query.to_wql_str()
        print(f"Test: Positive LIKE query\nWQL: {wql}")
        sql_query, params = self.encoder.encode_query(query)
        expected_query = "t.field LIKE %s"
        expected_params = ["%pat%"]
        self.assertEqual(sql_query, expected_query, "Positive LIKE query mismatch")
        self.assertEqual(params, expected_params, "Positive LIKE params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, field) VALUES (%s, %s) RETURNING id",
            [(1, "pattern"), (2, "path"), (3, "other"), (4, "pat")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, field TEXT);")
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
        print("\n-- Cleanup\nDROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [1, 2, 4], "Positive LIKE")

    def test_like_negated(self):
        query = TagQuery.not_(TagQuery.like(TagName("field"), "%pat%"))
        wql = query.to_wql_str()
        print(f"Test: Negated LIKE query\nWQL: {wql}")
        sql_query, params = self.encoder.encode_query(query)
        expected_query = "NOT (t.field LIKE %s)"
        expected_params = ["%pat%"]
        self.assertEqual(sql_query, expected_query, "Negated LIKE query mismatch")
        self.assertEqual(params, expected_params, "Negated LIKE params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, field) VALUES (%s, %s) RETURNING id",
            [(1, "pattern"), (2, "path"), (3, "other"), (4, "pat")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, field TEXT);")
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
        print("\n-- Cleanup\nDROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [3], "Negated LIKE")

    def test_in_positive(self):
        query = TagQuery.in_(TagName("field"), ["a", "b"])
        wql = query.to_wql_str()
        print(f"Test: Positive IN query\nWQL: {wql}")
        sql_query, params = self.encoder.encode_query(query)
        expected_query = "t.field IN (%s, %s)"
        expected_params = ["a", "b"]
        self.assertEqual(sql_query, expected_query, "Positive IN query mismatch")
        self.assertEqual(params, expected_params, "Positive IN params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, field) VALUES (%s, %s) RETURNING id",
            [(1, "a"), (2, "b"), (3, "c"), (4, "a")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, field TEXT);")
        print(
            "INSERT INTO items (id, field) VALUES (1, 'a'), (2, 'b'), (3, 'c'), (4, 'a');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 2, 4")
        print("\n-- Cleanup\nDROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [1, 2, 4], "Positive IN")

    def test_in_negated(self):
        query = TagQuery.not_(TagQuery.in_(TagName("field"), ["a", "b"]))
        wql = query.to_wql_str()
        print(f"Test: Negated IN query\nWQL: {wql}")
        sql_query, params = self.encoder.encode_query(query)
        expected_query = "t.field NOT IN (%s, %s)"
        expected_params = ["a", "b"]
        self.assertEqual(sql_query, expected_query, "Negated IN query mismatch")
        self.assertEqual(params, expected_params, "Negated IN params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, field) VALUES (%s, %s) RETURNING id",
            [(1, "a"), (2, "b"), (3, "c"), (4, "d")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, field TEXT);")
        print(
            "INSERT INTO items (id, field) VALUES (1, 'a'), (2, 'b'), (3, 'c'), (4, 'd');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 3, 4")
        print("\n-- Cleanup\nDROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [3, 4], "Negated IN")

    def test_exist_positive(self):
        query = TagQuery.exist([TagName("field")])
        wql = query.to_wql_str()
        print(f"Test: Positive EXIST query\nWQL: {wql}")
        sql_query, params = self.encoder.encode_query(query)
        expected_query = "t.field IS NOT NULL"
        expected_params = []
        self.assertEqual(sql_query, expected_query, "Positive EXIST query mismatch")
        self.assertEqual(params, expected_params, "Positive EXIST params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, field) VALUES (%s, %s) RETURNING id",
            [(1, "value"), (2, None), (3, "another")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, field TEXT);")
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
        print("\n-- Cleanup\nDROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [1, 3], "Positive EXIST")

    def test_exist_negated(self):
        query = TagQuery.not_(TagQuery.exist([TagName("field")]))
        wql = query.to_wql_str()
        print(f"Test: Negated EXIST query\nWQL: {wql}")
        sql_query, params = self.encoder.encode_query(query)
        expected_query = "t.field IS NULL"
        expected_params = []
        self.assertEqual(sql_query, expected_query, "Negated EXIST query mismatch")
        self.assertEqual(params, expected_params, "Negated EXIST params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, field) VALUES (%s, %s) RETURNING id",
            [(1, "value"), (2, None), (3, "another")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, field TEXT);")
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
        print("\n-- Cleanup\nDROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [2], "Negated EXIST")

    def test_and_multiple(self):
        query = TagQuery.and_(
            [TagQuery.eq(TagName("f1"), "v1"), TagQuery.gt(TagName("f2"), "10")]
        )
        wql = query.to_wql_str()
        print(f"Test: AND query with multiple subqueries\nWQL: {wql}")
        sql_query, params = self.encoder.encode_query(query)
        expected_query = "(t.f1 = %s AND t.f2 > %s)"
        expected_params = ["v1", "10"]
        self.assertEqual(sql_query, expected_query, "AND multiple query mismatch")
        self.assertEqual(params, expected_params, "AND multiple params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, f1, f2) VALUES (%s, %s, %s) RETURNING id",
            [(1, "v1", "15"), (2, "v1", "05"), (3, "v2", "15"), (4, "v1", "20")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, f1 TEXT, f2 TEXT);")
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
        print("\n-- Cleanup\nDROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [1, 4], "AND multiple")

    def test_or_multiple(self):
        query = TagQuery.or_(
            [TagQuery.eq(TagName("f1"), "v1"), TagQuery.gt(TagName("f2"), "10")]
        )
        wql = query.to_wql_str()
        print(f"Test: OR query with multiple subqueries\nWQL: {wql}")
        sql_query, params = self.encoder.encode_query(query)
        expected_query = "(t.f1 = %s OR t.f2 > %s)"
        expected_params = ["v1", "10"]
        self.assertEqual(sql_query, expected_query, "OR multiple query mismatch")
        self.assertEqual(params, expected_params, "OR multiple params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, f1, f2) VALUES (%s, %s, %s) RETURNING id",
            [(1, "v1", "15"), (2, "v1", "05"), (3, "v2", "15"), (4, "v2", "05")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, f1 TEXT, f2 TEXT);")
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
        print("\n-- Cleanup\nDROP TABLE items;")
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
        sql_query, params = self.encoder.encode_query(query)
        expected_query = "(t.f1 = %s AND (t.f2 > %s OR t.f3 < %s))"
        expected_params = ["v1", "10", "5"]
        self.assertEqual(sql_query, expected_query, "Nested AND/OR query mismatch")
        self.assertEqual(params, expected_params, "Nested AND/OR params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, f1, f2, f3) VALUES (%s, %s, %s, %s) RETURNING id",
            [
                (1, "v1", "15", "3"),
                (2, "v1", "05", "4"),
                (3, "v2", "15", "3"),
                (4, "v1", "05", "6"),
            ],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, f1 TEXT, f2 TEXT, f3 TEXT);")
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
        print("\n-- Cleanup\nDROP TABLE items;")
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
        sql_query, params = self.encoder.encode_query(query)
        expected_query = "(t.category = %s AND t.price > %s)"
        expected_params = ["electronics", "100"]
        self.assertEqual(
            sql_query, expected_query, "Comparison conjunction query mismatch"
        )
        self.assertEqual(
            params, expected_params, "Comparison conjunction params mismatch"
        )
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, category, price) VALUES (%s, %s, %s) RETURNING id",
            [
                (1, "electronics", "150"),
                (2, "electronics", "090"),
                (3, "books", "120"),
                (4, "electronics", "200"),
            ],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, category TEXT, price TEXT);")
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
        print("\n-- Cleanup\nDROP TABLE items;")
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
        sql_query, params = self.encoder.encode_query(query)
        expected_query = "NOT ((t.category = %s OR t.sale = %s) AND NOT (t.stock = %s))"
        expected_params = ["electronics", "yes", "out"]
        self.assertEqual(sql_query, expected_query, "Deeply nested NOT query mismatch")
        self.assertEqual(params, expected_params, "Deeply nested NOT params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, category, sale, stock) VALUES (%s, %s, %s, %s) RETURNING id",
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
            "CREATE TABLE items (id SERIAL PRIMARY KEY, category TEXT, sale TEXT, stock TEXT);"
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
        print("\n-- Cleanup\nDROP TABLE items;")
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
        sql_query, params = self.encoder.encode_query(query)
        expected_query = "NOT (t.username = %s AND (t.age > %s OR NOT (t.height <= %s) OR (t.score < %s AND NOT (t.timestamp >= %s))) AND NOT (t.secret_code LIKE %s) AND (t.occupation = %s AND NOT (t.status != %s)))"
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
            "INSERT INTO items (id, username, age, height, score, timestamp, secret_code, occupation, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
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
        expected_ids = [1, 3, 4, 5, 6, 8, 10, 11]
        print("\n### Complete SQL Statements for Testing")
        print(
            "CREATE TABLE items (id SERIAL PRIMARY KEY, username TEXT, age TEXT, height TEXT, score TEXT, timestamp TEXT, secret_code TEXT, occupation TEXT, status TEXT);"
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
        print("\n-- Cleanup\nDROP TABLE items;")
        self.run_query_and_verify(
            sql_query, params, expected_ids, "Complex AND/OR/NOT query"
        )

    def test_empty_query(self):
        query = TagQuery.and_([])
        wql = query.to_wql_str()
        print(f"Test: Empty query\nWQL: {wql}")
        sql_query, params = self.encoder.encode_query(query)
        expected_query = "TRUE"
        expected_params = []
        self.assertEqual(sql_query, expected_query, "Empty query mismatch")
        self.assertEqual(params, expected_params, "Empty query params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, field) VALUES (%s, %s) RETURNING id",
            [(1, "value"), (2, "data")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, field TEXT);")
        print("INSERT INTO items (id, field) VALUES (1, 'value'), (2, 'data');")
        select_query = f"SELECT id FROM items AS t WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 2")
        print("\n-- Cleanup\nDROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [1, 2], "Empty query")

    def test_multiple_exists(self):
        query = TagQuery.exist([TagName("f1"), TagName("f2")])
        wql = query.to_wql_str()
        print(f"Test: Multiple EXISTS query\nWQL: {wql}")
        sql_query, params = self.encoder.encode_query(query)
        expected_query = "(t.f1 IS NOT NULL AND t.f2 IS NOT NULL)"
        expected_params = []
        self.assertEqual(sql_query, expected_query, "Multiple EXISTS query mismatch")
        self.assertEqual(params, expected_params, "Multiple EXISTS params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, f1, f2) VALUES (%s, %s, %s) RETURNING id",
            [(1, "v1", "v2"), (2, "v1", None), (3, None, "v2"), (4, None, None)],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, f1 TEXT, f2 TEXT);")
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
        print("\n-- Cleanup\nDROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [1], "Multiple EXISTS")

    def test_special_characters(self):
        query = TagQuery.eq(TagName("f1"), "val$ue")
        wql = query.to_wql_str()
        print(f"Test: Special characters query\nWQL: {wql}")
        sql_query, params = self.encoder.encode_query(query)
        expected_query = "t.f1 = %s"
        expected_params = ["val$ue"]
        self.assertEqual(sql_query, expected_query, "Special characters query mismatch")
        self.assertEqual(params, expected_params, "Special characters params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id, f1) VALUES (%s, %s) RETURNING id",
            [(1, "val$ue"), (2, "other"), (3, "val$ue")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, f1 TEXT);")
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
        print("\n-- Cleanup\nDROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [1, 3], "Special characters")


def main():
    print("Running PostgresTagEncoder tests (part B)...")
    unittest.main(argv=[""], exit=False)
    print("All tests completed.")


if __name__ == "__main__":
    main()
