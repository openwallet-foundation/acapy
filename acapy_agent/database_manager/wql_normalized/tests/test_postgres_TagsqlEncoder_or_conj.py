# pytest --maxfail=1 --disable-warnings --no-cov -s -vv acapy_agent/database_manager/wql_normalized/tests/test_postgres_TagsqlEncoder_or_conj.py
# python -m unittest acapy_agent/database_manager/wql_normalized/tests/test_postgres_TagsqlEncoder_or_conj.py

import logging
import os
import unittest

import psycopg
import pytest

from acapy_agent.database_manager.wql_normalized.encoders import encoder_factory
from acapy_agent.database_manager.wql_normalized.tags import TagName, TagQuery

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
class TestPostgresTagEncoderOrConj(unittest.TestCase):
    """Test cases for the PostgresTagEncoder class with OR conjunction queries."""

    def setUp(self):
        """Set up PostgreSQL database connection and encoders for both modes."""
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
            # Create tables for both normalized and non-normalized modes
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY,
                    category TEXT,
                    price TEXT
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
            self.normalized_encoder = encoder_factory.get_encoder(
                "postgresql", self.enc_name, self.enc_value, normalized=True
            )
            self.non_normalized_encoder = encoder_factory.get_encoder(
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

    def run_query_and_verify(
        self, sql_query, params, expected_ids, test_name, table_alias="t"
    ):
        """Run a PostgreSQL query and verify results."""
        try:
            query = sql_query[0] if isinstance(sql_query, tuple) else sql_query
            select_query = f"SELECT id FROM items AS {table_alias} WHERE {query}"
            self.cursor.execute(select_query, params)
            actual_ids = sorted([row[0] for row in self.cursor.fetchall()])
            self.assertEqual(
                actual_ids,
                expected_ids,
                f"{test_name} failed: Expected IDs {expected_ids}, got {actual_ids}",
            )
        except Exception as e:
            logger.error(f"Query execution failed in {test_name}: {e}")
            raise

    def test_or_conjunction_normalized(self):
        """Test encoding an OR conjunction in normalized mode."""
        query = TagQuery.or_(
            [
                TagQuery.eq(TagName("category"), "electronics"),
                TagQuery.gt(TagName("price"), "100"),
            ]
        )

        query_str, params = self.normalized_encoder.encode_query(query)
        print(
            f"Test: OR conjunction (normalized)\nencoded query_str is: {query_str}, params: {params}"
        )

        expected_query = "(t.category = %s OR t.price > %s)"
        expected_args = ["electronics", "100"]

        self.assertEqual(
            query_str, expected_query, "OR conjunction normalized query mismatch"
        )
        self.assertEqual(
            params, expected_args, "OR conjunction normalized params mismatch"
        )

        # Insert test data
        self.cursor.executemany(
            "INSERT INTO items (id, category, price) VALUES (%s, %s, %s) RETURNING id",
            [
                (1, "electronics", "150"),
                (2, "electronics", "090"),
                (3, "books", "120"),
                (4, "clothing", "200"),
            ],
        )
        self.conn.commit()

        # Run query and verify
        self.run_query_and_verify(
            query_str, params, [1, 2, 3, 4], "OR conjunction normalized"
        )

        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY, category TEXT, price TEXT);")
        print(
            "INSERT INTO items (id, category, price) VALUES "
            "(1, 'electronics', '150'), "
            "(2, 'electronics', '090'), "
            "(3, 'books', '120'), "
            "(4, 'clothing', '200');"
        )
        select_query = f"SELECT id FROM items AS t WHERE {query_str}"
        complete_select = replace_placeholders(select_query, params)
        print("\n-- Complete SELECT statement with values:")
        print(complete_select)
        print("\n-- Expected result: Items 1, 2, 3, 4")
        print("\n-- Cleanup")
        print("DROP TABLE items;")

    def test_or_conjunction_non_normalized(self):
        """Test encoding an OR conjunction in non-normalized mode."""
        query = TagQuery.or_(
            [
                TagQuery.eq(TagName("category"), "electronics"),
                TagQuery.gt(TagName("price"), "100"),
            ]
        )

        query_str, params = self.non_normalized_encoder.encode_query(query)
        print(
            f"Test: OR conjunction (non-normalized)\nencoded query_str is: {query_str}, params: {params}"
        )

        expected_query = (
            "(i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value = %s) "
            "OR i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value > %s))"
        )
        expected_args = ["category", "electronics", "price", "100"]

        self.assertEqual(
            query_str, expected_query, "OR conjunction non-normalized query mismatch"
        )
        self.assertEqual(
            params, expected_args, "OR conjunction non-normalized params mismatch"
        )

        # Insert test data
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
                (4, "category", "clothing"),
                (4, "price", "200"),
            ],
        )
        self.conn.commit()

        # Run query and verify
        self.run_query_and_verify(
            query_str,
            params,
            [1, 2, 3, 4],
            "OR conjunction non-normalized",
            table_alias="i",
        )

        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY);")
        print(
            "CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT, FOREIGN KEY(item_id) REFERENCES items(id));"
        )
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print("INSERT INTO items_tags (item_id, name, value) VALUES")
        print("    (1, 'category', 'electronics'),  -- Item 1: electronics, price=150")
        print("    (1, 'price', '150'),")
        print("    (2, 'category', 'electronics'),  -- Item 2: electronics, price=090")
        print("    (2, 'price', '090'),")
        print("    (3, 'category', 'books'),        -- Item 3: books, price=120")
        print("    (3, 'price', '120'),")
        print("    (4, 'category', 'clothing'),     -- Item 4: clothing, price=200")
        print("    (4, 'price', '200');")
        select_query = f"SELECT id FROM items AS i WHERE {query_str}"
        complete_select = replace_placeholders(select_query, params)
        print("\n-- Complete SELECT statement with values:")
        print(complete_select)
        print("\n-- Expected result: Items 1, 2, 3, 4")
        print("\n-- Cleanup")
        print("DROP TABLE items_tags;")
        print("DROP TABLE items;")


if __name__ == "__main__":
    unittest.main()
