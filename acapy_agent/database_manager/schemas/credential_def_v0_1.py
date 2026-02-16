"""Module docstring."""

CATEGORY = "credential_def"

IDX_CRED_DEF_ON_ITEM_ID = "ON credential_def_v0_1 (item_id);"
IDX_CRED_DEF_ON_SCHEMA_ID = "ON credential_def_v0_1 (schema_id);"
IDX_CRED_DEF_ON_ISSUER_ID = "ON credential_def_v0_1 (issuer_id);"

SCHEMAS = {
    "sqlite": [
        """
        CREATE TABLE IF NOT EXISTS credential_def_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            item_name TEXT,
            schema_id TEXT NOT NULL,
            schema_issuer_id TEXT,
            issuer_id TEXT,
            schema_name TEXT,
            tag TEXT,
            state TEXT,
            schema_version TEXT,
            epoch TEXT,
            support_revocation INTEGER,
            max_cred_num INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT credential_def_v0_1_unique_item_id UNIQUE (item_id)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_credential_def_item_id_v0_1 "
        + IDX_CRED_DEF_ON_ITEM_ID,
        "CREATE INDEX IF NOT EXISTS idx_credential_def_schema_id_v0_1 "
        + IDX_CRED_DEF_ON_SCHEMA_ID,
        "CREATE INDEX IF NOT EXISTS idx_credential_def_issuer_did_v0_1 "
        + IDX_CRED_DEF_ON_ISSUER_ID,
        """
        CREATE TRIGGER IF NOT EXISTS trg_update_credential_def_timestamp_v0_1
        AFTER UPDATE ON credential_def_v0_1
        FOR EACH ROW
        BEGIN
            UPDATE credential_def_v0_1
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = OLD.id;
        END;
        """,
    ],
    "postgresql": [
        """
        CREATE TABLE IF NOT EXISTS credential_def_v0_1 (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            item_name TEXT,
            schema_id TEXT NOT NULL,
            schema_issuer_id TEXT,
            issuer_id TEXT,
            schema_name TEXT,
            tag TEXT,
            state TEXT,
            schema_version TEXT,
            epoch TEXT,
            support_revocation BOOLEAN,
            max_cred_num INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT credential_def_v0_1_unique_item_id UNIQUE (item_id)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_credential_def_item_id_v0_1 "
        + IDX_CRED_DEF_ON_ITEM_ID,
        "CREATE INDEX IF NOT EXISTS idx_credential_def_schema_id_v0_1 "
        + IDX_CRED_DEF_ON_SCHEMA_ID,
        "CREATE INDEX IF NOT EXISTS idx_credential_def_issuer_did_v0_1 "
        + IDX_CRED_DEF_ON_ISSUER_ID,
        """
        CREATE OR REPLACE FUNCTION update_credential_def_timestamp_v0_1()
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
        CREATE TRIGGER trg_update_credential_def_timestamp_v0_1
        BEFORE UPDATE ON credential_def_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION update_credential_def_timestamp_v0_1();
        """,
    ],
    "mssql": [
        """
        CREATE TABLE credential_def_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            item_id INT NOT NULL,
            item_name NVARCHAR(MAX),
            schema_id NVARCHAR(255) NOT NULL,
            schema_issuer_id NVARCHAR(255),
            issuer_id NVARCHAR(255),
            schema_name NVARCHAR(MAX),
            tag NVARCHAR(255),
            state NVARCHAR(255),
            schema_version NVARCHAR(50),
            epoch NVARCHAR(50),
            support_revocation BIT,
            max_cred_num INT,
            created_at DATETIME2 DEFAULT SYSDATETIME(),
            updated_at DATETIME2 DEFAULT SYSDATETIME(),
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT credential_def_v0_1_unique_item_id UNIQUE (item_id)
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_credential_def_item_id_v0_1 "
        + IDX_CRED_DEF_ON_ITEM_ID,
        "CREATE NONCLUSTERED INDEX idx_credential_def_schema_id_v0_1 "
        + IDX_CRED_DEF_ON_SCHEMA_ID,
        "CREATE NONCLUSTERED INDEX idx_credential_def_issuer_did_v0_1 "
        + IDX_CRED_DEF_ON_ISSUER_ID,
        """
        CREATE TRIGGER trg_update_credential_def_timestamp_v0_1
        ON credential_def_v0_1
        AFTER UPDATE
        AS
        BEGIN
            UPDATE credential_def_v0_1
            SET updated_at = SYSDATETIME()
            FROM credential_def_v0_1
            INNER JOIN inserted ON credential_def_v0_1.id = inserted.id
            WHERE inserted.updated_at IS NULL;
        END;
        """,
    ],
}

DROP_SCHEMAS = {
    "sqlite": [
        "DROP TRIGGER IF EXISTS trg_update_credential_def_timestamp_v0_1;",
        "DROP INDEX IF EXISTS idx_credential_def_issuer_did_v0_1;",
        "DROP INDEX IF EXISTS idx_credential_def_schema_id_v0_1;",
        "DROP INDEX IF EXISTS idx_credential_def_item_id_v0_1;",
        "DROP TABLE IF EXISTS credential_def_v0_1;",
    ],
    "postgresql": [
        "DROP TRIGGER IF EXISTS trg_update_credential_def_timestamp_v0_1 "
        "ON credential_def_v0_1;",
        "DROP FUNCTION IF EXISTS update_credential_def_timestamp_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_credential_def_issuer_did_v0_1;",
        "DROP INDEX IF EXISTS idx_credential_def_schema_id_v0_1;",
        "DROP INDEX IF EXISTS idx_credential_def_item_id_v0_1;",
        "DROP TABLE IF EXISTS credential_def_v0_1 CASCADE;",
    ],
    "mssql": [
        "DROP TRIGGER IF EXISTS trg_update_credential_def_timestamp_v0_1;",
        "DROP INDEX IF EXISTS idx_credential_def_issuer_did_v0_1 ON credential_def_v0_1;",
        "DROP INDEX IF EXISTS idx_credential_def_schema_id_v0_1 ON credential_def_v0_1;",
        "DROP INDEX IF EXISTS idx_credential_def_item_id_v0_1 ON credential_def_v0_1;",
        "DROP TABLE IF EXISTS credential_def_v0_1;",
    ],
}

COLUMNS = [
    "schema_id",
    "schema_issuer_id",
    "issuer_id",
    "tag",
    "schema_name",
    "state",
    "schema_version",
    "epoch",
    "support_revocation",
    "max_cred_num",
]
