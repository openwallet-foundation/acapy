"""Module docstring."""

CATEGORY = "cred_def_sent"

IDX_CRED_DEF_SENT_ON_ITEM_ID = "ON cred_def_sent_v0_1 (item_id);"
IDX_CRED_DEF_SENT_ON_SCHEMA_ID = "ON cred_def_sent_v0_1 (schema_id);"

SCHEMAS = {
    "sqlite": [
        """
        CREATE TABLE IF NOT EXISTS cred_def_sent_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            item_name TEXT,
            schema_id TEXT,
            cred_def_id TEXT,
            schema_issuer_did TEXT,
            schema_name TEXT,
            schema_version TEXT,
            issuer_did TEXT,
            epoch TEXT,
            meta_data TEXT,
            FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT cred_def_sent_v0_1_unique_item_id UNIQUE (item_id)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_cred_def_sent_item_id_v0_1 "
        + IDX_CRED_DEF_SENT_ON_ITEM_ID,
        "CREATE INDEX IF NOT EXISTS idx_cred_def_sent_schema_id_v0_1 "
        + IDX_CRED_DEF_SENT_ON_SCHEMA_ID,
    ],
    "postgresql": [
        """
        CREATE TABLE IF NOT EXISTS cred_def_sent_v0_1 (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            item_name TEXT,
            schema_id TEXT,
            cred_def_id TEXT,
            schema_issuer_did TEXT,
            schema_name TEXT,
            schema_version TEXT,
            issuer_did TEXT,
            epoch TEXT,
            meta_data TEXT,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT cred_def_sent_v0_1_unique_item_id UNIQUE (item_id)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_cred_def_sent_item_id_v0_1 "
        + IDX_CRED_DEF_SENT_ON_ITEM_ID,
        "CREATE INDEX IF NOT EXISTS idx_cred_def_sent_schema_id_v0_1 "
        + IDX_CRED_DEF_SENT_ON_SCHEMA_ID,
    ],
    "mssql": [
        """
        CREATE TABLE cred_def_sent_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            item_id INT NOT NULL,
            item_name NVARCHAR(MAX),
            schema_id NVARCHAR(255),
            cred_def_id NVARCHAR(255),
            schema_issuer_did NVARCHAR(255),
            schema_name NVARCHAR(MAX),
            schema_version NVARCHAR(50),
            issuer_did NVARCHAR(255),
            epoch NVARCHAR(50),
            meta_data NVARCHAR(MAX),
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT cred_def_sent_v0_1_unique_item_id UNIQUE (item_id)
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_cred_def_sent_item_id_v0_1 "
        + IDX_CRED_DEF_SENT_ON_ITEM_ID,
        "CREATE NONCLUSTERED INDEX idx_cred_def_sent_schema_id_v0_1 "
        + IDX_CRED_DEF_SENT_ON_SCHEMA_ID,
    ],
}


DROP_SCHEMAS = {
    "sqlite": [
        "DROP INDEX IF EXISTS idx_cred_def_sent_schema_id_v0_1;",
        "DROP INDEX IF EXISTS idx_cred_def_sent_item_id_v0_1;",
        "DROP TABLE IF EXISTS cred_def_sent_v0_1;",
    ],
    "postgresql": [
        "DROP INDEX IF EXISTS idx_cred_def_sent_schema_id_v0_1;",
        "DROP INDEX IF EXISTS idx_cred_def_sent_item_id_v0_1;",
        "DROP TABLE IF EXISTS cred_def_sent_v0_1 CASCADE;",
    ],
    "mssql": [
        "DROP INDEX IF EXISTS idx_cred_def_sent_schema_id_v0_1 ON cred_def_sent_v0_1;",
        "DROP INDEX IF EXISTS idx_cred_def_sent_item_id_v0_1 ON cred_def_sent_v0_1;",
        "DROP TABLE IF EXISTS cred_def_sent_v0_1;",
    ],
}


COLUMNS = [
    "schema_id",
    "schema_issuer_did",
    "cred_def_id",
    "schema_name",
    "schema_version",
    "issuer_did",
    "meta_data",
]
