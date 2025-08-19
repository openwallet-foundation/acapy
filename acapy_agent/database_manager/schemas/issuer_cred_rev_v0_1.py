CATEGORY = "issuer_cred_rev"

SCHEMAS = {
    "sqlite": [
        """
        CREATE TABLE IF NOT EXISTS issuer_cred_rev_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            state TEXT,
            cred_ex_id TEXT,
            rev_reg_id TEXT,
            cred_rev_id TEXT,
            cred_def_id TEXT,
            cred_ex_version TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT issuer_cred_rev_v0_1_unique_rev_reg_cred_rev UNIQUE (rev_reg_id, cred_rev_id)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_issuer_cred_rev_item_id_v0_1 ON issuer_cred_rev_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_issuer_cred_rev_cred_ex_id_v0_1 ON issuer_cred_rev_v0_1 (cred_ex_id);",
        "CREATE INDEX IF NOT EXISTS idx_issuer_cred_rev_rev_reg_id_v0_1 ON issuer_cred_rev_v0_1 (rev_reg_id);",
        "CREATE INDEX IF NOT EXISTS idx_issuer_cred_rev_cred_def_id_v0_1 ON issuer_cred_rev_v0_1 (cred_def_id);",
        "CREATE INDEX IF NOT EXISTS idx_issuer_cred_rev_state_v0_1 ON issuer_cred_rev_v0_1 (state);",
        "CREATE INDEX IF NOT EXISTS idx_issuer_cred_rev_rev_reg_cred_rev_v0_1 ON issuer_cred_rev_v0_1 (rev_reg_id, cred_rev_id);",
        """
        CREATE TRIGGER IF NOT EXISTS trg_update_issuer_cred_rev_timestamp_v0_1
        AFTER UPDATE ON issuer_cred_rev_v0_1
        FOR EACH ROW
        BEGIN
            UPDATE issuer_cred_rev_v0_1
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = OLD.id;
        END;
        """,
    ],
    "postgresql": [
        """
        CREATE TABLE IF NOT EXISTS issuer_cred_rev_v0_1 (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            state TEXT,
            cred_ex_id TEXT,
            rev_reg_id TEXT,
            cred_rev_id TEXT,
            cred_def_id TEXT,
            cred_ex_version TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT issuer_cred_rev_v0_1_unique_rev_reg_cred_rev UNIQUE (rev_reg_id, cred_rev_id)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_issuer_cred_rev_item_id_v0_1 ON issuer_cred_rev_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_issuer_cred_rev_cred_ex_id_v0_1 ON issuer_cred_rev_v0_1 (cred_ex_id);",
        "CREATE INDEX IF NOT EXISTS idx_issuer_cred_rev_rev_reg_id_v0_1 ON issuer_cred_rev_v0_1 (rev_reg_id);",
        "CREATE INDEX IF NOT EXISTS idx_issuer_cred_rev_cred_def_id_v0_1 ON issuer_cred_rev_v0_1 (cred_def_id);",
        "CREATE INDEX IF NOT EXISTS idx_issuer_cred_rev_state_v0_1 ON issuer_cred_rev_v0_1 (state);",
        "CREATE INDEX IF NOT EXISTS idx_issuer_cred_rev_rev_reg_cred_rev_v0_1 ON issuer_cred_rev_v0_1 (rev_reg_id, cred_rev_id);",
        """
        CREATE OR REPLACE FUNCTION update_issuer_cred_rev_timestamp_v0_1()
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
        CREATE TRIGGER trg_update_issuer_cred_rev_timestamp_v0_1
        BEFORE UPDATE ON issuer_cred_rev_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION update_issuer_cred_rev_timestamp_v0_1();
        """,
    ],
    "mssql": [
        """
        CREATE TABLE issuer_cred_rev_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            item_id INT NOT NULL,
            item_name NVARCHAR(MAX) NOT NULL,
            state NVARCHAR(255),
            cred_ex_id NVARCHAR(255),
            rev_reg_id NVARCHAR(255),
            cred_rev_id NVARCHAR(255),
            cred_def_id NVARCHAR(255),
            cred_ex_version NVARCHAR(50),
            created_at DATETIME2 DEFAULT SYSDATETIME(),
            updated_at DATETIME2 DEFAULT SYSDATETIME(),
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT issuer_cred_rev_v0_1_unique_rev_reg_cred_rev UNIQUE (rev_reg_id, cred_rev_id)
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_issuer_cred_rev_item_id_v0_1 ON issuer_cred_rev_v0_1 (item_id);",
        "CREATE NONCLUSTERED INDEX idx_issuer_cred_rev_cred_ex_id_v0_1 ON issuer_cred_rev_v0_1 (cred_ex_id);",
        "CREATE NONCLUSTERED INDEX idx_issuer_cred_rev_rev_reg_id_v0_1 ON issuer_cred_rev_v0_1 (rev_reg_id);",
        "CREATE NONCLUSTERED INDEX idx_issuer_cred_rev_cred_def_id_v0_1 ON issuer_cred_rev_v0_1 (cred_def_id);",
        "CREATE NONCLUSTERED INDEX idx_issuer_cred_rev_state_v0_1 ON issuer_cred_rev_v0_1 (state);",
        "CREATE NONCLUSTERED INDEX idx_issuer_cred_rev_rev_reg_cred_rev_v0_1 ON issuer_cred_rev_v0_1 (rev_reg_id, cred_rev_id);",
        """
        CREATE TRIGGER trg_update_issuer_cred_rev_timestamp_v0_1
        ON issuer_cred_rev_v0_1
        AFTER UPDATE
        AS
        BEGIN
            UPDATE issuer_cred_rev_v0_1
            SET updated_at = SYSDATETIME()
            FROM issuer_cred_rev_v0_1
            INNER JOIN inserted ON issuer_cred_rev_v0_1.id = inserted.id
            WHERE inserted.updated_at IS NULL;
        END;
        """,
    ],
}

DROP_SCHEMAS = {
    "sqlite": [
        "DROP TRIGGER IF EXISTS trg_update_issuer_cred_rev_timestamp_v0_1;",
        "DROP INDEX IF EXISTS idx_issuer_cred_rev_rev_reg_cred_rev_v0_1;",
        "DROP INDEX IF EXISTS idx_issuer_cred_rev_state_v0_1;",
        "DROP INDEX IF EXISTS idx_issuer_cred_rev_cred_def_id_v0_1;",
        "DROP INDEX IF EXISTS idx_issuer_cred_rev_rev_reg_id_v0_1;",
        "DROP INDEX IF EXISTS idx_issuer_cred_rev_cred_ex_id_v0_1;",
        "DROP INDEX IF EXISTS idx_issuer_cred_rev_item_id_v0_1;",
        "DROP TABLE IF EXISTS issuer_cred_rev_v0_1;",
    ],
    "postgresql": [
        "DROP TRIGGER IF EXISTS trg_update_issuer_cred_rev_timestamp_v0_1 ON issuer_cred_rev_v0_1;",
        "DROP FUNCTION IF EXISTS update_issuer_cred_rev_timestamp_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_issuer_cred_rev_rev_reg_cred_rev_v0_1;",
        "DROP INDEX IF EXISTS idx_issuer_cred_rev_state_v0_1;",
        "DROP INDEX IF EXISTS idx_issuer_cred_rev_cred_def_id_v0_1;",
        "DROP INDEX IF EXISTS idx_issuer_cred_rev_rev_reg_id_v0_1;",
        "DROP INDEX IF EXISTS idx_issuer_cred_rev_cred_ex_id_v0_1;",
        "DROP INDEX IF EXISTS idx_issuer_cred_rev_item_id_v0_1;",
        "DROP TABLE IF EXISTS issuer_cred_rev_v0_1 CASCADE;",
    ],
    "mssql": [
        "DROP TRIGGER IF EXISTS trg_update_issuer_cred_rev_timestamp_v0_1;",
        "DROP INDEX IF EXISTS idx_issuer_cred_rev_rev_reg_cred_rev_v0_1 ON issuer_cred_rev_v0_1;",
        "DROP INDEX IF EXISTS idx_issuer_cred_rev_state_v0_1 ON issuer_cred_rev_v0_1;",
        "DROP INDEX IF EXISTS idx_issuer_cred_rev_cred_def_id_v0_1 ON issuer_cred_rev_v0_1;",
        "DROP INDEX IF EXISTS idx_issuer_cred_rev_rev_reg_id_v0_1 ON issuer_cred_rev_v0_1;",
        "DROP INDEX IF EXISTS idx_issuer_cred_rev_cred_ex_id_v0_1 ON issuer_cred_rev_v0_1;",
        "DROP INDEX IF EXISTS idx_issuer_cred_rev_item_id_v0_1 ON issuer_cred_rev_v0_1;",
        "DROP TABLE IF EXISTS issuer_cred_rev_v0_1;",
    ],
}


COLUMNS = [
    "state",
    "cred_ex_id",
    "rev_reg_id",
    "cred_rev_id",
    "cred_def_id",
    "cred_ex_version",
    "created_at",
    "updated_at",
]

# sample
# category=issuer_cred_rev, name=76db16bc-bcfb-4d91-8c89-53373f09bd4a,
#  value={"cred_ex_id": "e8a39578-b7e3-4682-b319-d2f5433adf25", "cred_rev_id": "1", "cred_ex_version": "2", "cred_def_id": "BacujJ3zNmAR9afs9hPryb:3:CL:2842581:cd0.31", "rev_reg_id": "BacujJ3zNmAR9afs9hPryb:4:BacujJ3zNmAR9afs9hPryb:3:CL:2842581:cd0.31:CL_ACCUM:0", "state": "issued", "created_at": "2025-06-17T19:29:48.947936Z", "updated_at": "2025-06-17T19:29:48.947936Z"},
# tags={'cred_ex_id': 'e8a39578-b7e3-4682-b319-d2f5433adf25', 'cred_rev_id': '1', 'cred_ex_version': '2', 'cred_def_id': 'BacujJ3zNmAR9afs9hPryb:3:CL:2842581:cd0.31', 'rev_reg_id': 'BacujJ3zNmAR9afs9hPryb:4:BacujJ3zNmAR9afs9hPryb:3:CL:2842581:cd0.31:CL_ACCUM:0', 'state': 'issued'}, expiry_ms=None, value_json=None
