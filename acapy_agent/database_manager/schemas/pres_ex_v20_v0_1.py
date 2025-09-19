"""Module docstring."""

CATEGORY = "pres_ex_v20"

SCHEMAS = {
    "sqlite": [
        """
        CREATE TABLE IF NOT EXISTS pres_ex_v20_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            connection_id TEXT,
            thread_id TEXT,
            initiator TEXT,
            role TEXT,
            state TEXT,
            pres_request TEXT,
            pres TEXT,
            revealed_attr_groups TEXT,
            verified TEXT,
            verified_msgs TEXT,
            auto_present TEXT,
            auto_verify TEXT,
            auto_remove TEXT,
            error_msg TEXT,
            trace TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_pres_ex_item_id_v0_1 "
        "ON pres_ex_v20_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_pres_ex_thread_id_v0_1 "
        "ON pres_ex_v20_v0_1 (thread_id);",
        """
        CREATE TABLE IF NOT EXISTS pres_ex_v20_revealed_attr_groups_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            presentation_id INTEGER NOT NULL,
            attr_name TEXT NOT NULL,
            attr_value TEXT NOT NULL,
            FOREIGN KEY (presentation_id) REFERENCES pres_ex_v20_v0_1(id)
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS "
        "idx_pres_ex_v20_revealed_attr_groups_attr_name_v0_1 "
        "ON pres_ex_v20_revealed_attr_groups_v0_1 (attr_name);",
        """
        CREATE TRIGGER IF NOT EXISTS trg_insert_pres_ex_v20_revealed_attr_groups_v0_1
        AFTER INSERT ON pres_ex_v20_v0_1
        FOR EACH ROW
        WHEN NEW.revealed_attr_groups IS NOT NULL AND json_valid(NEW.revealed_attr_groups)
        BEGIN
            INSERT INTO pres_ex_v20_revealed_attr_groups_v0_1 (
                presentation_id, attr_name, attr_value
            )
            SELECT NEW.id, json_extract(value, '$.attr_name'), 
                json_extract(value, '$.attr_value')
            FROM json_each(NEW.revealed_attr_groups);
        END;
        """,
    ],
    "postgresql": [
        """
        CREATE TABLE IF NOT EXISTS pres_ex_v20_v0_1 (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            connection_id TEXT,
            thread_id TEXT,
            initiator TEXT,
            role TEXT,
            state TEXT,
            pres_request TEXT,
            pres TEXT,
            revealed_attr_groups TEXT,
            verified TEXT,
            verified_msgs TEXT,
            auto_present TEXT,
            auto_verify TEXT,
            auto_remove TEXT,
            error_msg TEXT,
            trace TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id)
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_pres_ex_item_id_v0_1 "
        "ON pres_ex_v20_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_pres_ex_thread_id_v0_1 "
        "ON pres_ex_v20_v0_1 (thread_id);",
        """
        CREATE TABLE IF NOT EXISTS pres_ex_v20_revealed_attr_groups_v0_1 (
            id SERIAL PRIMARY KEY,
            presentation_id INTEGER NOT NULL,
            attr_name TEXT NOT NULL,
            attr_value TEXT NOT NULL,
            CONSTRAINT fk_presentation_id FOREIGN KEY (presentation_id) 
                REFERENCES pres_ex_v20_v0_1(id)
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS "
        "idx_pres_ex_v20_revealed_attr_groups_attr_name_v0_1 "
        "ON pres_ex_v20_revealed_attr_groups_v0_1 (attr_name);",
        """
        CREATE OR REPLACE FUNCTION insert_pres_ex_v20_revealed_attr_groups_v0_1()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.revealed_attr_groups IS NOT NULL AND 
                NEW.revealed_attr_groups::jsonb IS NOT NULL THEN
                INSERT INTO pres_ex_v20_revealed_attr_groups_v0_1 (
                    presentation_id, attr_name, attr_value
                )
                SELECT
                    NEW.id,
                    jsonb_extract_path_text(value, 'attr_name'),
                    jsonb_extract_path_text(value, 'attr_value')
                FROM jsonb_array_elements(NEW.revealed_attr_groups::jsonb) AS value
                WHERE jsonb_extract_path_text(value, 'attr_name') IS NOT NULL
                  AND jsonb_extract_path_text(value, 'attr_value') IS NOT NULL;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        CREATE TRIGGER trg_insert_pres_ex_v20_revealed_attr_groups_v0_1
        AFTER INSERT ON pres_ex_v20_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION insert_pres_ex_v20_revealed_attr_groups_v0_1();
        """,
    ],
    "mssql": [
        """
        CREATE TABLE pres_ex_v20_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            item_id INT NOT NULL,
            item_name NVARCHAR(MAX) NOT NULL,
            connection_id NVARCHAR(255),
            thread_id NVARCHAR(255),
            initiator NVARCHAR(255),
            role NVARCHAR(255),
            state NVARCHAR(255),
            pres_request NVARCHAR(MAX),
            pres NVARCHAR(MAX),
            revealed_attr_groups NVARCHAR(MAX),
            verified NVARCHAR(255),
            verified_msgs NVARCHAR(MAX),
            auto_present NVARCHAR(50),
            auto_verify NVARCHAR(50),
            auto_remove NVARCHAR(50),
            error_msg NVARCHAR(MAX),
            trace NVARCHAR(50),
            created_at DATETIME2 DEFAULT SYSDATETIME(),
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id)
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_pres_ex_item_id_v0_1 "
        "ON pres_ex_v20_v0_1 (item_id);",
        "CREATE NONCLUSTERED INDEX idx_pres_ex_thread_id_v0_1 "
        "ON pres_ex_v20_v0_1 (thread_id);",
        """
        CREATE TABLE pres_ex_v20_revealed_attr_groups_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            presentation_id INT NOT NULL,
            attr_name NVARCHAR(MAX) NOT NULL,
            attr_value NVARCHAR(MAX) NOT NULL,
            CONSTRAINT fk_presentation_id FOREIGN KEY (presentation_id) 
                REFERENCES pres_ex_v20_v0_1(id)
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_pres_ex_v20_revealed_attr_groups_attr_name_v0_1 "
        "ON pres_ex_v20_revealed_attr_groups_v0_1 (attr_name);",
        """
        CREATE TRIGGER trg_insert_pres_ex_v20_revealed_attr_groups_v0_1
        ON pres_ex_v20_v0_1
        AFTER INSERT
        AS
        BEGIN
            INSERT INTO pres_ex_v20_revealed_attr_groups_v0_1 (
                presentation_id, attr_name, attr_value
            )
            SELECT
                i.id,
                JSON_VALUE(v.value, '$.attr_name'),
                JSON_VALUE(v.value, '$.attr_value')
            FROM inserted i
            CROSS APPLY OPENJSON(i.revealed_attr_groups) v
            WHERE i.revealed_attr_groups IS NOT NULL
              AND ISJSON(i.revealed_attr_groups) = 1
              AND JSON_VALUE(v.value, '$.attr_name') IS NOT NULL
              AND JSON_VALUE(v.value, '$.attr_value') IS NOT NULL;
        END;
        """,
    ],
}


DROP_SCHEMAS = {
    "sqlite": [
        "DROP TRIGGER IF EXISTS trg_insert_pres_ex_v20_revealed_attr_groups_v0_1;",
        "DROP INDEX IF EXISTS idx_pres_ex_v20_revealed_attr_groups_attr_name_v0_1;",
        "DROP TABLE IF EXISTS pres_ex_v20_revealed_attr_groups_v0_1;",
        "DROP INDEX IF EXISTS idx_pres_ex_thread_id_v0_1;",
        "DROP INDEX IF EXISTS idx_pres_ex_item_id_v0_1;",
        "DROP TABLE IF EXISTS pres_ex_v20_v0_1;",
    ],
    "postgresql": [
        "DROP TRIGGER IF EXISTS trg_insert_pres_ex_v20_revealed_attr_groups_v0_1 "
        "ON pres_ex_v20_v0_1;",
        "DROP FUNCTION IF EXISTS insert_pres_ex_v20_revealed_attr_groups_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_pres_ex_v20_revealed_attr_groups_attr_name_v0_1;",
        "DROP TABLE IF EXISTS pres_ex_v20_revealed_attr_groups_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_pres_ex_thread_id_v0_1;",
        "DROP INDEX IF EXISTS idx_pres_ex_item_id_v0_1;",
        "DROP TABLE IF EXISTS pres_ex_v20_v0_1 CASCADE;",
    ],
    "mssql": [
        "DROP TRIGGER IF EXISTS trg_insert_pres_ex_v20_revealed_attr_groups_v0_1;",
        "DROP INDEX IF EXISTS idx_pres_ex_v20_revealed_attr_groups_attr_name_v0_1 "
        "ON pres_ex_v20_revealed_attr_groups_v0_1;",
        "DROP TABLE IF EXISTS pres_ex_v20_revealed_attr_groups_v0_1;",
        "DROP INDEX IF EXISTS idx_pres_ex_thread_id_v0_1 ON pres_ex_v20_v0_1;",
        "DROP INDEX IF EXISTS idx_pres_ex_item_id_v0_1 ON pres_ex_v20_v0_1;",
        "DROP TABLE IF EXISTS pres_ex_v20_v0_1;",
    ],
}

COLUMNS = [
    "connection_id",
    "thread_id",
    "initiator",
    "role",
    "state",
    "pres_request",
    "pres",
    "revealed_attr_groups",
    "verified",
    "verified_msgs",
    "auto_present",
    "auto_verify",
    "auto_remove",
    "error_msg",
    "trace",
]
