# pytest --maxfail=1 --disable-warnings --no-cov -s -vv acapy_agent/database_manager/wql_normalized/tests/test_postgres_TagsqlEncoder_negate_conj.py
# python -m unittest acapy_agent/database_manager/wql_normalized/tests/test_postgres_TagsqlEncoder_negate_conj.py


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
class TestPostgresTagEncoderNegateConj(unittest.TestCase):
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

    def test_negate_conj(self):
        """Test encoding a negated conjunction TagQuery into a PostgreSQL statement."""
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

        query_str, params = self.encoder.encode_query(query)
        print(f"encoded query_str is: {query_str}, params: {params}")

        expected_query = (
            "NOT ((i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value = %s) "
            "AND i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value = %s)) "
            "OR (i.id IN (SELECT item_id FROM items_tags WHERE name = %s AND value = %s) "
            "AND i.id NOT IN (SELECT item_id FROM items_tags WHERE name = %s AND value = %s)))"
        )
        expected_args = [
            "category",
            "electronics",  # From condition_1: category = electronics
            "status",
            "in_stock",  # From condition_1: status = in_stock
            "category",
            "electronics",  # From condition_2: category = electronics
            "status",
            "sold_out",  # From condition_2: NOT (status = sold_out)
        ]

        self.assertEqual(query_str, expected_query, "Negated conjunction query mismatch")
        self.assertEqual(params, expected_args, "Negated conjunction params mismatch")

        # Setup database for verification
        self.cursor.executemany(
            "INSERT INTO items (id) VALUES (%s) RETURNING id", [(1,), (2,), (3,), (4,)]
        )
        self.cursor.executemany(
            "INSERT INTO items_tags (item_id, name, value) VALUES (%s, %s, %s)",
            [
                (1, "category", "electronics"),
                (1, "status", "in_stock"),
                (2, "category", "electronics"),
                (2, "status", "sold_out"),
                (3, "category", "books"),
                (3, "status", "in_stock"),
                (4, "category", "clothing"),
            ],
        )
        self.conn.commit()

        # Run query and verify
        self.run_query_and_verify(query_str, params, [2, 3, 4], "Negated conjunction")

        # Print complete SQL statements for copying and running
        print("\n### Complete SQL Statements for Testing")
        print("CREATE TABLE items (id SERIAL PRIMARY KEY);")
        print(
            "CREATE TABLE items_tags (item_id INTEGER, name TEXT, value TEXT, FOREIGN KEY(item_id) REFERENCES items(id));"
        )
        print("INSERT INTO items (id) VALUES (1), (2), (3), (4);")
        print("INSERT INTO items_tags (item_id, name, value) VALUES")
        print("    (1, 'category', 'electronics'),  -- Item 1: electronics, in_stock")
        print("    (1, 'status', 'in_stock'),")
        print("    (2, 'category', 'electronics'),  -- Item 2: electronics, sold_out")
        print("    (2, 'status', 'sold_out'),")
        print("    (3, 'category', 'books'),        -- Item 3: books, in_stock")
        print("    (3, 'status', 'in_stock'),")
        print("    (4, 'category', 'clothing');     -- Item 4: clothing, no status")
        select_query = f"SELECT id FROM items i WHERE {query_str}"
        complete_select = replace_placeholders(select_query, params)
        print("\n-- Complete SELECT statement with values:")
        print(complete_select)
        print("\n-- Expected result: Items 2, 3 and 4")
        print("\n-- Cleanup")
        print("DROP TABLE items_tags;")
        print("DROP TABLE items;")


if __name__ == "__main__":
    unittest.main()
