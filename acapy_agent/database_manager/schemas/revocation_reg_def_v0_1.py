"""Module docstring."""

CATEGORY = "revocation_reg_def"

SCHEMAS = {
    "sqlite": [
        """
        CREATE TABLE IF NOT EXISTS revocation_reg_def_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            state TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            issuerId TEXT,
            cred_def_id TEXT,
            revoc_def_type TEXT,
            value TEXT,
            active INTEGER,
            FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_revocation_reg_def_item_id_v0_1 "
        "ON revocation_reg_def_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_revocation_reg_def_item_name_v0_1 "
        "ON revocation_reg_def_v0_1 (item_name);",
        "CREATE INDEX IF NOT EXISTS idx_revocation_reg_def_cred_def_id_v0_1 "
        "ON revocation_reg_def_v0_1 (cred_def_id);",
        "CREATE INDEX IF NOT EXISTS idx_revocation_reg_def_state_v0_1 "
        "ON revocation_reg_def_v0_1 (state);",
        "CREATE INDEX IF NOT EXISTS idx_revocation_reg_def_issuerId_v0_1 "
        "ON revocation_reg_def_v0_1 (issuerId);",
        """
        CREATE TABLE IF NOT EXISTS revocation_reg_def_values_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rev_reg_def_id INTEGER NOT NULL,
            public_keys TEXT NOT NULL CHECK (json_valid(public_keys)),
            max_cred_num INTEGER NOT NULL,
            tails_location TEXT NOT NULL,
            tails_hash TEXT NOT NULL,
            FOREIGN KEY (rev_reg_def_id) 
                REFERENCES revocation_reg_def_v0_1(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS "
        "idx_revocation_reg_def_values_rev_reg_def_id_v0_1 "
        "ON revocation_reg_def_values_v0_1 (rev_reg_def_id);",
        """
        CREATE TRIGGER IF NOT EXISTS trg_insert_revocation_reg_def_values_v0_1
        AFTER INSERT ON revocation_reg_def_v0_1
        FOR EACH ROW
        WHEN NEW.value IS NOT NULL AND json_valid(NEW.value)
        BEGIN
            INSERT INTO revocation_reg_def_values_v0_1 (
                rev_reg_def_id, public_keys, max_cred_num, tails_location, tails_hash
            )
            SELECT
                NEW.id,
                json_extract(NEW.value, '$.publicKeys'),
                CAST(json_extract(NEW.value, '$.maxCredNum') AS INTEGER),
                json_extract(NEW.value, '$.tailsLocation'),
                json_extract(NEW.value, '$.tailsHash')
            WHERE
                json_extract(NEW.value, '$.publicKeys') IS NOT NULL
                AND json_extract(NEW.value, '$.maxCredNum') IS NOT NULL
                AND json_extract(NEW.value, '$.tailsLocation') IS NOT NULL
                AND json_extract(NEW.value, '$.tailsHash') IS NOT NULL;
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS trg_update_revocation_reg_def_values_v0_1
        AFTER UPDATE ON revocation_reg_def_v0_1
        FOR EACH ROW
        WHEN NEW.value IS NOT NULL AND json_valid(NEW.value) AND NEW.value != OLD.value
        BEGIN
            DELETE FROM revocation_reg_def_values_v0_1 WHERE rev_reg_def_id = OLD.id;
            INSERT INTO revocation_reg_def_values_v0_1 (
                rev_reg_def_id, public_keys, max_cred_num, tails_location, tails_hash
            )
            SELECT
                NEW.id,
                json_extract(NEW.value, '$.publicKeys'),
                CAST(json_extract(NEW.value, '$.maxCredNum') AS INTEGER),
                json_extract(NEW.value, '$.tailsLocation'),
                json_extract(NEW.value, '$.tailsHash')
            WHERE
                json_extract(NEW.value, '$.publicKeys') IS NOT NULL
                AND json_extract(NEW.value, '$.maxCredNum') IS NOT NULL
                AND json_extract(NEW.value, '$.tailsLocation') IS NOT NULL
                AND json_extract(NEW.value, '$.tailsHash') IS NOT NULL;
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS trg_update_revocation_reg_def_timestamp_v0_1
        AFTER UPDATE ON revocation_reg_def_v0_1
        FOR EACH ROW
        BEGIN
            UPDATE revocation_reg_def_v0_1
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = OLD.id;
        END;
        """,
    ],
    "postgresql": [
        """
        CREATE TABLE IF NOT EXISTS revocation_reg_def_v0_1 (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            state TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            issuerId TEXT,
            cred_def_id TEXT,
            revoc_def_type TEXT,
            value TEXT,
            active BOOLEAN,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_revocation_reg_def_item_id_v0_1 "
        "ON revocation_reg_def_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_revocation_reg_def_item_name_v0_1 "
        "ON revocation_reg_def_v0_1 (item_name);",
        "CREATE INDEX IF NOT EXISTS idx_revocation_reg_def_cred_def_id_v0_1 "
        "ON revocation_reg_def_v0_1 (cred_def_id);",
        "CREATE INDEX IF NOT EXISTS idx_revocation_reg_def_state_v0_1 "
        "ON revocation_reg_def_v0_1 (state);",
        "CREATE INDEX IF NOT EXISTS idx_revocation_reg_def_issuerId_v0_1 "
        "ON revocation_reg_def_v0_1 (issuerId);",
        """
        CREATE TABLE IF NOT EXISTS revocation_reg_def_values_v0_1 (
            id SERIAL PRIMARY KEY,
            rev_reg_def_id INTEGER NOT NULL,
            public_keys TEXT NOT NULL CHECK (public_keys::jsonb IS NOT NULL),
            max_cred_num INTEGER NOT NULL,
            tails_location TEXT NOT NULL,
            tails_hash TEXT NOT NULL,
            CONSTRAINT fk_rev_reg_def_id FOREIGN KEY (rev_reg_def_id) 
                REFERENCES revocation_reg_def_v0_1(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS "
        "idx_revocation_reg_def_values_rev_reg_def_id_v0_1 "
        "ON revocation_reg_def_values_v0_1 (rev_reg_def_id);",
        """
        CREATE OR REPLACE FUNCTION insert_revocation_reg_def_values_v0_1()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.value IS NOT NULL AND NEW.value::jsonb IS NOT NULL THEN
                INSERT INTO revocation_reg_def_values_v0_1 (
                    rev_reg_def_id, public_keys, max_cred_num, tails_location, tails_hash
                )
                SELECT
                    NEW.id,
                    jsonb_extract_path_text(NEW.value::jsonb, 'publicKeys'),
                    (jsonb_extract_path_text(NEW.value::jsonb, 
                                             'maxCredNum'))::INTEGER,
                    jsonb_extract_path_text(NEW.value::jsonb, 
                                            'tailsLocation'),
                    jsonb_extract_path_text(NEW.value::jsonb, 
                                            'tailsHash')
                WHERE
                    jsonb_extract_path_text(NEW.value::jsonb, 'publicKeys') IS NOT NULL
                    AND jsonb_extract_path_text(NEW.value::jsonb, 
                                                 'maxCredNum') IS NOT NULL
                    AND jsonb_extract_path_text(NEW.value::jsonb, 
                                                 'tailsLocation') IS NOT NULL
                    AND jsonb_extract_path_text(NEW.value::jsonb, 
                                                 'tailsHash') IS NOT NULL;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        CREATE TRIGGER trg_insert_revocation_reg_def_values_v0_1
        AFTER INSERT ON revocation_reg_def_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION insert_revocation_reg_def_values_v0_1();
        """,
        """
        CREATE OR REPLACE FUNCTION update_revocation_reg_def_values_v0_1()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.value IS NOT NULL AND NEW.value::jsonb IS NOT NULL 
               AND NEW.value != OLD.value THEN
                DELETE FROM revocation_reg_def_values_v0_1 WHERE rev_reg_def_id = OLD.id;
                INSERT INTO revocation_reg_def_values_v0_1 (
                    rev_reg_def_id, public_keys, max_cred_num, tails_location, tails_hash
                )
                SELECT
                    NEW.id,
                    jsonb_extract_path_text(NEW.value::jsonb, 'publicKeys'),
                    (jsonb_extract_path_text(NEW.value::jsonb, 
                                             'maxCredNum'))::INTEGER,
                    jsonb_extract_path_text(NEW.value::jsonb, 
                                            'tailsLocation'),
                    jsonb_extract_path_text(NEW.value::jsonb, 
                                            'tailsHash')
                WHERE
                    jsonb_extract_path_text(NEW.value::jsonb, 'publicKeys') IS NOT NULL
                    AND jsonb_extract_path_text(NEW.value::jsonb, 
                                                 'maxCredNum') IS NOT NULL
                    AND jsonb_extract_path_text(NEW.value::jsonb, 
                                                 'tailsLocation') IS NOT NULL
                    AND jsonb_extract_path_text(NEW.value::jsonb, 
                                                 'tailsHash') IS NOT NULL;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        CREATE TRIGGER trg_update_revocation_reg_def_values_v0_1
        AFTER UPDATE ON revocation_reg_def_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION update_revocation_reg_def_values_v0_1();
        """,
        """
        CREATE OR REPLACE FUNCTION update_revocation_reg_def_timestamp_v0_1()
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
        CREATE TRIGGER trg_update_revocation_reg_def_timestamp_v0_1
        BEFORE UPDATE ON revocation_reg_def_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION update_revocation_reg_def_timestamp_v0_1();
        """,
    ],
    "mssql": [
        """
        CREATE TABLE revocation_reg_def_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            item_id INT NOT NULL,
            item_name NVARCHAR(MAX) NOT NULL,
            state NVARCHAR(255),
            created_at DATETIME2 DEFAULT SYSDATETIME(),
            updated_at DATETIME2 DEFAULT SYSDATETIME(),
            issuerId NVARCHAR(255),
            cred_def_id NVARCHAR(255),
            revoc_def_type NVARCHAR(255),
            value NVARCHAR(MAX),
            active BIT,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_revocation_reg_def_item_id_v0_1 "
        "ON revocation_reg_def_v0_1 (item_id);",
        "CREATE NONCLUSTERED INDEX idx_revocation_reg_def_item_name_v0_1 "
        "ON revocation_reg_def_v0_1 (item_name);",
        "CREATE NONCLUSTERED INDEX idx_revocation_reg_def_cred_def_id_v0_1 "
        "ON revocation_reg_def_v0_1 (cred_def_id);",
        "CREATE NONCLUSTERED INDEX idx_revocation_reg_def_state_v0_1 "
        "ON revocation_reg_def_v0_1 (state);",
        "CREATE NONCLUSTERED INDEX idx_revocation_reg_def_issuerId_v0_1 "
        "ON revocation_reg_def_v0_1 (issuerId);"
        """
        CREATE TABLE revocation_reg_def_values_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            rev_reg_def_id INT NOT NULL,
            public_keys NVARCHAR(MAX) NOT NULL CHECK (ISJSON(public_keys) = 1),
            max_cred_num INT NOT NULL,
            tails_location NVARCHAR(MAX) NOT NULL,
            tails_hash NVARCHAR(MAX) NOT NULL,
            CONSTRAINT fk_rev_reg_def_id FOREIGN KEY (rev_reg_def_id) 
                REFERENCES revocation_reg_def_v0_1(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE NONCLUSTERED INDEX "
        "idx_revocation_reg_def_values_rev_reg_def_id_v0_1 "
        "ON revocation_reg_def_values_v0_1 (rev_reg_def_id);"
        """
        CREATE TRIGGER trg_insert_revocation_reg_def_values_v0_1
        ON revocation_reg_def_v0_1
        AFTER INSERT
        AS
        BEGIN
            INSERT INTO revocation_reg_def_values_v0_1 (
                rev_reg_def_id, public_keys, max_cred_num, tails_location, tails_hash
            )
            SELECT
                i.id,
                JSON_VALUE(i.value, '$.publicKeys'),
                CAST(JSON_VALUE(i.value, '$.maxCredNum') AS INT),
                JSON_VALUE(i.value, '$.tailsLocation'),
                JSON_VALUE(i.value, '$.tailsHash')
            FROM inserted i
            WHERE i.value IS NOT NULL
              AND ISJSON(i.value) = 1
              AND JSON_VALUE(i.value, '$.publicKeys') IS NOT NULL
              AND JSON_VALUE(i.value, '$.maxCredNum') IS NOT NULL
              AND JSON_VALUE(i.value, '$.tailsLocation') IS NOT NULL
              AND JSON_VALUE(i.value, '$.tailsHash') IS NOT NULL;
        END;
        """,
        """
        CREATE TRIGGER trg_update_revocation_reg_def_values_v0_1
        ON revocation_reg_def_v0_1
        AFTER UPDATE
        AS
        BEGIN
            DELETE FROM revocation_reg_def_values_v0_1
            WHERE rev_reg_def_id IN (
                SELECT i.id
                FROM inserted i
                INNER JOIN deleted d ON i.id = d.id
                WHERE i.value IS NOT NULL
                  AND ISJSON(i.value) = 1
                  AND i.value != d.value
            );

            INSERT INTO revocation_reg_def_values_v0_1 (
                rev_reg_def_id, public_keys, max_cred_num, tails_location, tails_hash
            )
            SELECT
                i.id,
                JSON_VALUE(i.value, '$.publicKeys'),
                CAST(JSON_VALUE(i.value, '$.maxCredNum') AS INT),
                JSON_VALUE(i.value, '$.tailsLocation'),
                JSON_VALUE(i.value, '$.tailsHash')
            FROM inserted i
            WHERE i.value IS NOT NULL
              AND ISJSON(i.value) = 1
              AND JSON_VALUE(i.value, '$.publicKeys') IS NOT NULL
              AND JSON_VALUE(i.value, '$.maxCredNum') IS NOT NULL
              AND JSON_VALUE(i.value, '$.tailsLocation') IS NOT NULL
              AND JSON_VALUE(i.value, '$.tailsHash') IS NOT NULL
              AND i.value != (SELECT d.value FROM deleted d WHERE d.id = i.id);
        END;
        """,
        """
        CREATE TRIGGER trg_update_revocation_reg_def_timestamp_v0_1
        ON revocation_reg_def_v0_1
        AFTER UPDATE
        AS
        BEGIN
            UPDATE revocation_reg_def_v0_1
            SET updated_at = SYSDATETIME()
            FROM revocation_reg_def_v0_1
            INNER JOIN inserted ON revocation_reg_def_v0_1.id = inserted.id
            WHERE inserted.updated_at IS NULL;
        END;
        """,
    ],
}


DROP_SCHEMAS = {
    "sqlite": [
        "DROP TRIGGER IF EXISTS trg_update_revocation_reg_def_timestamp_v0_1;",
        "DROP TRIGGER IF EXISTS trg_update_revocation_reg_def_values_v0_1;",
        "DROP TRIGGER IF EXISTS trg_insert_revocation_reg_def_values_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_reg_def_values_rev_reg_def_id_v0_1;",
        "DROP TABLE IF EXISTS revocation_reg_def_values_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_reg_def_issuerId_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_reg_def_state_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_reg_def_cred_def_id_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_reg_def_item_name_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_reg_def_item_id_v0_1;",
        "DROP TABLE IF EXISTS revocation_reg_def_v0_1;",
    ],
    "postgresql": [
        "DROP TRIGGER IF EXISTS trg_update_revocation_reg_def_timestamp_v0_1 "
        "ON revocation_reg_def_v0_1;",
        "DROP FUNCTION IF EXISTS update_revocation_reg_def_timestamp_v0_1 CASCADE;",
        "DROP TRIGGER IF EXISTS trg_update_revocation_reg_def_values_v0_1 "
        "ON revocation_reg_def_v0_1;",
        "DROP FUNCTION IF EXISTS update_revocation_reg_def_values_v0_1 CASCADE;",
        "DROP TRIGGER IF EXISTS trg_insert_revocation_reg_def_values_v0_1 ON "
        "revocation_reg_def_v0_1;",
        "DROP FUNCTION IF EXISTS insert_revocation_reg_def_values_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_revocation_reg_def_values_rev_reg_def_id_v0_1;",
        "DROP TABLE IF EXISTS revocation_reg_def_values_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_revocation_reg_def_issuerId_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_reg_def_state_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_reg_def_cred_def_id_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_reg_def_item_name_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_reg_def_item_id_v0_1;",
        "DROP TABLE IF EXISTS revocation_reg_def_v0_1 CASCADE;",
    ],
    "mssql": [
        "DROP TRIGGER IF EXISTS trg_update_revocation_reg_def_timestamp_v0_1;",
        "DROP TRIGGER IF EXISTS trg_update_revocation_reg_def_values_v0_1;",
        "DROP TRIGGER IF EXISTS trg_insert_revocation_reg_def_values_v0_1;",
        "DROP INDEX IF EXISTS "
        "idx_revocation_reg_def_values_rev_reg_def_id_v0_1 "
        "ON revocation_reg_def_values_v0_1;",
        "DROP TABLE IF EXISTS revocation_reg_def_values_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_reg_def_issuerId_v0_1 "
        "ON revocation_reg_def_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_reg_def_state_v0_1 "
        "ON revocation_reg_def_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_reg_def_cred_def_id_v0_1 "
        "ON revocation_reg_def_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_reg_def_item_name_v0_1 "
        "ON revocation_reg_def_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_reg_def_item_id_v0_1 "
        "ON revocation_reg_def_v0_1;"
        "DROP TABLE IF EXISTS revocation_reg_def_v0_1;",
    ],
}


COLUMNS = ["state", "issuerId", "cred_def_id", "revoc_def_type", "value", "active"]

# sample
# Sample revocation registry definition:
# revocation_reg_def,
# name=BacujJ3zNmAR9afs9hPryb:4:BacujJ3zNmAR9afs9hPryb:3:CL:2842508:cd0.29:CL_ACCUM:1,
# value={
#   "issuerId": "BacujJ3zNmAR9afs9hPryb",
#   "revocDefType": "CL_ACCUM",
#   "credDefId": "BacujJ3zNmAR9afs9hPryb:3:CL:2842508:cd0.29",
#   "tag": "1",
#   "value": {
#     "publicKeys": { "accumKey": { "z": "<very_long_key>" } },
#     "maxCredNum": 5,
#     "tailsLocation": "http://tails-server.digicred.services:6543/hash/...",
#     "tailsHash": "62pgdbNRRhDsBkhmUx4FdCEqrcczEdQ4jumm4rQK1K2K"
#   }
# }
# tags={
#   'cred_def_id': 'BacujJ3zNmAR9afs9hPryb:3:CL:2842508:cd0.29',
#   'state': 'finished',
#   'active': 'false'
# }
