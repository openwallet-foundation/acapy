"""Module docstring."""

CATEGORY = "connection"

SCHEMAS = {
    "sqlite": [
        """
        CREATE TABLE IF NOT EXISTS connection_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            item_name TEXT,
            state TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            my_did TEXT,
            their_did TEXT,
            their_label TEXT,
            their_role TEXT,
            invitation_key TEXT,
            invitation_msg_id TEXT,
            request_id TEXT,
            inbound_connection_id TEXT,
            error_msg TEXT,
            accept TEXT,
            invitation_mode TEXT,
            alias TEXT,
            their_public_did TEXT,
            connection_protocol TEXT,
            rfc23_state TEXT,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_connection_item_id_v0_1
        ON connection_v0_1 (item_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_connection_state_v0_1
        ON connection_v0_1 (state);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_connection_created_at_v0_1
        ON connection_v0_1 (created_at);
        """,
        """
        CREATE TRIGGER IF NOT EXISTS trg_update_connection_timestamp_v0_1
        AFTER UPDATE ON connection_v0_1
        FOR EACH ROW
        BEGIN
            UPDATE connection_v0_1
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = OLD.id;
        END;
        """,
    ],
    "postgresql": [
        """
        CREATE TABLE IF NOT EXISTS connection_v0_1 (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            item_name TEXT,
            state TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            my_did TEXT,
            their_did TEXT,
            their_label TEXT,
            their_role TEXT,
            invitation_key TEXT,
            invitation_msg_id TEXT,
            request_id TEXT,
            inbound_connection_id TEXT,
            error_msg TEXT,
            accept TEXT,
            invitation_mode TEXT,
            alias TEXT,
            their_public_did TEXT,
            connection_protocol TEXT,
            rfc23_state TEXT,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id)
            REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_connection_item_id_v0_1
        ON connection_v0_1 (item_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_connection_state_v0_1
        ON connection_v0_1 (state);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_connection_created_at_v0_1
        ON connection_v0_1 (created_at);
        """,
        """
        CREATE OR REPLACE FUNCTION update_connection_timestamp_v0_1()
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
        CREATE TRIGGER trg_update_connection_timestamp_v0_1
        BEFORE UPDATE ON connection_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION update_connection_timestamp_v0_1();
        """,
    ],
    "mssql": [
        """
        CREATE TABLE connection_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            item_id INT NOT NULL,
            item_name NVARCHAR(MAX),
            state NVARCHAR(255),
            created_at DATETIME2 DEFAULT SYSDATETIME(),
            updated_at DATETIME2 DEFAULT SYSDATETIME(),
            my_did NVARCHAR(255),
            their_did NVARCHAR(255),
            their_label NVARCHAR(MAX),
            their_role NVARCHAR(255),
            invitation_key NVARCHAR(255),
            invitation_msg_id NVARCHAR(255),
            request_id NVARCHAR(255),
            inbound_connection_id NVARCHAR(255),
            error_msg NVARCHAR(MAX),
            accept NVARCHAR(255),
            invitation_mode NVARCHAR(255),
            alias NVARCHAR(MAX),
            their_public_did NVARCHAR(255),
            connection_protocol NVARCHAR(255),
            rfc23_state NVARCHAR(255),
            CONSTRAINT fk_item_id FOREIGN KEY (item_id)
            REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        """
        CREATE NONCLUSTERED INDEX idx_connection_item_id_v0_1
        ON connection_v0_1 (item_id);
        """,
        """
        CREATE NONCLUSTERED INDEX idx_connection_state_v0_1
        ON connection_v0_1 (state);
        """,
        """
        CREATE NONCLUSTERED INDEX idx_connection_created_at_v0_1
        ON connection_v0_1 (created_at);
        """,
        """
        CREATE TRIGGER trg_update_connection_timestamp_v0_1
        ON connection_v0_1
        AFTER UPDATE
        AS
        BEGIN
            UPDATE connection_v0_1
            SET updated_at = SYSDATETIME()
            FROM connection_v0_1
            INNER JOIN inserted ON connection_v0_1.id = inserted.id
            WHERE inserted.updated_at IS NULL;
        END;
        """,
    ],
}

DROP_SCHEMAS = {
    "sqlite": [
        "DROP TRIGGER IF EXISTS trg_update_connection_timestamp_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_created_at_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_state_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_item_id_v0_1;",
        "DROP TABLE IF EXISTS connection_v0_1;",
    ],
    "postgresql": [
        "DROP TRIGGER IF EXISTS trg_update_connection_timestamp_v0_1 ON connection_v0_1;",
        "DROP FUNCTION IF EXISTS update_connection_timestamp_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_connection_created_at_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_state_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_item_id_v0_1;",
        "DROP TABLE IF EXISTS connection_v0_1 CASCADE;",
    ],
    "mssql": [
        "DROP TRIGGER IF EXISTS trg_update_connection_timestamp_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_created_at_v0_1 ON connection_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_state_v0_1 ON connection_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_item_id_v0_1 ON connection_v0_1;",
        "DROP TABLE IF EXISTS connection_v0_1;",
    ],
}

COLUMNS = [
    "state",
    "created_at",
    "updated_at",
    "my_did",
    "their_did",
    "their_label",
    "their_role",
    "invitation_key",
    "invitation_msg_id",
    "request_id",
    "inbound_connection_id",
    "error_msg",
    "accept",
    "invitation_mode",
    "alias",
    "their_public_did",
    "connection_protocol",
    "rfc23_state",
]
