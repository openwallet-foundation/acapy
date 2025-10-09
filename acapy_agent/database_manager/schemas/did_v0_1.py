"""Module docstring."""

CATEGORY = "did"

SCHEMAS = {
    "sqlite": [
        """
        CREATE TABLE IF NOT EXISTS did_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            method TEXT NOT NULL,
            verkey TEXT NOT NULL,
            verkey_type TEXT,
            epoch TEXT,
            metadata TEXT,
            endpoint TEXT GENERATED ALWAYS AS 
                (json_extract(metadata, '$.endpoint')) STORED,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT did_v0_1_unique_item_id UNIQUE (item_id)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_did_item_id_v0_1 ON did_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_did_did_id_v0_1 ON did_v0_1 (item_name);",
        """
        CREATE TRIGGER IF NOT EXISTS trg_update_did_timestamp_v0_1
        AFTER UPDATE ON did_v0_1
        FOR EACH ROW
        BEGIN
            UPDATE did_v0_1
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = OLD.id;
        END;
        """,
    ],
    "postgresql": [
        """
        CREATE TABLE IF NOT EXISTS did_v0_1 (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            method TEXT NOT NULL,
            verkey TEXT NOT NULL,
            verkey_type TEXT,
            epoch TEXT,
            metadata TEXT,
            endpoint TEXT GENERATED ALWAYS AS (
                jsonb_extract_path_text(metadata::jsonb, 'endpoint')
            ) STORED,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT did_v0_1_unique_item_id UNIQUE (item_id)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_did_item_id_v0_1 ON did_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_did_did_id_v0_1 ON did_v0_1 (item_name);",
        """
        CREATE OR REPLACE FUNCTION update_did_timestamp_v0_1()
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
        CREATE TRIGGER trg_update_did_timestamp_v0_1
        BEFORE UPDATE ON did_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION update_did_timestamp_v0_1();
        """,
    ],
    "mssql": [
        """
        CREATE TABLE did_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            item_id INT NOT NULL,
            item_name NVARCHAR(MAX) NOT NULL,
            method NVARCHAR(255) NOT NULL,
            verkey NVARCHAR(255) NOT NULL,
            verkey_type NVARCHAR(255),
            epoch NVARCHAR(50),
            metadata NVARCHAR(MAX),
            endpoint AS JSON_VALUE(metadata, '$.endpoint'),
            created_at DATETIME2 DEFAULT SYSDATETIME(),
            updated_at DATETIME2 DEFAULT SYSDATETIME(),
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT did_v0_1_unique_item_id UNIQUE (item_id)
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_did_item_id_v0_1 ON did_v0_1 (item_id);",
        "CREATE NONCLUSTERED INDEX idx_did_did_id_v0_1 ON did_v0_1 (item_name);",
        """
        CREATE TRIGGER trg_update_did_timestamp_v0_1
        ON did_v0_1
        AFTER UPDATE
        AS
        BEGIN
            UPDATE did_v0_1
            SET updated_at = SYSDATETIME()
            FROM did_v0_1
            INNER JOIN inserted ON did_v0_1.id = inserted.id
            WHERE inserted.updated_at IS NULL;
        END;
        """,
    ],
}

DROP_SCHEMAS = {
    "sqlite": [
        "DROP TRIGGER IF EXISTS trg_update_did_timestamp_v0_1;",
        "DROP INDEX IF EXISTS idx_did_did_id_v0_1;",
        "DROP INDEX IF EXISTS idx_did_item_id_v0_1;",
        "DROP TABLE IF EXISTS did_v0_1;",
    ],
    "postgresql": [
        "DROP TRIGGER IF EXISTS trg_update_did_timestamp_v0_1 ON did_v0_1;",
        "DROP FUNCTION IF EXISTS update_did_timestamp_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_did_did_id_v0_1;",
        "DROP INDEX IF EXISTS idx_did_item_id_v0_1;",
        "DROP TABLE IF EXISTS did_v0_1 CASCADE;",
    ],
    "mssql": [
        "DROP TRIGGER IF EXISTS trg_update_did_timestamp_v0_1;",
        "DROP INDEX IF EXISTS idx_did_did_id_v0_1 ON did_v0_1;",
        "DROP INDEX IF EXISTS idx_did_item_id_v0_1 ON did_v0_1;",
        "DROP TABLE IF EXISTS did_v0_1;",
    ],
}

COLUMNS = ["method", "verkey", "verkey_type", "epoch", "metadata"]

# category=did, name=did:peer:4zQmd7eCxTFjMLb9XFsmDqPXKKd862HusooDmJGKkg1HjGWM,
# value={"did": "did:peer:4zQmd7eCxTFjMLb9XFsmDqPXKKd862HusooDmJGKkg1HjGWM",
#        "method": "did:peer:4", "verkey": "Ge9ZwM26zcfkSRKT85VhqXtFYLLou56nuDoWBynEdfV3",
#        "verkey_type": "ed25519", "metadata": {}},
# tags={'method': 'did:peer:4', 'verkey': 'Ge9ZwM26zcfkSRKT85VhqXtFYLLou56nuDoWBynEdfV3',
#       'verkey_type': 'ed25519'}
