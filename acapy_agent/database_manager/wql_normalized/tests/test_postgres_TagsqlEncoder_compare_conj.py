# pytest --maxfail=1 --disable-warnings --no-cov -s -vv acapy_agent/database_manager/wql_normalized/tests/test_postgres_TagsqlEncoder_compare_conj.py
# python -m unittest acapy_agent/database_manager/wql_normalized/tests/test_postgres_TagsqlEncoder_compare_conj.py

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
class TestPostgresTagEncoder(unittest.TestCase):
    """Test cases for the PostgresTagEncoder class in non-normalized mode."""

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

    def test_comparison_conjunction(self):
        """Test encoding a conjunction of comparison operations into a PostgreSQL statement."""
        query = TagQuery.and_(
            [
                TagQuery.eq(TagName("category"), "electronics"),
                TagQuery.gt(TagName("price"), "100"),
            ]
        )

        query_str, params = self.encoder.encode_query(query)
        print(f"encoded query_str is: {query_str}, params: {params}")

        # Expected SQL uses subqueries with %s placeholders
        expected_query = (
            "(i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value = %s) "
            "AND i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value > %s))"
        )
        expected_args = ["category", "electronics", "price", "100"]

        self.assertEqual(
            query_str, expected_query, "Comparison conjunction query mismatch"
        )
        self.assertEqual(params, expected_args, "Comparison conjunction params mismatch")

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
                (4, "category", "electronics"),
                (4, "price", "200"),
            ],
        )
        self.conn.commit()

        # Run query and verify
        select_query = f"SELECT id FROM items i WHERE {query_str}"
        self.cursor.execute(select_query, params)
        actual_ids = sorted([row[0] for row in self.cursor.fetchall()])
        expected_ids = [1, 4]
        self.assertEqual(
            actual_ids,
            expected_ids,
            f"Comparison conjunction failed: Expected IDs {expected_ids}, got {actual_ids}",
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
        print("    (4, 'category', 'electronics'),  -- Item 4: electronics, price=200")
        print("    (4, 'price', '200');")
        complete_select = replace_placeholders(select_query, params)
        print("\n-- Complete SELECT statement with values:")
        print(complete_select)
        print("\n-- Expected result: Items 1 and 4")
        print("\n-- Cleanup")
        print("DROP TABLE items_tags;")
        print("DROP TABLE items;")


if __name__ == "__main__":
    unittest.main()
