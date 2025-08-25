"""Module docstring."""


def migrate_sqlite(conn):
    """Migrate SQLite database from release 1.0 to 1.1."""
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_did_v1_name ON did_v1 (name)")
    conn.commit()
