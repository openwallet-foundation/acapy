"""Module docstring."""

CATEGORY = "connection_metadata"

SCHEMAS = {
    "sqlite": [
        """
        CREATE TABLE IF NOT EXISTS connection_metadata_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            key TEXT,
            connection_id TEXT,
            metadata TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT connection_metadata_v0_1_unique_item_name UNIQUE (item_name)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_connection_metadata_item_id_v0_1 "
        "ON connection_metadata_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_connection_metadata_item_name_v0_1 "
        "ON connection_metadata_v0_1 (item_name);",
        "CREATE INDEX IF NOT EXISTS idx_connection_metadata_key_v0_1 "
        "ON connection_metadata_v0_1 (key);",
        "CREATE INDEX IF NOT EXISTS idx_connection_metadata_connection_id_v0_1 "
        "ON connection_metadata_v0_1 (connection_id);",
        "CREATE INDEX IF NOT EXISTS idx_connection_metadata_created_at_v0_1 "
        "ON connection_metadata_v0_1 (created_at);",
        """
        CREATE TABLE IF NOT EXISTS connection_metadata_attributes_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            connection_metadata_id INTEGER NOT NULL,
            metadata_key TEXT NOT NULL,
            value TEXT NOT NULL,
            FOREIGN KEY (connection_metadata_id) 
                REFERENCES connection_metadata_v0_1(id) 
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS "
        "idx_connection_metadata_attributes_metadata_key_v0_1 "
        "ON connection_metadata_attributes_v0_1 (metadata_key);",
        """
        CREATE TRIGGER IF NOT EXISTS trg_insert_connection_metadata_attributes_v0_1
        AFTER INSERT ON connection_metadata_v0_1
        FOR EACH ROW
        WHEN NEW.metadata IS NOT NULL AND json_valid(NEW.metadata) 
             AND json_type(NEW.metadata) = 'object'
        BEGIN
            INSERT INTO connection_metadata_attributes_v0_1 (
                connection_metadata_id, metadata_key, value
            )
            SELECT
                NEW.id,
                key,
                json_extract(NEW.metadata, '$.' || key)
            FROM json_each(NEW.metadata)
            WHERE json_extract(NEW.metadata, '$.' || key) IS NOT NULL;
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS trg_update_connection_metadata_attributes_v0_1
        AFTER UPDATE ON connection_metadata_v0_1
        FOR EACH ROW
        WHEN NEW.metadata IS NOT NULL AND json_valid(NEW.metadata) 
             AND json_type(NEW.metadata) = 'object' AND NEW.metadata != OLD.metadata
        BEGIN
            DELETE FROM connection_metadata_attributes_v0_1 
            WHERE connection_metadata_id = OLD.id;
            INSERT INTO connection_metadata_attributes_v0_1 (
                connection_metadata_id, metadata_key, value
            )
            SELECT
                NEW.id,
                key,
                json_extract(NEW.metadata, '$.' || key)
            FROM json_each(NEW.metadata)
            WHERE json_extract(NEW.metadata, '$.' || key) IS NOT NULL;
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS trg_update_connection_metadata_timestamp_v0_1
        AFTER UPDATE ON connection_metadata_v0_1
        FOR EACH ROW
        BEGIN
            UPDATE connection_metadata_v0_1
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = OLD.id;
        END;
        """,
    ],
    "postgresql": [
        """
        CREATE TABLE IF NOT EXISTS connection_metadata_v0_1 (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            key TEXT,
            connection_id TEXT,
            metadata TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT connection_metadata_v0_1_unique_item_name UNIQUE (item_name)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_connection_metadata_item_id_v0_1 "
        "ON connection_metadata_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_connection_metadata_item_name_v0_1 "
        "ON connection_metadata_v0_1 (item_name);",
        "CREATE INDEX IF NOT EXISTS idx_connection_metadata_key_v0_1 "
        "ON connection_metadata_v0_1 (key);",
        "CREATE INDEX IF NOT EXISTS idx_connection_metadata_connection_id_v0_1 "
        "ON connection_metadata_v0_1 (connection_id);",
        "CREATE INDEX IF NOT EXISTS idx_connection_metadata_created_at_v0_1 "
        "ON connection_metadata_v0_1 (created_at);",
        """
        CREATE TABLE IF NOT EXISTS connection_metadata_attributes_v0_1 (
            id SERIAL PRIMARY KEY,
            connection_metadata_id INTEGER NOT NULL,
            metadata_key TEXT NOT NULL,
            value TEXT NOT NULL,
            CONSTRAINT fk_connection_metadata_id FOREIGN KEY (connection_metadata_id) 
                REFERENCES connection_metadata_v0_1(id) 
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS "
        "idx_connection_metadata_attributes_metadata_key_v0_1 "
        "ON connection_metadata_attributes_v0_1 (metadata_key);",
        """
        CREATE OR REPLACE FUNCTION insert_connection_metadata_attributes_v0_1()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.metadata IS NOT NULL AND NEW.metadata::jsonb IS NOT NULL 
               AND jsonb_typeof(NEW.metadata::jsonb) = 'object' THEN
                INSERT INTO connection_metadata_attributes_v0_1 (
                connection_metadata_id, metadata_key, value
            )
                SELECT
                    NEW.id,
                    key,
                    value::text
                FROM jsonb_each_text(NEW.metadata::jsonb);
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        CREATE TRIGGER trg_insert_connection_metadata_attributes_v0_1
        AFTER INSERT ON connection_metadata_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION insert_connection_metadata_attributes_v0_1();
        """,
        """
        CREATE OR REPLACE FUNCTION update_connection_metadata_attributes_v0_1()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.metadata IS NOT NULL AND NEW.metadata::jsonb IS NOT NULL 
               AND jsonb_typeof(NEW.metadata::jsonb) = 'object' 
               AND NEW.metadata != OLD.metadata THEN
                DELETE FROM connection_metadata_attributes_v0_1 
            WHERE connection_metadata_id = OLD.id;
                INSERT INTO connection_metadata_attributes_v0_1 (
                connection_metadata_id, metadata_key, value
            )
                SELECT
                    NEW.id,
                    key,
                    value::text
                FROM jsonb_each_text(NEW.metadata::jsonb);
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        CREATE TRIGGER trg_update_connection_metadata_attributes_v0_1
        AFTER UPDATE ON connection_metadata_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION update_connection_metadata_attributes_v0_1();
        """,
        """
        CREATE OR REPLACE FUNCTION update_connection_metadata_timestamp_v0_1()
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
        CREATE TRIGGER trg_update_connection_metadata_timestamp_v0_1
        BEFORE UPDATE ON connection_metadata_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION update_connection_metadata_timestamp_v0_1();
        """,
    ],
    "mssql": [
        """
        CREATE TABLE connection_metadata_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            item_id INT NOT NULL,
            item_name NVARCHAR(MAX) NOT NULL,
            key NVARCHAR(255),
            connection_id NVARCHAR(255),
            metadata NVARCHAR(MAX),
            created_at DATETIME2 DEFAULT SYSDATETIME(),
            updated_at DATETIME2 DEFAULT SYSDATETIME(),
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT connection_metadata_v0_1_unique_item_name UNIQUE (item_name)
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_connection_metadata_item_id_v0_1 "
        "ON connection_metadata_v0_1 (item_id);",
        "CREATE NONCLUSTERED INDEX idx_connection_metadata_item_name_v0_1 "
        "ON connection_metadata_v0_1 (item_name);",
        "CREATE NONCLUSTERED INDEX idx_connection_metadata_key_v0_1 "
        "ON connection_metadata_v0_1 (key);",
        "CREATE NONCLUSTERED INDEX idx_connection_metadata_connection_id_v0_1 "
        "ON connection_metadata_v0_1 (connection_id);",
        "CREATE NONCLUSTERED INDEX idx_connection_metadata_created_at_v0_1 "
        "ON connection_metadata_v0_1 (created_at);"
        """
        CREATE TABLE connection_metadata_attributes_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            connection_metadata_id INT NOT NULL,
            metadata_key NVARCHAR(MAX) NOT NULL,
            value NVARCHAR(MAX) NOT NULL,
            CONSTRAINT fk_connection_metadata_id FOREIGN KEY (connection_metadata_id) 
                REFERENCES connection_metadata_v0_1(id) 
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE NONCLUSTERED INDEX "
        "idx_connection_metadata_attributes_metadata_key_v0_1 "
        "ON connection_metadata_attributes_v0_1 (metadata_key);"
        """
        CREATE TRIGGER trg_insert_connection_metadata_attributes_v0_1
        ON connection_metadata_v0_1
        AFTER INSERT
        AS
        BEGIN
            INSERT INTO connection_metadata_attributes_v0_1 (
                connection_metadata_id, metadata_key, value
            )
            SELECT
                i.id,
                j.[key],
                j.value
            FROM inserted i
            CROSS APPLY OPENJSON(i.metadata) j
            WHERE i.metadata IS NOT NULL AND ISJSON(i.metadata) = 1;
        END;
        """,
        """
        CREATE TRIGGER trg_update_connection_metadata_attributes_v0_1
        ON connection_metadata_v0_1
        AFTER UPDATE
        AS
        BEGIN
            DELETE FROM connection_metadata_attributes_v0_1
            WHERE connection_metadata_id IN (SELECT id FROM deleted)
              AND EXISTS (
                  SELECT 1
                  FROM inserted i
                  WHERE i.id = deleted.id
                    AND i.metadata IS NOT NULL
                    AND ISJSON(i.metadata) = 1
                    AND i.metadata != deleted.metadata
              );

            INSERT INTO connection_metadata_attributes_v0_1 (
                connection_metadata_id, metadata_key, value
            )
            SELECT
                i.id,
                j.[key],
                j.value
            FROM inserted i
            CROSS APPLY OPENJSON(i.metadata) j
            WHERE i.metadata IS NOT NULL
              AND ISJSON(i.metadata) = 1
              AND EXISTS (
                  SELECT 1
                  FROM deleted d
                  WHERE d.id = i.id
                    AND i.metadata != d.metadata
              );
        END;
        """,
        """
        CREATE TRIGGER trg_update_connection_metadata_timestamp_v0_1
        ON connection_metadata_v0_1
        AFTER UPDATE
        AS
        BEGIN
            UPDATE connection_metadata_v0_1
            SET updated_at = SYSDATETIME()
            FROM connection_metadata_v0_1
            INNER JOIN inserted ON connection_metadata_v0_1.id = inserted.id
            WHERE inserted.updated_at IS NULL;
        END;
        """,
    ],
}


DROP_SCHEMAS = {
    "sqlite": [
        "DROP TRIGGER IF EXISTS trg_update_connection_metadata_timestamp_v0_1;",
        "DROP TRIGGER IF EXISTS trg_update_connection_metadata_attributes_v0_1;",
        "DROP TRIGGER IF EXISTS trg_insert_connection_metadata_attributes_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_metadata_attributes_metadata_key_v0_1;",
        "DROP TABLE IF EXISTS connection_metadata_attributes_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_metadata_created_at_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_metadata_connection_id_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_metadata_key_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_metadata_item_name_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_metadata_item_id_v0_1;",
        "DROP TABLE IF EXISTS connection_metadata_v0_1;",
    ],
    "postgresql": [
        "DROP TRIGGER IF EXISTS trg_update_connection_metadata_timestamp_v0_1 "
        "ON connection_metadata_v0_1;",
        "DROP FUNCTION IF EXISTS update_connection_metadata_timestamp_v0_1 CASCADE;",
        "DROP TRIGGER IF EXISTS trg_update_connection_metadata_attributes_v0_1 "
        "ON connection_metadata_v0_1;",
        "DROP FUNCTION IF EXISTS update_connection_metadata_attributes_v0_1 CASCADE;",
        "DROP TRIGGER IF EXISTS trg_insert_connection_metadata_attributes_v0_1 "
        "ON connection_metadata_v0_1;"
        "DROP FUNCTION IF EXISTS insert_connection_metadata_attributes_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_connection_metadata_attributes_metadata_key_v0_1;",
        "DROP TABLE IF EXISTS connection_metadata_attributes_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_connection_metadata_created_at_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_metadata_connection_id_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_metadata_key_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_metadata_item_name_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_metadata_item_id_v0_1;",
        "DROP TABLE IF EXISTS connection_metadata_v0_1 CASCADE;",
    ],
    "mssql": [
        "DROP TRIGGER IF EXISTS trg_update_connection_metadata_timestamp_v0_1;",
        "DROP TRIGGER IF EXISTS trg_update_connection_metadata_attributes_v0_1;",
        "DROP TRIGGER IF EXISTS trg_insert_connection_metadata_attributes_v0_1;",
        "DROP INDEX IF EXISTS "
        "idx_connection_metadata_attributes_metadata_key_v0_1 "
        "ON connection_metadata_attributes_v0_1;",
        "DROP TABLE IF EXISTS connection_metadata_attributes_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_metadata_created_at_v0_1 "
        "ON connection_metadata_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_metadata_connection_id_v0_1 "
        "ON connection_metadata_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_metadata_key_v0_1 "
        "ON connection_metadata_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_metadata_item_name_v0_1 "
        "ON connection_metadata_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_metadata_item_id_v0_1 "
        "ON connection_metadata_v0_1;"
        "DROP TABLE IF EXISTS connection_metadata_v0_1;",
    ],
}

COLUMNS = ["key", "connection_id", "metadata"]
