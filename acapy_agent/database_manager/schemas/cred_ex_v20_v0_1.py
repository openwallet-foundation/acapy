"""Module docstring."""

CATEGORY = "cred_ex_v20"

SCHEMAS = {
    "sqlite": [
        """
        CREATE TABLE IF NOT EXISTS cred_ex_v20_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            connection_id TEXT,
            cred_def_id TEXT,
            thread_id TEXT NOT NULL,
            parent_thread_id TEXT,
            verification_method TEXT,
            initiator TEXT,
            role TEXT,
            state TEXT,
            cred_proposal TEXT,
            cred_offer TEXT,
            cred_request TEXT,
            cred_issue TEXT,
            auto_offer INTEGER,
            auto_issue INTEGER,
            auto_remove INTEGER,
            error_msg TEXT,
            trace INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT cred_ex_v20_v0_1_unique_item_id UNIQUE (item_id),
            CONSTRAINT cred_ex_v20_v0_1_unique_thread_id UNIQUE (thread_id)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_cred_ex_item_id_v0_1 "
        "ON cred_ex_v20_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_cred_ex_thread_id_v0_1 "
        "ON cred_ex_v20_v0_1 (thread_id);",
        """
        CREATE TABLE IF NOT EXISTS cred_ex_v20_attributes_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cred_ex_v20_id INTEGER NOT NULL,
            attr_name TEXT NOT NULL,
            attr_value TEXT NOT NULL,
            FOREIGN KEY (cred_ex_v20_id) REFERENCES cred_ex_v20_v0_1(id)
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_cred_ex_v20_attributes_attr_name_v0_1 "
        "ON cred_ex_v20_attributes_v0_1 (attr_name);",
        """
        CREATE TABLE IF NOT EXISTS cred_ex_v20_formats_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cred_ex_v20_id INTEGER NOT NULL,
            format_id TEXT NOT NULL,
            format_type TEXT,
            FOREIGN KEY (cred_ex_v20_id) REFERENCES cred_ex_v20_v0_1(id)
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_cred_ex_v20_formats_format_id_v0_1 "
        "ON cred_ex_v20_formats_v0_1 (format_id);",
        """
        CREATE TRIGGER IF NOT EXISTS trg_update_cred_ex_v20_timestamp_v0_1
        AFTER UPDATE ON cred_ex_v20_v0_1
        FOR EACH ROW
        BEGIN
            UPDATE cred_ex_v20_v0_1
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = OLD.id;
        END;
        """,
    ],
    "postgresql": [
        """
        CREATE TABLE IF NOT EXISTS cred_ex_v20_v0_1 (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            connection_id TEXT,
            cred_def_id TEXT,
            thread_id TEXT NOT NULL,
            parent_thread_id TEXT,
            verification_method TEXT,
            initiator TEXT,
            role TEXT,
            state TEXT,
            cred_proposal TEXT,
            cred_offer TEXT,
            cred_request TEXT,
            cred_issue TEXT,
            auto_offer BOOLEAN,
            auto_issue BOOLEAN,
            auto_remove BOOLEAN,
            error_msg TEXT,
            trace BOOLEAN,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT cred_ex_v20_v0_1_unique_item_id UNIQUE (item_id),
            CONSTRAINT cred_ex_v20_v0_1_unique_thread_id UNIQUE (thread_id)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_cred_ex_item_id_v0_1 "
        "ON cred_ex_v20_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_cred_ex_thread_id_v0_1 "
        "ON cred_ex_v20_v0_1 (thread_id);",
        """
        CREATE TABLE IF NOT EXISTS cred_ex_v20_attributes_v0_1 (
            id SERIAL PRIMARY KEY,
            cred_ex_v20_id INTEGER NOT NULL,
            attr_name TEXT NOT NULL,
            attr_value TEXT NOT NULL,
            CONSTRAINT fk_cred_ex_v20_id FOREIGN KEY (cred_ex_v20_id) 
                REFERENCES cred_ex_v20_v0_1(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_cred_ex_v20_attributes_attr_name_v0_1 "
        "ON cred_ex_v20_attributes_v0_1 (attr_name);",
        """
        CREATE TABLE IF NOT EXISTS cred_ex_v20_formats_v0_1 (
            id SERIAL PRIMARY KEY,
            cred_ex_v20_id INTEGER NOT NULL,
            format_id TEXT NOT NULL,
            format_type TEXT,
            CONSTRAINT fk_cred_ex_v20_id FOREIGN KEY (cred_ex_v20_id) 
                REFERENCES cred_ex_v20_v0_1(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_cred_ex_v20_formats_format_id_v0_1 "
        "ON cred_ex_v20_formats_v0_1 (format_id);",
        """
        CREATE OR REPLACE FUNCTION update_cred_ex_v20_timestamp_v0_1()
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
        CREATE TRIGGER trg_update_cred_ex_v20_timestamp_v0_1
        BEFORE UPDATE ON cred_ex_v20_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION update_cred_ex_v20_timestamp_v0_1();
        """,
    ],
    "mssql": [
        """
        CREATE TABLE cred_ex_v20_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            item_id INT NOT NULL,
            item_name NVARCHAR(MAX) NOT NULL,
            connection_id NVARCHAR(255),
            cred_def_id NVARCHAR(255),
            thread_id NVARCHAR(255) NOT NULL,
            parent_thread_id NVARCHAR(255),
            verification_method NVARCHAR(255),
            initiator NVARCHAR(255),
            role NVARCHAR(255),
            state NVARCHAR(255),
            cred_proposal NVARCHAR(MAX),
            cred_offer NVARCHAR(MAX),
            cred_request NVARCHAR(MAX),
            cred_issue NVARCHAR(MAX),
            auto_offer BIT,
            auto_issue BIT,
            auto_remove BIT,
            error_msg NVARCHAR(MAX),
            trace BIT,
            created_at DATETIME2 DEFAULT SYSDATETIME(),
            updated_at DATETIME2 DEFAULT SYSDATETIME(),
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT cred_ex_v20_v0_1_unique_item_id UNIQUE (item_id),
            CONSTRAINT cred_ex_v20_v0_1_unique_thread_id UNIQUE (thread_id)
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_cred_ex_item_id_v0_1 "
        "ON cred_ex_v20_v0_1 (item_id);",
        "CREATE NONCLUSTERED INDEX idx_cred_ex_thread_id_v0_1 "
        "ON cred_ex_v20_v0_1 (thread_id);",
        """
        CREATE TABLE cred_ex_v20_attributes_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            cred_ex_v20_id INT NOT NULL,
            attr_name NVARCHAR(MAX) NOT NULL,
            attr_value NVARCHAR(MAX) NOT NULL,
            CONSTRAINT fk_cred_ex_v20_id FOREIGN KEY (cred_ex_v20_id) 
                REFERENCES cred_ex_v20_v0_1(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_cred_ex_v20_attributes_attr_name_v0_1 "
        "ON cred_ex_v20_attributes_v0_1 (attr_name);",
        """
        CREATE TABLE cred_ex_v20_formats_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            cred_ex_v20_id INT NOT NULL,
            format_id NVARCHAR(255) NOT NULL,
            format_type NVARCHAR(255),
            CONSTRAINT fk_cred_ex_v20_id FOREIGN KEY (cred_ex_v20_id) 
                REFERENCES cred_ex_v20_v0_1(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_cred_ex_v20_formats_format_id_v0_1 "
        "ON cred_ex_v20_formats_v0_1 (format_id);",
        """
        CREATE TRIGGER trg_update_cred_ex_v20_timestamp_v0_1
        ON cred_ex_v20_v0_1
        AFTER UPDATE
        AS
        BEGIN
            UPDATE cred_ex_v20_v0_1
            SET updated_at = SYSDATETIME()
            FROM cred_ex_v20_v0_1
            INNER JOIN inserted ON cred_ex_v20_v0_1.id = inserted.id
            WHERE inserted.updated_at IS NULL;
        END;
        """,
    ],
}

DROP_SCHEMAS = {
    "sqlite": [
        "DROP TRIGGER IF EXISTS trg_update_cred_ex_v20_timestamp_v0_1;",
        "DROP INDEX IF EXISTS idx_cred_ex_v20_formats_format_id_v0_1;",
        "DROP TABLE IF EXISTS cred_ex_v20_formats_v0_1;",
        "DROP INDEX IF EXISTS idx_cred_ex_v20_attributes_attr_name_v0_1;",
        "DROP TABLE IF EXISTS cred_ex_v20_attributes_v0_1;",
        "DROP INDEX IF EXISTS idx_cred_ex_thread_id_v0_1;",
        "DROP INDEX IF EXISTS idx_cred_ex_item_id_v0_1;",
        "DROP TABLE IF EXISTS cred_ex_v20_v0_1;",
    ],
    "postgresql": [
        "DROP TRIGGER IF EXISTS trg_update_cred_ex_v20_timestamp_v0_1 "
        "ON cred_ex_v20_v0_1;",
        "DROP FUNCTION IF EXISTS update_cred_ex_v20_timestamp_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_cred_ex_v20_formats_format_id_v0_1;",
        "DROP TABLE IF EXISTS cred_ex_v20_formats_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_cred_ex_v20_attributes_attr_name_v0_1;",
        "DROP TABLE IF EXISTS cred_ex_v20_attributes_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_cred_ex_thread_id_v0_1;",
        "DROP INDEX IF EXISTS idx_cred_ex_item_id_v0_1;",
        "DROP TABLE IF EXISTS cred_ex_v20_v0_1 CASCADE;",
    ],
    "mssql": [
        "DROP TRIGGER IF EXISTS trg_update_cred_ex_v20_timestamp_v0_1;",
        "DROP INDEX IF EXISTS idx_cred_ex_v20_formats_format_id_v0_1 "
        "ON cred_ex_v20_formats_v0_1;",
        "DROP TABLE IF EXISTS cred_ex_v20_formats_v0_1;",
        "DROP INDEX IF EXISTS idx_cred_ex_v20_attributes_attr_name_v0_1 "
        "ON cred_ex_v20_attributes_v0_1;",
        "DROP TABLE IF EXISTS cred_ex_v20_attributes_v0_1;",
        "DROP INDEX IF EXISTS idx_cred_ex_thread_id_v0_1 ON cred_ex_v20_v0_1;",
        "DROP INDEX IF EXISTS idx_cred_ex_item_id_v0_1 ON cred_ex_v20_v0_1;",
        "DROP TABLE IF EXISTS cred_ex_v20_v0_1;",
    ],
}


COLUMNS = [
    "connection_id",
    "thread_id",
    "cred_def_id",
    "parent_thread_id",
    "verification_method",
    "initiator",
    "role",
    "state",
    "cred_proposal",
    "cred_offer",
    "cred_request",
    "cred_issue",
    "auto_offer",
    "auto_issue",
    "auto_remove",
    "error_msg",
    "trace",
    "created_at",
    "updated_at",
]
