def migrate_sqlite(conn):
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_did_v1_name ON did_v1 (name)")
    conn.commit()
