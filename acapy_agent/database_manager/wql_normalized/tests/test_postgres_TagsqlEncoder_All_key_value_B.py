# pytest --maxfail=1 --disable-warnings --no-cov -s -vv acapy_agent/database_manager/wql_normalized/tests/test_postgres_TagsqlEncoder_All_key_value_B.py
# python -m unittest acapy_agent.database_manager.wql_normalized.tests.test_postgres_TagsqlEncoder_All_key_value_B -v

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
class TestPostgresTagEncoderNonNormalizedB(unittest.TestCase):
    """Test cases for the PostgresTagEncoder class in non-normalized mode (part B)."""

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
                user=parsed.username or "myuser",
                password=parsed.password or "mypass",
            )
            self.conn.autocommit = True  # Enable autocommit for setup/teardown
            self.cursor = self.conn.cursor()
            # Create tables for key-value pair structure
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS items_tags (
                    item_id INTEGER,
                    name TEXT,
                    value TEXT,
                    FOREIGN KEY(item_id) REFERENCES items(id)
                )
            """)
            logger.info("Tables 'items' and 'items_tags' created in setUp")
            self.encoder = encoder_factory.get_encoder(
                "postgresql", self.enc_name, self.enc_value, normalized=False
            )
        except Exception as e:
            logger.error(f"Failed to set up PostgreSQL database: {e}")
            raise

    def tearDown(self):
        """Clean up by dropping tables and closing the PostgreSQL connection."""
        try:
            self.cursor.execute("DROP TABLE IF EXISTS items_tags")
            self.cursor.execute("DROP TABLE IF EXISTS items")
            self.conn.commit()
            self.cursor.close()
            self.conn.close()
            logger.info("Tables dropped and PostgreSQL connection closed in tearDown")
        except Exception as e:
            logger.error(f"Failed to tear down PostgreSQL connection: {e}")
            raise

    def run_query_and_verify(self, sql_query, params, expected_ids, test_name):
        """Run a PostgreSQL query and verify results."""
        try:
            query = sql_query[0] if isinstance(sql_query, tuple) else sql_query
            self.cursor.execute(f"SELECT i.id FROM items i WHERE {query}", params)
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

    def test_in_positive(self):
        query = TagQuery.in_(TagName("field"), ["a", "b"])
        wql = query.to_wql_str()
        print(f"Test: Positive IN query\nWQL: {wql}")
        sql_query, params = self.encoder.encode_query(query)
        expected_query = "i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value IN (%s, %s))"
        expected_params = ["field", "a", "b"]
        self.assertEqual(sql_query, expected_query, "Positive IN query mismatch")
        self.assertEqual(params, expected_params, "Positive IN params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (%s) RETURNING id", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (%s, %s, %s)",
            [(1, "field", "a"), (2, "field", "b"), (3, "field", "c"), (4, "field", "a")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY);")
        print(
            "CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT, FOREIGN KEY(item_id) REFERENCES items(id));"
        )
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'field', 'a'), "
            "(2, 'field', 'b'), "
            "(3, 'field', 'c'), "
            "(4, 'field', 'a');"
        )
        select_query = f"SELECT id FROM items i WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 2, 4")
        print("\n-- Cleanup\nDROP TABLE items_tags; DROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [1, 2, 4], "Positive IN")

    def test_in_negated(self):
        query = TagQuery.not_(TagQuery.in_(TagName("field"), ["a", "b"]))
        wql = query.to_wql_str()
        print(f"Test: Negated IN query\nWQL: {wql}")
        sql_query, params = self.encoder.encode_query(query)
        expected_query = "i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value NOT IN (%s, %s))"
        expected_params = ["field", "a", "b"]
        self.assertEqual(sql_query, expected_query, "Negated IN query mismatch")
        self.assertEqual(params, expected_params, "Negated IN params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (%s) RETURNING id", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (%s, %s, %s)",
            [(1, "field", "a"), (2, "field", "b"), (3, "field", "c"), (4, "field", "d")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY);")
        print(
            "CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT, FOREIGN KEY(item_id) REFERENCES items(id));"
        )
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'field', 'a'), "
            "(2, 'field', 'b'), "
            "(3, 'field', 'c'), "
            "(4, 'field', 'd');"
        )
        select_query = f"SELECT id FROM items i WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 3, 4")
        print("\n-- Cleanup\nDROP TABLE items_tags; DROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [3, 4], "Negated IN")

    def test_exist_positive(self):
        query = TagQuery.exist([TagName("field")])
        wql = query.to_wql_str()
        print(f"Test: Positive EXIST query\nWQL: {wql}")
        sql_query, params = self.encoder.encode_query(query)
        expected_query = "i.id IN (SELECT item_id FROM items_tags WHERE name = %s)"
        expected_params = ["field"]
        self.assertEqual(sql_query, expected_query, "Positive EXIST query mismatch")
        self.assertEqual(params, expected_params, "Positive EXIST params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (%s) RETURNING id", [(1,), (2,), (3,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (%s, %s, %s)",
            [(1, "field", "value"), (3, "field", "another")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY);")
        print(
            "CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT, FOREIGN KEY(item_id) REFERENCES items(id));"
        )
        print("INSERT INTO items (id) VALUES (1), (2), (3);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'field', 'value'), "
            "(3, 'field', 'another');"
        )
        select_query = f"SELECT id FROM items i WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 3")
        print("\n-- Cleanup\nDROP TABLE items_tags; DROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [1, 3], "Positive EXIST")

    def test_exist_negated(self):
        query = TagQuery.not_(TagQuery.exist([TagName("field")]))
        wql = query.to_wql_str()
        print(f"Test: Negated EXIST query\nWQL: {wql}")
        sql_query, params = self.encoder.encode_query(query)
        expected_query = "i.id NOT IN (SELECT item_id FROM items_tags WHERE name = %s)"
        expected_params = ["field"]
        self.assertEqual(sql_query, expected_query, "Negated EXIST query mismatch")
        self.assertEqual(params, expected_params, "Negated EXIST params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (%s) RETURNING id", [(1,), (2,), (3,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (%s, %s, %s)",
            [(1, "field", "value"), (3, "field", "another")],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY);")
        print(
            "CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT, FOREIGN KEY(item_id) REFERENCES items(id));"
        )
        print("INSERT INTO items (id) VALUES (1), (2), (3);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'field', 'value'), "
            "(3, 'field', 'another');"
        )
        select_query = f"SELECT id FROM items i WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Item 2")
        print("\n-- Cleanup\nDROP TABLE items_tags; DROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [2], "Negated EXIST")

    def test_and_multiple(self):
        query = TagQuery.and_(
            [TagQuery.eq(TagName("f1"), "v1"), TagQuery.gt(TagName("f2"), "10")]
        )
        wql = query.to_wql_str()
        print(f"Test: AND query with multiple subqueries\nWQL: {wql}")
        sql_query, params = self.encoder.encode_query(query)
        expected_query = "(i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value = %s) AND i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value > %s))"
        expected_params = ["f1", "v1", "f2", "10"]
        self.assertEqual(sql_query, expected_query, "AND multiple query mismatch")
        self.assertEqual(params, expected_params, "AND multiple params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (%s) RETURNING id", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (%s, %s, %s)",
            [
                (1, "f1", "v1"),
                (1, "f2", "15"),
                (2, "f1", "v1"),
                (2, "f2", "05"),
                (3, "f1", "v2"),
                (3, "f2", "15"),
                (4, "f1", "v1"),
                (4, "f2", "20"),
            ],
        )
        self.conn.commit()
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY);")
        print(
            "CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT, FOREIGN KEY(item_id) REFERENCES items(id));"
        )
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'f1', 'v1'), (1, 'f2', '15'), "
            "(2, 'f1', 'v1'), (2, 'f2', '05'), "
            "(3, 'f1', 'v2'), (3, 'f2', '15'), "
            "(4, 'f1', 'v1'), (4, 'f2', '20');"
        )
        select_query = f"SELECT id FROM items i WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 4")
        print("\n-- Cleanup\nDROP TABLE items_tags; DROP TABLE items;")
        self.run_query_and_verify(sql_query, params, [1, 4], "AND multiple")

    def test_or_multiple(self):
        query = TagQuery.or_(
            [TagQuery.eq(TagName("f1"), "v1"), TagQuery.gt(TagName("f2"), "10")]
        )
        wql = query.to_wql_str()
        print(f"Test: OR query with multiple subqueries\nWQL: {wql}")
        sql_query, params = self.encoder.encode_query(query)
        expected_query = "(i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value = %s) OR i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value > %s))"
        expected_params = ["f1", "v1", "f2", "10"]
        self.assertEqual(sql_query, expected_query, "OR multiple query mismatch")
        self.assertEqual(params, expected_params, "OR multiple params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (%s) RETURNING id", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (%s, %s, %s)",
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
        print("CREATE TABLE items (id SERIAL PRIMARY KEY);")
        print(
            "CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT, FOREIGN KEY(item_id) REFERENCES items(id));"
        )
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'f1', 'v1'), (1, 'f2', '15'), "
            "(2, 'f1', 'v1'), (2, 'f2', '05'), "
            "(3, 'f1', 'v2'), (3, 'f2', '15'), "
            "(4, 'f1', 'v2'), (4, 'f2', '05');"
        )
        select_query = f"SELECT id FROM items i WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 2, 3")
        print("\n-- Cleanup\nDROP TABLE items_tags; DROP TABLE items;")
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
        expected_query = "(i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value = %s) AND (i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value > %s) OR i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value < %s)))"
        expected_params = ["f1", "v1", "f2", "10", "f3", "5"]
        self.assertEqual(sql_query, expected_query, "Nested AND/OR query mismatch")
        self.assertEqual(params, expected_params, "Nested AND/OR params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (%s) RETURNING id", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (%s, %s, %s)",
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
        print("CREATE TABLE items (id SERIAL PRIMARY KEY);")
        print(
            "CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT, FOREIGN KEY(item_id) REFERENCES items(id));"
        )
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'f1', 'v1'), (1, 'f2', '15'), (1, 'f3', '3'), "
            "(2, 'f1', 'v1'), (2, 'f2', '05'), (2, 'f3', '4'), "
            "(3, 'f1', 'v2'), (3, 'f2', '15'), (3, 'f3', '3'), "
            "(4, 'f1', 'v1'), (4, 'f2', '05'), (4, 'f3', '6');"
        )
        select_query = f"SELECT id FROM items i WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 2")
        print("\n-- Cleanup\nDROP TABLE items_tags; DROP TABLE items;")
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
        expected_query = "(i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value = %s) AND i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value > %s))"
        expected_params = ["category", "electronics", "price", "100"]
        self.assertEqual(
            sql_query, expected_query, "Comparison conjunction query mismatch"
        )
        self.assertEqual(
            params, expected_params, "Comparison conjunction params mismatch"
        )
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (%s) RETURNING id", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (%s, %s, %s)",
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
        print("CREATE TABLE items (id SERIAL PRIMARY KEY);")
        print(
            "CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT, FOREIGN KEY(item_id) REFERENCES items(id));"
        )
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'category', 'electronics'), (1, 'price', '150'), "
            "(2, 'category', 'electronics'), (2, 'price', '090'), "
            "(3, 'category', 'books'), (3, 'price', '120'), "
            "(4, 'category', 'electronics'), (4, 'price', '200');"
        )
        select_query = f"SELECT id FROM items i WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Items 1, 4")
        print("\n-- Cleanup\nDROP TABLE items_tags; DROP TABLE items;")
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
        expected_query = "NOT ((i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value = %s) OR i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value = %s)) AND i.id NOT IN (SELECT item_id FROM items_tags WHERE name = %s AND value = %s))"
        expected_params = ["category", "electronics", "sale", "yes", "stock", "out"]
        self.assertEqual(sql_query, expected_query, "Deeply nested NOT query mismatch")
        self.assertEqual(params, expected_params, "Deeply nested NOT params mismatch")
        self.verify_round_trip(query, sql_query, params)
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (%s) RETURNING id", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (%s, %s, %s)",
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
        print("CREATE TABLE items (id SERIAL PRIMARY KEY);")
        print(
            "CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT, FOREIGN KEY(item_id) REFERENCES items(id));"
        )
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print(
            "INSERT INTO items_tags (item_id, name, value) VALUES "
            "(1, 'category', 'electronics'), (1, 'stock', 'in'), "
            "(2, 'category', 'electronics'), (2, 'stock', 'out'), "
            "(3, 'sale', 'yes'), (3, 'stock', 'in'), "
            "(4, 'sale', 'yes');"
        )
        select_query = f"SELECT id FROM items i WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print("\n-- Expected result: Item 2")
        print("\n-- Cleanup\nDROP TABLE items_tags; DROP TABLE items;")
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
        expected_query = "NOT (i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value = %s) AND (i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value > %s) OR i.id NOT IN (SELECT item_id FROM items_tags WHERE name = %s AND value <= %s) OR (i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value < %s) AND i.id NOT IN (SELECT item_id FROM items_tags WHERE name = %s AND value >= %s))) AND i.id NOT IN (SELECT item_id FROM items_tags WHERE name = %s AND value LIKE %s) AND (i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value = %s) AND i.id NOT IN (SELECT item_id FROM items_tags WHERE name = %s AND value != %s)))"
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
            "INSERT INTO items (id) VALUES (%s) RETURNING id",
            [(1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,), (10,), (11,), (12,)],
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (%s, %s, %s)",
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
        print("CREATE TABLE items (id SERIAL PRIMARY KEY);")
        print(
            "CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT, FOREIGN KEY(item_id) REFERENCES items(id));"
        )
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
        select_query = f"SELECT id FROM items i WHERE {sql_query}"
        complete_sql = replace_placeholders(select_query, params)
        print(f"\n-- Complete SELECT statement with values:\n{complete_sql}")
        print(f"\n-- Expected result: Items {expected_ids}")
        print("\n-- Cleanup\nDROP TABLE items_tags; DROP TABLE items;")
        self.run_query_and_verify(
            sql_query, params, expected_ids, "Complex AND/OR/NOT query"
        )


def main():
    print("Running PostgresTagEncoder non-normalized tests (part B)...")
    unittest.main(argv=[""], exit=False)
    print("All tests completed.")


if __name__ == "__main__":
    main()
