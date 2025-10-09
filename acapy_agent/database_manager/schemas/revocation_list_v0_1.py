"""Module docstring."""

CATEGORY = "revocation_list"

SCHEMAS = {
    "sqlite": [
        """
        CREATE TABLE IF NOT EXISTS revocation_list_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            rev_reg_def_id TEXT,
            issuer_id TEXT,
            revocationList TEXT,  -- Note: json_valid() not available in older SQLite
            current_accumulator TEXT,
            next_index INTEGER NOT NULL DEFAULT 0,
            pending TEXT,
            state TEXT,
            rev_list TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_revocation_list_item_id_v0_1 "
        "ON revocation_list_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_revocation_list_rev_reg_def_id_v0_1 "
        "ON revocation_list_v0_1 (rev_reg_def_id);",
        "CREATE INDEX IF NOT EXISTS idx_revocation_list_issuer_id_v0_1 "
        "ON revocation_list_v0_1 (issuer_id);",
        "CREATE INDEX IF NOT EXISTS idx_revocation_list_rev_reg_def_id_state_v0_1 "
        "ON revocation_list_v0_1 (rev_reg_def_id, state);",
        """
        CREATE TABLE IF NOT EXISTS revocation_list_revocations_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            revocation_list_id INTEGER NOT NULL,
            revoked_index INTEGER NOT NULL,
            FOREIGN KEY (revocation_list_id) REFERENCES revocation_list_v0_1(id)
            ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_revocation_list_revocations_revoked_index_v0_1 "
        "ON revocation_list_revocations_v0_1 (revoked_index);",
        """
        CREATE TRIGGER IF NOT EXISTS trg_insert_revocation_list_fields_v0_1
        AFTER INSERT ON revocation_list_v0_1
        FOR EACH ROW
        WHEN NEW.rev_list IS NOT NULL
        BEGIN
            UPDATE revocation_list_v0_1
            SET
                rev_reg_def_id = json_extract(NEW.rev_list, '$.revRegDefId'),
                issuer_id = json_extract(NEW.rev_list, '$.issuerId'),
                revocationList = json_extract(NEW.rev_list, '$.revocationList'),
                current_accumulator = json_extract(NEW.rev_list, '$.currentAccumulator')
            WHERE id = NEW.id;
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS trg_insert_revocation_list_revocations_v0_1
        AFTER INSERT ON revocation_list_v0_1
        FOR EACH ROW
        WHEN NEW.revocationList IS NOT NULL
        BEGIN
            INSERT INTO revocation_list_revocations_v0_1
            (revocation_list_id, revoked_index)
            SELECT NEW.id, key
            FROM json_each(NEW.revocationList)
            WHERE value = 1;
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS trg_update_revocation_list_fields_v0_1
        AFTER UPDATE ON revocation_list_v0_1
        FOR EACH ROW
        WHEN NEW.rev_list IS NOT NULL AND NEW.rev_list != OLD.rev_list
        BEGIN
            UPDATE revocation_list_v0_1
            SET
                rev_reg_def_id = json_extract(NEW.rev_list, '$.revRegDefId'),
                issuer_id = json_extract(NEW.rev_list, '$.issuerId'),
                revocationList = json_extract(NEW.rev_list, '$.revocationList'),
                current_accumulator = json_extract(NEW.rev_list, '$.currentAccumulator'),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = NEW.id;
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS trg_update_revocation_list_revocations_v0_1
        AFTER UPDATE ON revocation_list_v0_1
        FOR EACH ROW
        WHEN NEW.revocationList IS NOT NULL AND NEW.revocationList != OLD.revocationList
        BEGIN
            DELETE FROM revocation_list_revocations_v0_1
            WHERE revocation_list_id = OLD.id;
            INSERT INTO revocation_list_revocations_v0_1
            (revocation_list_id, revoked_index)
            SELECT NEW.id, key
            FROM json_each(NEW.revocationList)
            WHERE value = 1;
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS trg_update_revocation_list_timestamp_v0_1
        AFTER UPDATE ON revocation_list_v0_1
        FOR EACH ROW
        BEGIN
            UPDATE revocation_list_v0_1
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = OLD.id;
        END;
        """,
    ],
    "postgresql": [
        """
        CREATE TABLE IF NOT EXISTS revocation_list_v0_1 (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            rev_reg_def_id TEXT,
            issuer_id TEXT,
            revocationList TEXT CHECK (revocationList::jsonb IS NOT NULL),
            current_accumulator TEXT,
            next_index INTEGER NOT NULL DEFAULT 0,
            pending TEXT,
            state TEXT,
            rev_list TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id)
            REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_revocation_list_item_id_v0_1 "
        "ON revocation_list_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_revocation_list_rev_reg_def_id_v0_1 "
        "ON revocation_list_v0_1 (rev_reg_def_id);",
        "CREATE INDEX IF NOT EXISTS idx_revocation_list_issuer_id_v0_1 "
        "ON revocation_list_v0_1 (issuer_id);",
        "CREATE INDEX IF NOT EXISTS idx_revocation_list_rev_reg_def_id_state_v0_1 "
        "ON revocation_list_v0_1 (rev_reg_def_id, state);",
        """
        CREATE TABLE IF NOT EXISTS revocation_list_revocations_v0_1 (
            id SERIAL PRIMARY KEY,
            revocation_list_id INTEGER NOT NULL,
            revoked_index INTEGER NOT NULL,
            CONSTRAINT fk_revocation_list_id FOREIGN KEY (revocation_list_id)
            REFERENCES revocation_list_v0_1(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_revocation_list_revocations_revoked_index_v0_1 "
        "ON revocation_list_revocations_v0_1 (revoked_index);",
        """
        CREATE OR REPLACE FUNCTION insert_revocation_list_fields_v0_1()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.rev_list IS NOT NULL AND NEW.rev_list::jsonb IS NOT NULL THEN
                NEW.rev_reg_def_id = jsonb_extract_path_text(
                    NEW.rev_list::jsonb, 'revRegDefId');
                NEW.issuer_id = jsonb_extract_path_text(NEW.rev_list::jsonb, 'issuerId');
                NEW.revocationList = jsonb_extract_path_text(
                    NEW.rev_list::jsonb, 'revocationList');
                NEW.current_accumulator = jsonb_extract_path_text(
                    NEW.rev_list::jsonb, 'currentAccumulator');
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        CREATE TRIGGER trg_insert_revocation_list_fields_v0_1
        BEFORE INSERT ON revocation_list_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION insert_revocation_list_fields_v0_1();
        """,
        """
        CREATE OR REPLACE FUNCTION insert_revocation_list_revocations_v0_1()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.revocationList IS NOT NULL 
            AND NEW.revocationList::jsonb IS NOT NULL THEN
                INSERT INTO revocation_list_revocations_v0_1
                (revocation_list_id, revoked_index)
                SELECT NEW.id, (key::INTEGER)
                FROM jsonb_array_elements(NEW.revocationList::jsonb)
                WITH ORDINALITY AS arr(value, key)
                WHERE value::INTEGER = 1;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        CREATE TRIGGER trg_insert_revocation_list_revocations_v0_1
        AFTER INSERT ON revocation_list_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION insert_revocation_list_revocations_v0_1();
        """,
        """
        CREATE OR REPLACE FUNCTION update_revocation_list_fields_v0_1()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.rev_list IS NOT NULL AND NEW.rev_list::jsonb IS NOT NULL 
               AND NEW.rev_list != OLD.rev_list THEN
                NEW.rev_reg_def_id = jsonb_extract_path_text(
                    NEW.rev_list::jsonb, 'revRegDefId');
                NEW.issuer_id = jsonb_extract_path_text(NEW.rev_list::jsonb, 'issuerId');
                NEW.revocationList = jsonb_extract_path_text(
                    NEW.rev_list::jsonb, 'revocationList');
                NEW.current_accumulator = jsonb_extract_path_text(
                    NEW.rev_list::jsonb, 'currentAccumulator');
                NEW.updated_at = CURRENT_TIMESTAMP;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        CREATE TRIGGER trg_update_revocation_list_fields_v0_1
        BEFORE UPDATE ON revocation_list_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION update_revocation_list_fields_v0_1();
        """,
        """
        CREATE OR REPLACE FUNCTION update_revocation_list_revocations_v0_1()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.revocationList IS NOT NULL AND NEW.revocationList::jsonb IS NOT NULL 
               AND NEW.revocationList != OLD.revocationList THEN
                DELETE FROM revocation_list_revocations_v0_1 
                WHERE revocation_list_id = OLD.id;
                INSERT INTO revocation_list_revocations_v0_1
                (revocation_list_id, revoked_index)
                SELECT NEW.id, (key::INTEGER)
                FROM jsonb_array_elements(NEW.revocationList::jsonb)
                WITH ORDINALITY AS arr(value, key)
                WHERE value::INTEGER = 1;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        CREATE TRIGGER trg_update_revocation_list_revocations_v0_1
        AFTER UPDATE ON revocation_list_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION update_revocation_list_revocations_v0_1();
        """,
        """
        CREATE OR REPLACE FUNCTION update_revocation_list_timestamp_v0_1()
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
        CREATE TRIGGER trg_update_revocation_list_timestamp_v0_1
        BEFORE UPDATE ON revocation_list_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION update_revocation_list_timestamp_v0_1();
        """,
    ],
    "mssql": [
        """
        CREATE TABLE revocation_list_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            item_id INT NOT NULL,
            item_name NVARCHAR(MAX) NOT NULL,
            rev_reg_def_id NVARCHAR(255),
            issuer_id NVARCHAR(255),
            revocationList NVARCHAR(MAX) CHECK (ISJSON(revocationList) = 1),
            current_accumulator NVARCHAR(MAX),
            next_index INT NOT NULL DEFAULT 0,
            pending NVARCHAR(MAX),
            state NVARCHAR(255),
            rev_list NVARCHAR(MAX),
            created_at DATETIME2 DEFAULT SYSDATETIME(),
            updated_at DATETIME2 DEFAULT SYSDATETIME(),
            CONSTRAINT fk_item_id FOREIGN KEY (item_id)
            REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_revocation_list_item_id_v0_1 "
        "ON revocation_list_v0_1 (item_id);",
        "CREATE NONCLUSTERED INDEX idx_revocation_list_rev_reg_def_id_v0_1 "
        "ON revocation_list_v0_1 (rev_reg_def_id);",
        "CREATE NONCLUSTERED INDEX idx_revocation_list_issuer_id_v0_1 "
        "ON revocation_list_v0_1 (issuer_id);",
        "CREATE NONCLUSTERED INDEX idx_revocation_list_rev_reg_def_id_state_v0_1 "
        "ON revocation_list_v0_1 (rev_reg_def_id, state);",
        """
        CREATE TABLE revocation_list_revocations_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            revocation_list_id INT NOT NULL,
            revoked_index INT NOT NULL,
            CONSTRAINT fk_revocation_list_id FOREIGN KEY (revocation_list_id)
            REFERENCES revocation_list_v0_1(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_revocation_list_revocations_revoked_index_v0_1 "
        "ON revocation_list_revocations_v0_1 (revoked_index);",
        """
        CREATE TRIGGER trg_insert_revocation_list_fields_v0_1
        ON revocation_list_v0_1
        AFTER INSERT
        AS
        BEGIN
            UPDATE revocation_list_v0_1
            SET
                rev_reg_def_id = JSON_VALUE(i.rev_list, '$.revRegDefId'),
                issuer_id = JSON_VALUE(i.rev_list, '$.issuerId'),
                revocationList = JSON_VALUE(i.rev_list, '$.revocationList'),
                current_accumulator = JSON_VALUE(i.rev_list, '$.currentAccumulator')
            FROM revocation_list_v0_1 r
            INNER JOIN inserted i ON r.id = i.id
            WHERE i.rev_list IS NOT NULL AND ISJSON(i.rev_list) = 1;
        END;
        """,
        """
        CREATE TRIGGER trg_insert_revocation_list_revocations_v0_1
        ON revocation_list_v0_1
        AFTER INSERT
        AS
        BEGIN
            INSERT INTO revocation_list_revocations_v0_1
            (revocation_list_id, revoked_index)
            SELECT i.id, CAST(j.[key] AS INT)
            FROM inserted i
            CROSS APPLY OPENJSON(i.revocationList) j
            WHERE i.revocationList IS NOT NULL
              AND ISJSON(i.revocationList) = 1
              AND j.value = 1;
        END;
        """,
        """
        CREATE TRIGGER trg_update_revocation_list_fields_v0_1
        ON revocation_list_v0_1
        AFTER UPDATE
        AS
        BEGIN
            UPDATE revocation_list_v0_1
            SET
                rev_reg_def_id = JSON_VALUE(i.rev_list, '$.revRegDefId'),
                issuer_id = JSON_VALUE(i.rev_list, '$.issuerId'),
                revocationList = JSON_VALUE(i.rev_list, '$.revocationList'),
                current_accumulator = JSON_VALUE(i.rev_list, '$.currentAccumulator'),
                updated_at = SYSDATETIME()
            FROM revocation_list_v0_1 r
            INNER JOIN inserted i ON r.id = i.id
            WHERE i.rev_list IS NOT NULL
              AND ISJSON(i.rev_list) = 1
              AND i.rev_list != (SELECT d.rev_list FROM deleted d WHERE d.id = i.id);
        END;
        """,
        """
        CREATE TRIGGER trg_update_revocation_list_revocations_v0_1
        ON revocation_list_v0_1
        AFTER UPDATE
        AS
        BEGIN
            DELETE FROM revocation_list_revocations_v0_1
            WHERE revocation_list_id IN (
                SELECT i.id
                FROM inserted i
                INNER JOIN deleted d ON i.id = d.id
                WHERE i.revocationList IS NOT NULL
                  AND ISJSON(i.revocationList) = 1
                  AND i.revocationList != d.revocationList
            );

            INSERT INTO revocation_list_revocations_v0_1
            (revocation_list_id, revoked_index)
            SELECT i.id, CAST(j.[key] AS INT)
            FROM inserted i
            CROSS APPLY OPENJSON(i.revocationList) j
            WHERE i.revocationList IS NOT NULL
              AND ISJSON(i.revocationList) = 1
              AND j.value = 1
              AND i.revocationList != (
                SELECT d.revocationList FROM deleted d WHERE d.id = i.id
              );
        END;
        """,
        """
        CREATE TRIGGER trg_update_revocation_list_timestamp_v0_1
        ON revocation_list_v0_1
        AFTER UPDATE
        AS
        BEGIN
            UPDATE revocation_list_v0_1
            SET updated_at = SYSDATETIME()
            FROM revocation_list_v0_1
            INNER JOIN inserted ON revocation_list_v0_1.id = inserted.id
            WHERE inserted.updated_at IS NULL;
        END;
        """,
    ],
}


DROP_SCHEMAS = {
    "sqlite": [
        "DROP TRIGGER IF EXISTS trg_update_revocation_list_timestamp_v0_1;",
        "DROP TRIGGER IF EXISTS trg_update_revocation_list_revocations_v0_1;",
        "DROP TRIGGER IF EXISTS trg_update_revocation_list_fields_v0_1;",
        "DROP TRIGGER IF EXISTS trg_insert_revocation_list_revocations_v0_1;",
        "DROP TRIGGER IF EXISTS trg_insert_revocation_list_fields_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_list_revocations_revoked_index_v0_1;",
        "DROP TABLE IF EXISTS revocation_list_revocations_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_list_rev_reg_def_id_state_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_list_issuer_id_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_list_rev_reg_def_id_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_list_item_id_v0_1;",
        "DROP TABLE IF EXISTS revocation_list_v0_1;",
    ],
    "postgresql": [
        "DROP TRIGGER IF EXISTS trg_update_revocation_list_timestamp_v0_1 "
        "ON revocation_list_v0_1;",
        "DROP FUNCTION IF EXISTS update_revocation_list_timestamp_v0_1 CASCADE;",
        "DROP TRIGGER IF EXISTS trg_update_revocation_list_revocations_v0_1 "
        "ON revocation_list_v0_1;",
        "DROP FUNCTION IF EXISTS update_revocation_list_revocations_v0_1 CASCADE;",
        "DROP TRIGGER IF EXISTS trg_update_revocation_list_fields_v0_1 "
        "ON revocation_list_v0_1;",
        "DROP FUNCTION IF EXISTS update_revocation_list_fields_v0_1 CASCADE;",
        "DROP TRIGGER IF EXISTS trg_insert_revocation_list_revocations_v0_1 "
        "ON revocation_list_v0_1;",
        "DROP FUNCTION IF EXISTS insert_revocation_list_revocations_v0_1 CASCADE;",
        "DROP TRIGGER IF EXISTS trg_insert_revocation_list_fields_v0_1 "
        "ON revocation_list_v0_1;",
        "DROP FUNCTION IF EXISTS insert_revocation_list_fields_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_revocation_list_revocations_revoked_index_v0_1;",
        "DROP TABLE IF EXISTS revocation_list_revocations_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_revocation_list_rev_reg_def_id_state_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_list_issuer_id_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_list_rev_reg_def_id_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_list_item_id_v0_1;",
        "DROP TABLE IF EXISTS revocation_list_v0_1 CASCADE;",
    ],
    "mssql": [
        "DROP TRIGGER IF EXISTS trg_update_revocation_list_timestamp_v0_1;",
        "DROP TRIGGER IF EXISTS trg_update_revocation_list_revocations_v0_1;",
        "DROP TRIGGER IF EXISTS trg_update_revocation_list_fields_v0_1;",
        "DROP TRIGGER IF EXISTS trg_insert_revocation_list_revocations_v0_1;",
        "DROP TRIGGER IF EXISTS trg_insert_revocation_list_fields_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_list_revocations_revoked_index_v0_1 "
        "ON revocation_list_revocations_v0_1;",
        "DROP TABLE IF EXISTS revocation_list_revocations_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_list_rev_reg_def_id_state_v0_1 "
        "ON revocation_list_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_list_issuer_id_v0_1 "
        "ON revocation_list_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_list_rev_reg_def_id_v0_1 "
        "ON revocation_list_v0_1;",
        "DROP INDEX IF EXISTS idx_revocation_list_item_id_v0_1 ON revocation_list_v0_1;",
        "DROP TABLE IF EXISTS revocation_list_v0_1;",
    ],
}

COLUMNS = ["rev_list", "next_index", "pending", "state"]
