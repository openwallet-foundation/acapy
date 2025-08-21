"""Module docstring."""

CATEGORY = "connection_request"

SCHEMAS = {
    "sqlite": [
        """
        CREATE TABLE IF NOT EXISTS connection_request_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            connection_id TEXT NOT NULL,
            message_id TEXT,
            type TEXT,
            label TEXT,
            image_url TEXT,
            did TEXT,
            thread_pthid TEXT,
            did_doc TEXT,  -- JSON string of did_doc~attach
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_connection_request_item_id_v0_1
        ON connection_request_v0_1 (item_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_connection_request_message_id_v0_1
        ON connection_request_v0_1 (message_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_connection_request_did_v0_1
        ON connection_request_v0_1 (did);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_connection_request_thread_pthid_v0_1
        ON connection_request_v0_1 (thread_pthid);
        """,
        """
        CREATE TRIGGER IF NOT EXISTS trg_update_connection_request_timestamp_v0_1
        AFTER UPDATE ON connection_request_v0_1
        FOR EACH ROW
        BEGIN
            UPDATE connection_request_v0_1
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = OLD.id;
        END;
        """,
    ],
    "postgresql": [
        """
        CREATE TABLE IF NOT EXISTS connection_request_v0_1 (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            connection_id TEXT NOT NULL,
            message_id TEXT,
            type TEXT,
            label TEXT,
            image_url TEXT,
            did TEXT,
            thread_pthid TEXT,
            did_doc TEXT,  -- JSON string of did_doc~attach
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id)
            REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_connection_request_item_id_v0_1
        ON connection_request_v0_1 (item_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_connection_request_message_id_v0_1
        ON connection_request_v0_1 (message_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_connection_request_did_v0_1
        ON connection_request_v0_1 (did);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_connection_request_thread_pthid_v0_1
        ON connection_request_v0_1 (thread_pthid);
        """,
        """
        CREATE OR REPLACE FUNCTION update_connection_request_timestamp_v0_1()
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
        CREATE TRIGGER trg_update_connection_request_timestamp_v0_1
        BEFORE UPDATE ON connection_request_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION update_connection_request_timestamp_v0_1();
        """,
    ],
    "mssql": [
        """
        CREATE TABLE connection_request_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            item_id INT NOT NULL,
            item_name NVARCHAR(MAX) NOT NULL,
            connection_id NVARCHAR(255) NOT NULL,
            message_id NVARCHAR(255),
            type NVARCHAR(255),
            label NVARCHAR(MAX),
            image_url NVARCHAR(MAX),
            did NVARCHAR(255),
            thread_pthid NVARCHAR(255),
            did_doc NVARCHAR(MAX),  -- JSON string of did_doc~attach
            created_at DATETIME2 DEFAULT SYSDATETIME(),
            updated_at DATETIME2 DEFAULT SYSDATETIME(),
            CONSTRAINT fk_item_id FOREIGN KEY (item_id)
            REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        """
        CREATE NONCLUSTERED INDEX idx_connection_request_item_id_v0_1
        ON connection_request_v0_1 (item_id);
        """,
        """
        CREATE NONCLUSTERED INDEX idx_connection_request_message_id_v0_1
        ON connection_request_v0_1 (message_id);
        """,
        """
        CREATE NONCLUSTERED INDEX idx_connection_request_did_v0_1
        ON connection_request_v0_1 (did);
        """,
        """
        CREATE NONCLUSTERED INDEX idx_connection_request_thread_pthid_v0_1
        ON connection_request_v0_1 (thread_pthid);
        """,
        """
        CREATE TRIGGER trg_update_connection_request_timestamp_v0_1
        ON connection_request_v0_1
        AFTER UPDATE
        AS
        BEGIN
            UPDATE connection_request_v0_1
            SET updated_at = SYSDATETIME()
            FROM connection_request_v0_1
            INNER JOIN inserted ON connection_request_v0_1.id = inserted.id
            WHERE inserted.updated_at IS NULL;
        END;
        """,
    ],
}


DROP_SCHEMAS = {
    "sqlite": [
        "DROP TRIGGER IF EXISTS trg_update_connection_request_timestamp_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_request_thread_pthid_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_request_did_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_request_message_id_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_request_item_id_v0_1;",
        "DROP TABLE IF EXISTS connection_request_v0_1;",
    ],
    "postgresql": [
        """
        DROP TRIGGER IF EXISTS trg_update_connection_request_timestamp_v0_1
        ON connection_request_v0_1;
        """,
        "DROP FUNCTION IF EXISTS update_connection_request_timestamp_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_connection_request_thread_pthid_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_request_did_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_request_message_id_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_request_item_id_v0_1;",
        "DROP TABLE IF EXISTS connection_request_v0_1 CASCADE;",
    ],
    "mssql": [
        "DROP TRIGGER IF EXISTS trg_update_connection_request_timestamp_v0_1;",
        """
        DROP INDEX IF EXISTS idx_connection_request_thread_pthid_v0_1
        ON connection_request_v0_1;
        """,
        """
        DROP INDEX IF EXISTS idx_connection_request_did_v0_1
        ON connection_request_v0_1;
        """,
        """
        DROP INDEX IF EXISTS idx_connection_request_message_id_v0_1
        ON connection_request_v0_1;
        """,
        """
        DROP INDEX IF EXISTS idx_connection_request_item_id_v0_1
        ON connection_request_v0_1;
        """
        "DROP TABLE IF EXISTS connection_request_v0_1;",
    ],
}


COLUMNS = [
    "message_id",
    "connection_id",
    "type",
    "label",
    "image_url",
    "did",
    "thread_pthid",
    "did_doc",
]


# Sample data structure:
# {
#     "@type": "https://didcomm.org/didexchange/1.1/request",
#     "@id": "b7958c6e-b5fd-46cb-9214-bb2490e97c9e",
#     "~thread": {"pthid": "c314ba37-b375-4022-a2d2-3e44eee7eb75"},
#     "label": "My Wallet - 0655",
#     "did": "did:peer:1zQmdGpc4Tc6gvYvEy1HtDzaXaRGetXTvMki6jm6DLSsK62L",
#     "did_doc~attach": {
#         "@id": "6864e554-658f-4b79-a6d4-9e27477d53cc",
#         "mime-type": "application/json",
#         "data": {
#             "base64": "eyJAY29udGV4dCI6WyJodHRwczovL3czaWQub3JnL2RpZC92...",
#             "jws": {
#                 "header": {"kid": "did:key:z6MkwAuKddLDirF9BCpZDKeTZXVVnpg..."},
#                 "protected": "eyJhbGciOiJFZERTQSIsImp3ayI6eyJrdHk...",
#                 "signature": "R1Cu4JlCvkJg_ToJrd3aRBfOjPFaJ9ue5Oit37hBR0c..."
#             }
#         }
#     }
# }}
