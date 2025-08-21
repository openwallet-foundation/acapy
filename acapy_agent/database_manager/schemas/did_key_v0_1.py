"""Module docstring."""

CATEGORY = "did_key"

SCHEMAS = {
    "sqlite": [
        """
        CREATE TABLE IF NOT EXISTS did_key_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            did TEXT,
            key TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_did_key_item_id_v0_1 ON did_key_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_did_key_did_v0_1 ON did_key_v0_1 (did);",
        """
        CREATE TRIGGER IF NOT EXISTS trg_update_did_key_timestamp_v0_1
        AFTER UPDATE ON did_key_v0_1
        FOR EACH ROW
        BEGIN
            UPDATE did_key_v0_1
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = OLD.id;
        END;
        """,
    ],
    "postgresql": [
        """
        CREATE TABLE IF NOT EXISTS did_key_v0_1 (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            did TEXT,
            key TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_did_key_item_id_v0_1 ON did_key_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_did_key_did_v0_1 ON did_key_v0_1 (did);",
        """
        CREATE OR REPLACE FUNCTION update_did_key_timestamp_v0_1()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.updated_at IS NULL THEN
                NEW.updated_at = CURRENT_TIMESTAMP;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        CREATE TRIGGER trg_update_did_key_timestamp_v0_1
        BEFORE UPDATE ON did_key_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION update_did_key_timestamp_v0_1();
        """,
    ],
    "mssql": [
        """
        CREATE TABLE did_key_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            item_id INT NOT NULL,
            item_name NVARCHAR(MAX) NOT NULL,
            did NVARCHAR(255),
            key NVARCHAR(MAX),
            created_at DATETIME2 DEFAULT SYSDATETIME(),
            updated_at DATETIME2 DEFAULT SYSDATETIME(),
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_did_key_item_id_v0_1 ON did_key_v0_1 (item_id);",
        "CREATE NONCLUSTERED INDEX idx_did_key_did_v0_1 ON did_key_v0_1 (did);",
        """
        CREATE TRIGGER trg_update_did_key_timestamp_v0_1
        ON did_key_v0_1
        AFTER UPDATE
        AS
        BEGIN
            UPDATE did_key_v0_1
            SET updated_at = SYSDATETIME()
            FROM did_key_v0_1
            INNER JOIN inserted ON did_key_v0_1.id = inserted.id
            WHERE inserted.updated_at IS NULL;
        END;
        """,
    ],
}

DROP_SCHEMAS = {
    "sqlite": [
        "DROP TRIGGER IF EXISTS trg_update_did_key_timestamp_v0_1;",
        "DROP INDEX IF EXISTS idx_did_key_did_v0_1;",
        "DROP INDEX IF EXISTS idx_did_key_item_id_v0_1;",
        "DROP TABLE IF EXISTS did_key_v0_1;",
    ],
    "postgresql": [
        "DROP TRIGGER IF EXISTS trg_update_did_key_timestamp_v0_1 ON did_key_v0_1;",
        "DROP FUNCTION IF EXISTS update_did_key_timestamp_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_did_key_did_v0_1;",
        "DROP INDEX IF EXISTS idx_did_key_item_id_v0_1;",
        "DROP TABLE IF EXISTS did_key_v0_1 CASCADE;",
    ],
    "mssql": [
        "DROP TRIGGER IF EXISTS trg_update_did_key_timestamp_v0_1;",
        "DROP INDEX IF EXISTS idx_did_key_did_v0_1 ON did_key_v0_1;",
        "DROP INDEX IF EXISTS idx_did_key_item_id_v0_1 ON did_key_v0_1;",
        "DROP TABLE IF EXISTS did_key_v0_1;",
    ],
}

COLUMNS = ["did", "key", "created_at", "updated_at"]

# sample
# category=did_key, name=6e91cade598d4440b1d6becfab997914,
# value=2UFCSELfEF7tsBLJU5uhnDAyhDxe1vgaWqJiyBDhXvAx
# tags={'did': '3hQMdP4sNb1iQKN1L1VqLe',
#       'key': '2UFCSELfEF7tsBLJU5uhnDAyhDxe1vgaWqJiyBDhXvAx'}
