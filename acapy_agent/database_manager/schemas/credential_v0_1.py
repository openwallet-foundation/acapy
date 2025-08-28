"""Module docstring."""

CATEGORY = "credential"

IDX_CRED_ON_ITEM_ID = "ON credential_record_v0_1 (item_id);"
IDX_CRED_ON_NAME = "ON credential_record_v0_1 (name);"
IDX_CRED_ON_VALUE = "ON credential_record_v0_1 (value);"

SCHEMAS = {
    "sqlite": [
        """
        CREATE TABLE IF NOT EXISTS credential_record_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            value TEXT,
            FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_credential_record_item_id_v0_1 "
        + IDX_CRED_ON_ITEM_ID,
        "CREATE INDEX IF NOT EXISTS idx_credential_record_item_name_v0_1 "
        + IDX_CRED_ON_NAME,
        "CREATE INDEX IF NOT EXISTS idx_credential_record_value_v0_1 "
        + IDX_CRED_ON_VALUE,
    ],
    "postgresql": [
        """
        CREATE TABLE IF NOT EXISTS credential_record_v0_1 (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            value TEXT,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) 
            REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_credential_record_item_id_v0_1 "
        + IDX_CRED_ON_ITEM_ID,
        "CREATE INDEX IF NOT EXISTS idx_credential_record_item_name_v0_1 "
        + IDX_CRED_ON_NAME,
        "CREATE INDEX IF NOT EXISTS idx_credential_record_value_v0_1 "
        + IDX_CRED_ON_VALUE,
    ],
    "mssql": [
        """
        CREATE TABLE credential_record_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            item_id INT NOT NULL,
            name NVARCHAR(MAX) NOT NULL,
            value NVARCHAR(MAX),
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) 
            REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_credential_record_item_id_v0_1 "
        + IDX_CRED_ON_ITEM_ID,
        "CREATE NONCLUSTERED INDEX idx_credential_record_item_name_v0_1 "
        + IDX_CRED_ON_NAME,
        "CREATE NONCLUSTERED INDEX idx_credential_record_value_v0_1 " + IDX_CRED_ON_VALUE,
    ],
}

DROP_SCHEMAS = {
    "sqlite": [
        "DROP INDEX IF EXISTS idx_credential_record_value_v0_1;",
        "DROP INDEX IF EXISTS idx_credential_record_item_name_v0_1;",
        "DROP INDEX IF EXISTS idx_credential_record_item_id_v0_1;",
        "DROP TABLE IF EXISTS credential_record_v0_1;",
    ],
    "postgresql": [
        "DROP INDEX IF EXISTS idx_credential_record_value_v0_1;",
        "DROP INDEX IF EXISTS idx_credential_record_item_name_v0_1;",
        "DROP INDEX IF EXISTS idx_credential_record_item_id_v0_1;",
        "DROP TABLE IF EXISTS credential_record_v0_1 CASCADE;",
    ],
    "mssql": [
        "DROP INDEX IF EXISTS idx_credential_record_value_v0_1 "
        "ON credential_record_v0_1;",
        "DROP INDEX IF EXISTS idx_credential_record_item_name_v0_1 "
        "ON credential_record_v0_1;",
        "DROP INDEX IF EXISTS idx_credential_record_item_id_v0_1 "
        "ON credential_record_v0_1;",
        "DROP TABLE IF EXISTS credential_record_v0_1;",
    ],
}

COLUMNS = ["name", "value"]
