"""Module docstring."""

CATEGORY = "schema_sent"

IDX_ON_ITEM_ID = "ON schema_sent_v0_1 (item_id);"
IDX_ON_SCHEMA_ID = "ON schema_sent_v0_1 (schema_id);"

SCHEMAS = {
    "sqlite": [
        """
        CREATE TABLE IF NOT EXISTS schema_sent_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            schema_id TEXT NOT NULL,
            schema_issuer_did TEXT NOT NULL,
            schema_name TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            epoch TEXT NOT NULL,
            FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE,
            UNIQUE(item_id)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_schema_sent_item_id_v0_1 " + IDX_ON_ITEM_ID,
        "CREATE INDEX IF NOT EXISTS idx_schema_sent_schema_id_v0_1 " + IDX_ON_SCHEMA_ID,
    ],
    "postgresql": [
        """
        CREATE TABLE IF NOT EXISTS schema_sent_v0_1 (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            schema_id TEXT NOT NULL,
            schema_issuer_did TEXT NOT NULL,
            schema_name TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            epoch TEXT NOT NULL,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT schema_sent_v0_1_unique_item_id UNIQUE (item_id)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_schema_sent_item_id_v0_1 " + IDX_ON_ITEM_ID,
        "CREATE INDEX IF NOT EXISTS idx_schema_sent_schema_id_v0_1 " + IDX_ON_SCHEMA_ID,
    ],
    "mssql": [
        """
        CREATE TABLE schema_sent_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            item_id INT NOT NULL,
            item_name NVARCHAR(MAX) NOT NULL,
            schema_id NVARCHAR(255) NOT NULL,
            schema_issuer_did NVARCHAR(255) NOT NULL,
            schema_name NVARCHAR(MAX) NOT NULL,
            schema_version NVARCHAR(50) NOT NULL,
            epoch NVARCHAR(50) NOT NULL,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT schema_sent_v0_1_unique_item_id UNIQUE (item_id)
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_schema_sent_item_id_v0_1 " + IDX_ON_ITEM_ID,
        "CREATE NONCLUSTERED INDEX idx_schema_sent_schema_id_v0_1 " + IDX_ON_SCHEMA_ID,
    ],
}

DROP_SCHEMAS = {
    "sqlite": [
        "DROP INDEX IF EXISTS idx_schema_sent_schema_id_v0_1;",
        "DROP INDEX IF EXISTS idx_schema_sent_item_id_v0_1;",
        "DROP TABLE IF EXISTS schema_sent_v0_1;",
    ],
    "postgresql": [
        "DROP INDEX IF EXISTS idx_schema_sent_schema_id_v0_1;",
        "DROP INDEX IF EXISTS idx_schema_sent_item_id_v0_1;",
        "DROP TABLE IF EXISTS schema_sent_v0_1 CASCADE;",
    ],
    "mssql": [
        "DROP INDEX IF EXISTS idx_schema_sent_schema_id_v0_1 ON schema_sent_v0_1;",
        "DROP INDEX IF EXISTS idx_schema_sent_item_id_v0_1 ON schema_sent_v0_1;",
        "DROP TABLE IF EXISTS schema_sent_v0_1;",
    ],
}


COLUMNS = ["schema_id", "schema_issuer_did", "schema_name", "schema_version", "epoch"]
