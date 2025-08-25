"""Module docstring."""


def migrate_sqlite(conn, category="anoncreds_cred_ex_v20"):
    """Migrate SQLite anoncreds_cred_ex_v20 schema from v1 to v2.

    Example: Add a new_field column.
    """
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE anoncreds_cred_ex_v20_v1 ADD COLUMN new_field TEXT")
        cursor.execute("UPDATE anoncreds_cred_ex_v20_v1 SET new_field = 'default'")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise Exception(f"SQLite migration failed for {category}: {str(e)}")


def migrate_postgresql(conn, category="anoncreds_cred_ex_v20"):
    """Migrate PostgreSQL anoncreds_cred_ex_v20 schema from v1 to v2.

    Example: Add a new_field column.
    """
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE anoncreds_cred_ex_v20_v1 ADD COLUMN new_field TEXT")
        cursor.execute("UPDATE anoncreds_cred_ex_v20_v1 SET new_field = 'default'")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise Exception(f"PostgreSQL migration failed for {category}: {str(e)}")


def migrate_mssql(conn, category="anoncreds_cred_ex_v20"):
    """Migrate MSSQL anoncreds_cred_ex_v20 schema from v1 to v2.

    Example: Add a new_field column.
    """
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE anoncreds_cred_ex_v20_v1 ADD new_field NVARCHAR(255)")
        cursor.execute("UPDATE anoncreds_cred_ex_v20_v1 SET new_field = 'default'")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise Exception(f"MSSQL migration failed for {category}: {str(e)}")
