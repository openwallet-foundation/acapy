"""Module docstring."""

CATEGORY = "oob_record"

IDX_OOB_ON_ITEM_ID = "ON oob_record_v0_1 (item_id);"
IDX_OOB_ON_ITEM_NAME = "ON oob_record_v0_1 (item_name);"
IDX_OOB_ON_INVI_MSG_ID = "ON oob_record_v0_1 (invi_msg_id);"
IDX_OOB_ON_CONNECTION_ID = "ON oob_record_v0_1 (connection_id);"
IDX_OOB_ON_STATE = "ON oob_record_v0_1 (state);"
IDX_OOB_ON_CREATED_AT = "ON oob_record_v0_1 (created_at);"

SCHEMAS = {
    "sqlite": [
        """
        CREATE TABLE IF NOT EXISTS oob_record_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            state TEXT CHECK 
                (state IN ('await-response', 'done', 'failed', 'sent', NULL)),
            created_at TEXT NOT NULL,
            updated_at TEXT,
            trace INTEGER,
            invi_msg_id TEXT NOT NULL,
            role TEXT NOT NULL,
            invitation TEXT NOT NULL,
            their_service TEXT,
            connection_id TEXT,
            reuse_msg_id TEXT,
            attach_thread_id TEXT,
            our_recipient_key TEXT,
            our_service TEXT,
            multi_use INTEGER DEFAULT 0,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_oob_record_item_id_v0_1 " + IDX_OOB_ON_ITEM_ID,
        "CREATE INDEX IF NOT EXISTS idx_oob_record_item_name_v0_1 "
        + IDX_OOB_ON_ITEM_NAME,
        "CREATE INDEX IF NOT EXISTS idx_oob_record_invi_msg_id_v0_1 "
        + IDX_OOB_ON_INVI_MSG_ID,
        "CREATE INDEX IF NOT EXISTS idx_oob_record_connection_id_v0_1 "
        + IDX_OOB_ON_CONNECTION_ID,
        "CREATE INDEX IF NOT EXISTS idx_oob_record_state_v0_1 " + IDX_OOB_ON_STATE,
        "CREATE INDEX IF NOT EXISTS idx_oob_record_created_at_v0_1 "
        + IDX_OOB_ON_CREATED_AT,
        """
        CREATE TRIGGER IF NOT EXISTS trg_update_oob_record_timestamp_v0_1
        AFTER UPDATE ON oob_record_v0_1
        FOR EACH ROW
        BEGIN
            UPDATE oob_record_v0_1
            SET updated_at = strftime('%Y-%m-%dT%H:%M:%S.%fZ', 'now')
            WHERE id = OLD.id;
        END;
        """,
    ],
    "postgresql": [
        """
        CREATE TABLE IF NOT EXISTS oob_record_v0_1 (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            state TEXT CHECK 
                (state IN ('await-response', 'done', 'failed', 'sent', NULL)),
            created_at TEXT NOT NULL,
            updated_at TEXT,
            trace BOOLEAN,
            invi_msg_id TEXT NOT NULL,
            role TEXT NOT NULL,
            invitation TEXT NOT NULL,
            their_service TEXT,
            connection_id TEXT,
            reuse_msg_id TEXT,
            attach_thread_id TEXT,
            our_recipient_key TEXT,
            our_service TEXT,
            multi_use BOOLEAN DEFAULT FALSE,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id)
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_oob_record_item_id_v0_1 " + IDX_OOB_ON_ITEM_ID,
        "CREATE INDEX IF NOT EXISTS idx_oob_record_item_name_v0_1 "
        + IDX_OOB_ON_ITEM_NAME,
        "CREATE INDEX IF NOT EXISTS idx_oob_record_invi_msg_id_v0_1 "
        + IDX_OOB_ON_INVI_MSG_ID,
        "CREATE INDEX IF NOT EXISTS idx_oob_record_connection_id_v0_1 "
        + IDX_OOB_ON_CONNECTION_ID,
        "CREATE INDEX IF NOT EXISTS idx_oob_record_state_v0_1 " + IDX_OOB_ON_STATE,
        "CREATE INDEX IF NOT EXISTS idx_oob_record_created_at_v0_1 "
        + IDX_OOB_ON_CREATED_AT,
        """
        CREATE OR REPLACE FUNCTION update_oob_record_timestamp_v0_1()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.updated_at IS NULL THEN
                NEW.updated_at = TO_CHAR(
                    NOW() AT TIME ZONE 'UTC', 
                    'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'
                );
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        CREATE TRIGGER trg_update_oob_record_timestamp_v0_1
        BEFORE UPDATE ON oob_record_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION update_oob_record_timestamp_v0_1();
        """,
    ],
    "mssql": [
        """
        CREATE TABLE oob_record_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            item_id INT NOT NULL,
            item_name NVARCHAR(MAX) NOT NULL,
            state NVARCHAR(50) CHECK (
                state IN ('await-response', 'done', 'failed', 'sent', NULL)
            ),
            created_at NVARCHAR(50) NOT NULL,
            updated_at NVARCHAR(50),
            trace BIT,
            invi_msg_id NVARCHAR(255) NOT NULL,
            role NVARCHAR(255) NOT NULL,
            invitation NVARCHAR(MAX) NOT NULL,
            their_service NVARCHAR(MAX),
            connection_id NVARCHAR(255),
            reuse_msg_id NVARCHAR(255),
            attach_thread_id NVARCHAR(255),
            our_recipient_key NVARCHAR(255),
            our_service NVARCHAR(MAX),
            multi_use BIT DEFAULT 0,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id)
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_oob_record_item_id_v0_1 " + IDX_OOB_ON_ITEM_ID,
        "CREATE NONCLUSTERED INDEX idx_oob_record_item_name_v0_1 " + IDX_OOB_ON_ITEM_NAME,
        "CREATE NONCLUSTERED INDEX idx_oob_record_invi_msg_id_v0_1 "
        + IDX_OOB_ON_INVI_MSG_ID,
        "CREATE NONCLUSTERED INDEX idx_oob_record_connection_id_v0_1 "
        + IDX_OOB_ON_CONNECTION_ID,
        "CREATE NONCLUSTERED INDEX idx_oob_record_state_v0_1 " + IDX_OOB_ON_STATE,
        "CREATE NONCLUSTERED INDEX idx_oob_record_created_at_v0_1 "
        + IDX_OOB_ON_CREATED_AT,
        """
        CREATE TRIGGER trg_update_oob_record_timestamp_v0_1
        ON oob_record_v0_1
        AFTER UPDATE
        AS
        BEGIN
            UPDATE oob_record_v0_1
            SET updated_at = FORMAT(SYSDATETIME(), 'yyyy-MM-dd''T''HH:mm:ss.fff''Z''')
            FROM oob_record_v0_1
            INNER JOIN inserted ON oob_record_v0_1.id = inserted.id
            WHERE inserted.updated_at IS NULL;
        END;
        """,
    ],
}


DROP_SCHEMAS = {
    "sqlite": [
        "DROP TRIGGER IF EXISTS trg_update_oob_record_timestamp_v0_1;",
        "DROP INDEX IF EXISTS idx_oob_record_created_at_v0_1;",
        "DROP INDEX IF EXISTS idx_oob_record_state_v0_1;",
        "DROP INDEX IF EXISTS idx_oob_record_connection_id_v0_1;",
        "DROP INDEX IF EXISTS idx_oob_record_invi_msg_id_v0_1;",
        "DROP INDEX IF EXISTS idx_oob_record_item_name_v0_1;",
        "DROP INDEX IF EXISTS idx_oob_record_item_id_v0_1;",
        "DROP TABLE IF EXISTS oob_record_v0_1;",
    ],
    "postgresql": [
        "DROP TRIGGER IF EXISTS trg_update_oob_record_timestamp_v0_1 ON oob_record_v0_1;",
        "DROP FUNCTION IF EXISTS update_oob_record_timestamp_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_oob_record_created_at_v0_1;",
        "DROP INDEX IF EXISTS idx_oob_record_state_v0_1;",
        "DROP INDEX IF EXISTS idx_oob_record_connection_id_v0_1;",
        "DROP INDEX IF EXISTS idx_oob_record_invi_msg_id_v0_1;",
        "DROP INDEX IF EXISTS idx_oob_record_item_name_v0_1;",
        "DROP INDEX IF EXISTS idx_oob_record_item_id_v0_1;",
        "DROP TABLE IF EXISTS oob_record_v0_1 CASCADE;",
    ],
    "mssql": [
        "DROP TRIGGER IF EXISTS trg_update_oob_record_timestamp_v0_1;",
        "DROP INDEX IF EXISTS idx_oob_record_created_at_v0_1 ON oob_record_v0_1;",
        "DROP INDEX IF EXISTS idx_oob_record_state_v0_1 ON oob_record_v0_1;",
        "DROP INDEX IF EXISTS idx_oob_record_connection_id_v0_1 ON oob_record_v0_1;",
        "DROP INDEX IF EXISTS idx_oob_record_invi_msg_id_v0_1 ON oob_record_v0_1;",
        "DROP INDEX IF EXISTS idx_oob_record_item_name_v0_1 ON oob_record_v0_1;",
        "DROP INDEX IF EXISTS idx_oob_record_item_id_v0_1 ON oob_record_v0_1;",
        "DROP TABLE IF EXISTS oob_record_v0_1;",
    ],
}


COLUMNS = [
    "state",
    "created_at",
    "updated_at",
    "trace",
    "invi_msg_id",
    "role",
    "invitation",
    "their_service",
    "connection_id",
    "reuse_msg_id",
    "attach_thread_id",
    "our_recipient_key",
    "our_service",
    "multi_use",
]


# sample
# category=oob_record, name=c08c5e31-fcb1-484b-9c81-7020e878e0a9,
# json={"our_recipient_key": "8UgXwq4s7uXLg9f6ZxSexvyPPsMqMjxHnamtPdtUMPdo",
#       "invi_msg_id": "0ccaf2f7-771b-4ec0-a29f-2f7e71aecc94",
#       "connection_id": "110af30c-8711-42e0-baa3-b93f7918f72b",
#       "created_at": "2025-06-17T19:54:10.918294Z",
#       "updated_at": "2025-06-17T19:54:10.918294Z",
#       "state": "await-response", "their_service": null, "role": "sender",
#       "multi_use": false, "invitation": {"@type":
#       "https://didcomm.org/out-of-band/1.1/invitation",
#       "@id": "0ccaf2f7-771b-4ec0-a29f-2f7e71aecc94",
#       "label": "alice.agent",
#       "handshake_protocols": ["https://didcomm.org/didexchange/1.0"],
#       "services": [{"id": "#inline", "type": "did-communication",
#       "recipientKeys":
#       ["did:key:z6MkmvwaY5KJTT1oneVoFXQVp2XPDSdgmdCeUbgpDurVGcRB"
#        "#z6MkmvwaY5KJTT1oneVoFXQVp2XPDSdgmdCeUbgpDurVGcRB"],
#       "serviceEndpoint": "https://6fb8-70-49-2-61.ngrok-free.app"}],
#       "goal_code": "issue-vc",
#       "goal": "To issue a Faber College Graduate credential"}},
# tags={'our_recipient_key': '8UgXwq4s7uXLg9f6ZxSexvyPPsMqMjxHnamtPdtUMPdo',
#       'invi_msg_id': '0ccaf2f7-771b-4ec0-a29f-2f7e71aecc94',
#       'connection_id': '110af30c-8711-42e0-baa3-b93f7918f72b'}
