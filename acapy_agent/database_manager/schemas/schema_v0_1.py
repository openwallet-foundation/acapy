"""Module docstring."""

CATEGORY = "schema"

IDX_SCHEMA_ON_ITEM_ID = "ON schema_v0_1 (item_id);"
IDX_SCHEMA_ON_ITEM_NAME = "ON schema_v0_1 (item_name);"
IDX_SCHEMA_ON_ISSUER_ID = "ON schema_v0_1 (issuer_id);"
IDX_SCHEMA_ON_NAME_VERSION = "ON schema_v0_1 (name, version);"
IDX_SCHEMA_ON_STATE = "ON schema_v0_1 (state);"
IDX_SCHEMA_ATTR_ON_ATTR_NAME = "ON schema_attributes_v0_1 (attr_name);"
SCHEMAS = {
    "sqlite": [
        """
        CREATE TABLE IF NOT EXISTS schema_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            item_name TEXT,
            version TEXT,
            name TEXT,
            issuer_id TEXT,
            state TEXT,
            attrNames TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT schema_v0_1_unique_item_id UNIQUE (item_id)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_schema_item_id_v0_1 " + IDX_SCHEMA_ON_ITEM_ID,
        "CREATE INDEX IF NOT EXISTS idx_schema_schema_id_v0_1 " + IDX_SCHEMA_ON_ITEM_NAME,
        "CREATE INDEX IF NOT EXISTS idx_schema_issuer_id_v0_1 " + IDX_SCHEMA_ON_ISSUER_ID,
        "CREATE INDEX IF NOT EXISTS idx_schema_name_version_v0_1 "
        + IDX_SCHEMA_ON_NAME_VERSION,
        "CREATE INDEX IF NOT EXISTS idx_schema_state_v0_1 " + IDX_SCHEMA_ON_STATE,
        """
        CREATE TABLE IF NOT EXISTS schema_attributes_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schema_id INTEGER NOT NULL,
            attr_name TEXT NOT NULL,
            FOREIGN KEY (schema_id) REFERENCES schema_v0_1(id) 
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_schema_attributes_attr_name_v0_1 "
        + IDX_SCHEMA_ATTR_ON_ATTR_NAME,
        """
        CREATE TRIGGER IF NOT EXISTS trg_insert_schema_attributes_v0_1
        AFTER INSERT ON schema_v0_1
        FOR EACH ROW
        WHEN NEW.attrNames IS NOT NULL AND json_valid(NEW.attrNames)
        BEGIN
            INSERT INTO schema_attributes_v0_1 (schema_id, attr_name)
            SELECT NEW.id, value
            FROM json_each(NEW.attrNames);
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS trg_update_schema_attributes_v0_1
        AFTER UPDATE ON schema_v0_1
        FOR EACH ROW
        WHEN NEW.attrNames IS NOT NULL AND json_valid(NEW.attrNames) 
            AND NEW.attrNames != OLD.attrNames
        BEGIN
            DELETE FROM schema_attributes_v0_1 WHERE schema_id = OLD.id;
            INSERT INTO schema_attributes_v0_1 (schema_id, attr_name)
            SELECT NEW.id, value
            FROM json_each(NEW.attrNames);
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS trg_update_schema_timestamp_v0_1
        AFTER UPDATE ON schema_v0_1
        FOR EACH ROW
        BEGIN
            UPDATE schema_v0_1
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = OLD.id;
        END;
        """,
    ],
    "postgresql": [
        """
        CREATE TABLE IF NOT EXISTS schema_v0_1 (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            item_name TEXT,
            version TEXT,
            name TEXT,
            issuer_id TEXT,
            state TEXT,
            attrNames TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT schema_v0_1_unique_item_id UNIQUE (item_id)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_schema_item_id_v0_1 " + IDX_SCHEMA_ON_ITEM_ID,
        "CREATE INDEX IF NOT EXISTS idx_schema_schema_id_v0_1 " + IDX_SCHEMA_ON_ITEM_NAME,
        "CREATE INDEX IF NOT EXISTS idx_schema_issuer_id_v0_1 " + IDX_SCHEMA_ON_ISSUER_ID,
        "CREATE INDEX IF NOT EXISTS idx_schema_name_version_v0_1 "
        + IDX_SCHEMA_ON_NAME_VERSION,
        "CREATE INDEX IF NOT EXISTS idx_schema_state_v0_1 " + IDX_SCHEMA_ON_STATE,
        """
        CREATE TABLE IF NOT EXISTS schema_attributes_v0_1 (
            id SERIAL PRIMARY KEY,
            schema_id INTEGER NOT NULL,
            attr_name TEXT NOT NULL,
            CONSTRAINT fk_schema_id FOREIGN KEY (schema_id) 
                REFERENCES schema_v0_1(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_schema_attributes_attr_name_v0_1 "
        + IDX_SCHEMA_ATTR_ON_ATTR_NAME,
        """
        CREATE OR REPLACE FUNCTION insert_schema_attributes_v0_1()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.attrNames IS NOT NULL AND NEW.attrNames::jsonb IS NOT NULL THEN
                INSERT INTO schema_attributes_v0_1 (schema_id, attr_name)
                SELECT NEW.id, value
                FROM jsonb_array_elements_text(NEW.attrNames::jsonb) AS value;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        CREATE TRIGGER trg_insert_schema_attributes_v0_1
        AFTER INSERT ON schema_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION insert_schema_attributes_v0_1();
        """,
        """
        CREATE OR REPLACE FUNCTION update_schema_attributes_v0_1()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.attrNames IS NOT NULL AND NEW.attrNames::jsonb IS NOT NULL 
                AND NEW.attrNames != OLD.attrNames THEN
                DELETE FROM schema_attributes_v0_1 WHERE schema_id = OLD.id;
                INSERT INTO schema_attributes_v0_1 (schema_id, attr_name)
                SELECT NEW.id, value
                FROM jsonb_array_elements_text(NEW.attrNames::jsonb) AS value;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        CREATE TRIGGER trg_update_schema_attributes_v0_1
        AFTER UPDATE ON schema_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION update_schema_attributes_v0_1();
        """,
        """
        CREATE OR REPLACE FUNCTION update_schema_timestamp_v0_1()
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
        CREATE TRIGGER trg_update_schema_timestamp_v0_1
        BEFORE UPDATE ON schema_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION update_schema_timestamp_v0_1();
        """,
    ],
    "mssql": [
        """
        CREATE TABLE schema_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            item_id INT NOT NULL,
            item_name NVARCHAR(MAX),
            version NVARCHAR(50),
            name NVARCHAR(MAX),
            issuer_id NVARCHAR(255),
            state NVARCHAR(255),
            attrNames NVARCHAR(MAX),
            created_at DATETIME2 DEFAULT SYSDATETIME(),
            updated_at DATETIME2 DEFAULT SYSDATETIME(),
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT schema_v0_1_unique_item_id UNIQUE (item_id)
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_schema_item_id_v0_1 " + IDX_SCHEMA_ON_ITEM_ID,
        "CREATE NONCLUSTERED INDEX idx_schema_schema_id_v0_1 " + IDX_SCHEMA_ON_ITEM_NAME,
        "CREATE NONCLUSTERED INDEX idx_schema_issuer_id_v0_1 " + IDX_SCHEMA_ON_ISSUER_ID,
        "CREATE NONCLUSTERED INDEX idx_schema_name_version_v0_1 "
        + IDX_SCHEMA_ON_NAME_VERSION,
        "CREATE NONCLUSTERED INDEX idx_schema_state_v0_1 " + IDX_SCHEMA_ON_STATE,
        """
        CREATE TABLE schema_attributes_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            schema_id INT NOT NULL,
            attr_name NVARCHAR(MAX) NOT NULL,
            CONSTRAINT fk_schema_id FOREIGN KEY (schema_id) 
                REFERENCES schema_v0_1(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_schema_attributes_attr_name_v0_1 "
        + IDX_SCHEMA_ATTR_ON_ATTR_NAME,
        """
        CREATE TRIGGER trg_insert_schema_attributes_v0_1
        ON schema_v0_1
        AFTER INSERT
        AS
        BEGIN
            INSERT INTO schema_attributes_v0_1 (schema_id, attr_name)
            SELECT i.id, j.value
            FROM inserted i
            CROSS APPLY OPENJSON(i.attrNames) j
            WHERE i.attrNames IS NOT NULL AND ISJSON(i.attrNames) = 1;
        END;
        """,
        """
        CREATE TRIGGER trg_update_schema_attributes_v0_1
        ON schema_v0_1
        AFTER UPDATE
        AS
        BEGIN
            DELETE FROM schema_attributes_v0_1
            WHERE schema_id IN (
                SELECT i.id
                FROM inserted i
                INNER JOIN deleted d ON i.id = d.id
                WHERE i.attrNames IS NOT NULL
                  AND ISJSON(i.attrNames) = 1
                  AND i.attrNames != d.attrNames
            );

            INSERT INTO schema_attributes_v0_1 (schema_id, attr_name)
            SELECT i.id, j.value
            FROM inserted i
            CROSS APPLY OPENJSON(i.attrNames) j
            WHERE i.attrNames IS NOT NULL
              AND ISJSON(i.attrNames) = 1
              AND i.attrNames != (SELECT d.attrNames FROM deleted d WHERE d.id = i.id);
        END;
        """,
        """
        CREATE TRIGGER trg_update_schema_timestamp_v0_1
        ON schema_v0_1
        AFTER UPDATE
        AS
        BEGIN
            UPDATE schema_v0_1
            SET updated_at = SYSDATETIME()
            FROM schema_v0_1
            INNER JOIN inserted ON schema_v0_1.id = inserted.id
            WHERE inserted.updated_at IS NULL;
        END;
        """,
    ],
}

DROP_SCHEMAS = {
    "sqlite": [
        "DROP TRIGGER IF EXISTS trg_update_schema_timestamp_v0_1;",
        "DROP TRIGGER IF EXISTS trg_update_schema_attributes_v0_1;",
        "DROP TRIGGER IF EXISTS trg_insert_schema_attributes_v0_1;",
        "DROP INDEX IF EXISTS idx_schema_attributes_attr_name_v0_1;",
        "DROP TABLE IF EXISTS schema_attributes_v0_1;",
        "DROP INDEX IF EXISTS idx_schema_state_v0_1;",
        "DROP INDEX IF EXISTS idx_schema_name_version_v0_1;",
        "DROP INDEX IF EXISTS idx_schema_issuer_id_v0_1;",
        "DROP INDEX IF EXISTS idx_schema_schema_id_v0_1;",
        "DROP INDEX IF EXISTS idx_schema_item_id_v0_1;",
        "DROP TABLE IF EXISTS schema_v0_1;",
    ],
    "postgresql": [
        "DROP TRIGGER IF EXISTS trg_update_schema_timestamp_v0_1 ON schema_v0_1;",
        "DROP FUNCTION IF EXISTS update_schema_timestamp_v0_1 CASCADE;",
        "DROP TRIGGER IF EXISTS trg_update_schema_attributes_v0_1 ON schema_v0_1;",
        "DROP FUNCTION IF EXISTS update_schema_attributes_v0_1 CASCADE;",
        "DROP TRIGGER IF EXISTS trg_insert_schema_attributes_v0_1 ON schema_v0_1;",
        "DROP FUNCTION IF EXISTS insert_schema_attributes_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_schema_attributes_attr_name_v0_1;",
        "DROP TABLE IF EXISTS schema_attributes_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_schema_state_v0_1;",
        "DROP INDEX IF EXISTS idx_schema_name_version_v0_1;",
        "DROP INDEX IF EXISTS idx_schema_issuer_id_v0_1;",
        "DROP INDEX IF EXISTS idx_schema_schema_id_v0_1;",
        "DROP INDEX IF EXISTS idx_schema_item_id_v0_1;",
        "DROP TABLE IF EXISTS schema_v0_1 CASCADE;",
    ],
    "mssql": [
        "DROP TRIGGER IF EXISTS trg_update_schema_timestamp_v0_1;",
        "DROP TRIGGER IF EXISTS trg_update_schema_attributes_v0_1;",
        "DROP TRIGGER IF EXISTS trg_insert_schema_attributes_v0_1;",
        "DROP INDEX IF EXISTS idx_schema_attributes_attr_name_v0_1 "
        + "ON schema_attributes_v0_1;",
        "DROP TABLE IF EXISTS schema_attributes_v0_1;",
        "DROP INDEX IF EXISTS idx_schema_state_v0_1 ON schema_v0_1;",
        "DROP INDEX IF EXISTS idx_schema_name_version_v0_1 ON schema_v0_1;",
        "DROP INDEX IF EXISTS idx_schema_issuer_id_v0_1 ON schema_v0_1;",
        "DROP INDEX IF EXISTS idx_schema_schema_id_v0_1 ON schema_v0_1;",
        "DROP INDEX IF EXISTS idx_schema_item_id_v0_1 ON schema_v0_1;",
        "DROP TABLE IF EXISTS schema_v0_1;",
    ],
}

COLUMNS = ["version", "name", "attrNames", "issuer_id", "state"]


# category=schema, name=BacujJ3zNmAR9afs9hPryb:2:person-demo-schema:0.029,
# value={"issuerId": "BacujJ3zNmAR9afs9hPryb",
#        "attrNames": ["person.name.family", "person.name.given", "person.birthDate"],
#        "name": "person-demo-schema", "version": "0.029"},
#  tags={'name': 'person-demo-schema', 'version': '0.029',
#        'issuer_id': 'BacujJ3zNmAR9afs9hPryb', 'state': 'finished'}
