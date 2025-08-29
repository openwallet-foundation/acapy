"""Module docstring."""

CATEGORY = "transaction"

SCHEMAS = {
    "sqlite": [
        """
        CREATE TABLE IF NOT EXISTS transaction_record_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            state TEXT CHECK (state IN (
                'init', 'transaction_created', 'request_sent', 'request_received',
                'transaction_endorsed', 'transaction_refused', 'transaction_resent',
                'transaction_resent_received', 'transaction_cancelled', 
                'transaction_acked',
                NULL
            )),
            connection_id TEXT,
            thread_id TEXT,
            comment TEXT,
            signature_request TEXT,
            signature_response TEXT,
            timing TEXT,
            formats TEXT,
            messages_attach TEXT,
            endorser_write_txn INTEGER,
            meta_data TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT transaction_record_v0_1_unique_item_name UNIQUE (item_name)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_transaction_item_id_v0_1 "
        "ON transaction_record_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_transaction_item_name_v0_1 "
        "ON transaction_record_v0_1 (item_name);",
        "CREATE INDEX IF NOT EXISTS idx_transaction_connection_id_v0_1 "
        "ON transaction_record_v0_1 (connection_id);",
        "CREATE INDEX IF NOT EXISTS idx_transaction_thread_id_v0_1 "
        "ON transaction_record_v0_1 (thread_id);",
        "CREATE INDEX IF NOT EXISTS idx_transaction_state_v0_1 "
        "ON transaction_record_v0_1 (state);",
        "CREATE INDEX IF NOT EXISTS idx_transaction_created_at_v0_1 "
        "ON transaction_record_v0_1 (created_at);",
        """
        CREATE TABLE IF NOT EXISTS transaction_formats_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            attach_id TEXT NOT NULL,
            format_type TEXT NOT NULL,
            FOREIGN KEY (transaction_id) 
                REFERENCES transaction_record_v0_1(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_transaction_formats_attach_id_v0_1 "
        "ON transaction_formats_v0_1 (attach_id);",
        """
        CREATE TRIGGER IF NOT EXISTS trg_insert_transaction_formats_v0_1
        AFTER INSERT ON transaction_record_v0_1
        FOR EACH ROW
        WHEN NEW.formats IS NOT NULL AND json_valid(NEW.formats) 
             AND json_type(NEW.formats) = 'array'
        BEGIN
            INSERT INTO transaction_formats_v0_1 (
                transaction_id, attach_id, format_type
            )
            SELECT
                NEW.id,
                json_extract(f.value, '$.attach_id'),
                json_extract(f.value, '$.format')
            FROM json_each(NEW.formats) f
            WHERE
                json_extract(f.value, '$.attach_id') IS NOT NULL
                AND json_extract(f.value, '$.format') IS NOT NULL;
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS trg_update_transaction_formats_v0_1
        AFTER UPDATE ON transaction_record_v0_1
        FOR EACH ROW
        WHEN NEW.formats IS NOT NULL AND json_valid(NEW.formats) 
             AND json_type(NEW.formats) = 'array' AND NEW.formats != OLD.formats
        BEGIN
            DELETE FROM transaction_formats_v0_1 WHERE transaction_id = OLD.id;
            INSERT INTO transaction_formats_v0_1 (
                transaction_id, attach_id, format_type
            )
            SELECT
                NEW.id,
                json_extract(f.value, '$.attach_id'),
                json_extract(f.value, '$.format')
            FROM json_each(NEW.formats) f
            WHERE
                json_extract(f.value, '$.attach_id') IS NOT NULL
                AND json_extract(f.value, '$.format') IS NOT NULL;
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS trg_update_transaction_timestamp_v0_1
        AFTER UPDATE ON transaction_record_v0_1
        FOR EACH ROW
        BEGIN
            UPDATE transaction_record_v0_1
            SET updated_at = strftime('%Y-%m-%dT%H:%M:%S.%fZ', 'now')
            WHERE id = OLD.id;
        END;
        """,
    ],
    "postgresql": [
        """
        CREATE TABLE IF NOT EXISTS transaction_record_v0_1 (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            state TEXT CHECK (state IN (
                'init', 'transaction_created', 'request_sent', 'request_received',
                'transaction_endorsed', 'transaction_refused', 'transaction_resent',
                'transaction_resent_received', 'transaction_cancelled', 
                'transaction_acked',
                NULL
            )),
            connection_id TEXT,
            thread_id TEXT,
            comment TEXT,
            signature_request TEXT,
            signature_response TEXT,
            timing TEXT,
            formats TEXT,
            messages_attach TEXT,
            endorser_write_txn BOOLEAN,
            meta_data TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT transaction_record_v0_1_unique_item_name UNIQUE (item_name)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_transaction_item_id_v0_1 "
        "ON transaction_record_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_transaction_item_name_v0_1 "
        "ON transaction_record_v0_1 (item_name);",
        "CREATE INDEX IF NOT EXISTS idx_transaction_connection_id_v0_1 "
        "ON transaction_record_v0_1 (connection_id);",
        "CREATE INDEX IF NOT EXISTS idx_transaction_thread_id_v0_1 "
        "ON transaction_record_v0_1 (thread_id);",
        "CREATE INDEX IF NOT EXISTS idx_transaction_state_v0_1 "
        "ON transaction_record_v0_1 (state);",
        "CREATE INDEX IF NOT EXISTS idx_transaction_created_at_v0_1 "
        "ON transaction_record_v0_1 (created_at);",
        """
        CREATE TABLE IF NOT EXISTS transaction_formats_v0_1 (
            id SERIAL PRIMARY KEY,
            transaction_id INTEGER NOT NULL,
            attach_id TEXT NOT NULL,
            format_type TEXT NOT NULL,
            CONSTRAINT fk_transaction_id FOREIGN KEY (transaction_id) 
                REFERENCES transaction_record_v0_1(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_transaction_formats_attach_id_v0_1 "
        "ON transaction_formats_v0_1 (attach_id);",
        """
        CREATE OR REPLACE FUNCTION insert_transaction_formats_v0_1()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.formats IS NOT NULL AND NEW.formats::jsonb IS NOT NULL 
               AND jsonb_typeof(NEW.formats::jsonb) = 'array' THEN
                INSERT INTO transaction_formats_v0_1 (
                transaction_id, attach_id, format_type
            )
                SELECT
                    NEW.id,
                    jsonb_extract_path_text(f.value, 'attach_id'),
                    jsonb_extract_path_text(f.value, 'format')
                FROM jsonb_array_elements(NEW.formats::jsonb) f
                WHERE
                    jsonb_extract_path_text(f.value, 'attach_id') IS NOT NULL
                    AND jsonb_extract_path_text(f.value, 'format') IS NOT NULL;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        CREATE TRIGGER trg_insert_transaction_formats_v0_1
        AFTER INSERT ON transaction_record_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION insert_transaction_formats_v0_1();
        """,
        """
        CREATE OR REPLACE FUNCTION update_transaction_formats_v0_1()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.formats IS NOT NULL AND NEW.formats::jsonb IS NOT NULL 
               AND jsonb_typeof(NEW.formats::jsonb) = 'array' 
               AND NEW.formats != OLD.formats THEN
                DELETE FROM transaction_formats_v0_1 WHERE transaction_id = OLD.id;
                INSERT INTO transaction_formats_v0_1 (
                transaction_id, attach_id, format_type
            )
                SELECT
                    NEW.id,
                    jsonb_extract_path_text(f.value, 'attach_id'),
                    jsonb_extract_path_text(f.value, 'format')
                FROM jsonb_array_elements(NEW.formats::jsonb) f
                WHERE
                    jsonb_extract_path_text(f.value, 'attach_id') IS NOT NULL
                    AND jsonb_extract_path_text(f.value, 'format') IS NOT NULL;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        CREATE TRIGGER trg_update_transaction_formats_v0_1
        AFTER UPDATE ON transaction_record_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION update_transaction_formats_v0_1();
        """,
        """
        CREATE OR REPLACE FUNCTION update_transaction_timestamp_v0_1()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.updated_at IS NULL THEN
                NEW.updated_at = TO_CHAR(NOW() AT TIME ZONE 'UTC', 
                                  'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"');
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        CREATE TRIGGER trg_update_transaction_timestamp_v0_1
        BEFORE UPDATE ON transaction_record_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION update_transaction_timestamp_v0_1();
        """,
    ],
    "mssql": [
        """
        CREATE TABLE transaction_record_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            item_id INT NOT NULL,
            item_name NVARCHAR(MAX) NOT NULL,
            state NVARCHAR(50) CHECK (state IN (
                'init', 'transaction_created', 'request_sent', 'request_received',
                'transaction_endorsed', 'transaction_refused', 'transaction_resent',
                'transaction_resent_received', 'transaction_cancelled', 
                'transaction_acked',
                NULL
            )),
            connection_id NVARCHAR(255),
            thread_id NVARCHAR(255),
            comment NVARCHAR(MAX),
            signature_request NVARCHAR(MAX),
            signature_response NVARCHAR(MAX),
            timing NVARCHAR(MAX),
            formats NVARCHAR(MAX),
            messages_attach NVARCHAR(MAX),
            endorser_write_txn BIT,
            meta_data NVARCHAR(MAX),
            created_at NVARCHAR(50) NOT NULL,
            updated_at NVARCHAR(50),
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT transaction_record_v0_1_unique_item_name UNIQUE (item_name)
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_transaction_item_id_v0_1 "
        "ON transaction_record_v0_1 (item_id);",
        "CREATE NONCLUSTERED INDEX idx_transaction_item_name_v0_1 "
        "ON transaction_record_v0_1 (item_name);",
        "CREATE NONCLUSTERED INDEX idx_transaction_connection_id_v0_1 "
        "ON transaction_record_v0_1 (connection_id);",
        "CREATE NONCLUSTERED INDEX idx_transaction_thread_id_v0_1 "
        "ON transaction_record_v0_1 (thread_id);",
        "CREATE NONCLUSTERED INDEX idx_transaction_state_v0_1 "
        "ON transaction_record_v0_1 (state);",
        "CREATE NONCLUSTERED INDEX idx_transaction_created_at_v0_1 "
        "ON transaction_record_v0_1 (created_at);"
        """
        CREATE TABLE transaction_formats_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            transaction_id INT NOT NULL,
            attach_id NVARCHAR(255) NOT NULL,
            format_type NVARCHAR(255) NOT NULL,
            CONSTRAINT fk_transaction_id FOREIGN KEY (transaction_id) 
                REFERENCES transaction_record_v0_1(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_transaction_formats_attach_id_v0_1 "
        "ON transaction_formats_v0_1 (attach_id);",
        """
        CREATE TRIGGER trg_insert_transaction_formats_v0_1
        ON transaction_record_v0_1
        AFTER INSERT
        AS
        BEGIN
            INSERT INTO transaction_formats_v0_1 (
                transaction_id, attach_id, format_type
            )
            SELECT
                i.id,
                JSON_VALUE(f.value, '$.attach_id'),
                JSON_VALUE(f.value, '$.format')
            FROM inserted i
            CROSS APPLY OPENJSON(i.formats) f
            WHERE i.formats IS NOT NULL
              AND ISJSON(i.formats) = 1
              AND JSON_VALUE(f.value, '$.attach_id') IS NOT NULL
              AND JSON_VALUE(f.value, '$.format') IS NOT NULL;
        END;
        """,
        """
        CREATE TRIGGER trg_update_transaction_formats_v0_1
        ON transaction_record_v0_1
        AFTER UPDATE
        AS
        BEGIN
            DELETE FROM transaction_formats_v0_1
            WHERE transaction_id IN (
                SELECT i.id
                FROM inserted i
                INNER JOIN deleted d ON i.id = d.id
                WHERE i.formats IS NOT NULL
                  AND ISJSON(i.formats) = 1
                  AND i.formats != d.formats
            );

            INSERT INTO transaction_formats_v0_1 (
                transaction_id, attach_id, format_type
            )
            SELECT
                i.id,
                JSON_VALUE(f.value, '$.attach_id'),
                JSON_VALUE(f.value, '$.format')
            FROM inserted i
            CROSS APPLY OPENJSON(i.formats) f
            WHERE i.formats IS NOT NULL
              AND ISJSON(i.formats) = 1
              AND JSON_VALUE(f.value, '$.attach_id') IS NOT NULL
              AND JSON_VALUE(f.value, '$.format') IS NOT NULL
              AND i.formats != (SELECT d.formats FROM deleted d WHERE d.id = i.id);
        END;
        """,
        """
        CREATE TRIGGER trg_update_transaction_timestamp_v0_1
        ON transaction_record_v0_1
        AFTER UPDATE
        AS
        BEGIN
            UPDATE transaction_record_v0_1
            SET updated_at = FORMAT(SYSDATETIME(), 
                             'yyyy-MM-dd''T''HH:mm:ss.fff''Z''')
            FROM transaction_record_v0_1
            INNER JOIN inserted ON transaction_record_v0_1.id = inserted.id
            WHERE inserted.updated_at IS NULL;
        END;
        """,
    ],
}

DROP_SCHEMAS = {
    "sqlite": [
        "DROP TRIGGER IF EXISTS trg_update_transaction_timestamp_v0_1;",
        "DROP TRIGGER IF EXISTS trg_update_transaction_formats_v0_1;",
        "DROP TRIGGER IF EXISTS trg_insert_transaction_formats_v0_1;",
        "DROP INDEX IF EXISTS idx_transaction_formats_attach_id_v0_1;",
        "DROP TABLE IF EXISTS transaction_formats_v0_1;",
        "DROP INDEX IF EXISTS idx_transaction_created_at_v0_1;",
        "DROP INDEX IF EXISTS idx_transaction_state_v0_1;",
        "DROP INDEX IF EXISTS idx_transaction_thread_id_v0_1;",
        "DROP INDEX IF EXISTS idx_transaction_connection_id_v0_1;",
        "DROP INDEX IF EXISTS idx_transaction_item_name_v0_1;",
        "DROP INDEX IF EXISTS idx_transaction_item_id_v0_1;",
        "DROP TABLE IF EXISTS transaction_record_v0_1;",
    ],
    "postgresql": [
        "DROP TRIGGER IF EXISTS trg_update_transaction_timestamp_v0_1 "
        "ON transaction_record_v0_1;",
        "DROP FUNCTION IF EXISTS update_transaction_timestamp_v0_1 CASCADE;",
        "DROP TRIGGER IF EXISTS trg_update_transaction_formats_v0_1 "
        "ON transaction_record_v0_1;",
        "DROP FUNCTION IF EXISTS update_transaction_formats_v0_1 CASCADE;",
        "DROP TRIGGER IF EXISTS trg_insert_transaction_formats_v0_1 ON "
        "transaction_record_v0_1;",
        "DROP FUNCTION IF EXISTS insert_transaction_formats_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_transaction_formats_attach_id_v0_1;",
        "DROP TABLE IF EXISTS transaction_formats_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_transaction_created_at_v0_1;",
        "DROP INDEX IF EXISTS idx_transaction_state_v0_1;",
        "DROP INDEX IF EXISTS idx_transaction_thread_id_v0_1;",
        "DROP INDEX IF EXISTS idx_transaction_connection_id_v0_1;",
        "DROP INDEX IF EXISTS idx_transaction_item_name_v0_1;",
        "DROP INDEX IF EXISTS idx_transaction_item_id_v0_1;",
        "DROP TABLE IF EXISTS transaction_record_v0_1 CASCADE;",
    ],
    "mssql": [
        "DROP TRIGGER IF EXISTS trg_update_transaction_timestamp_v0_1;",
        "DROP TRIGGER IF EXISTS trg_update_transaction_formats_v0_1;",
        "DROP TRIGGER IF EXISTS trg_insert_transaction_formats_v0_1;",
        "DROP INDEX IF EXISTS idx_transaction_formats_attach_id_v0_1 "
        "ON transaction_formats_v0_1;",
        "DROP TABLE IF EXISTS transaction_formats_v0_1;",
        "DROP INDEX IF EXISTS idx_transaction_created_at_v0_1 "
        "ON transaction_record_v0_1;",
        "DROP INDEX IF EXISTS idx_transaction_state_v0_1 ON transaction_record_v0_1;",
        "DROP INDEX IF EXISTS idx_transaction_thread_id_v0_1 ON transaction_record_v0_1;",
        "DROP INDEX IF EXISTS idx_transaction_connection_id_v0_1 "
        "ON transaction_record_v0_1;",
        "DROP INDEX IF EXISTS idx_transaction_item_name_v0_1 ON transaction_record_v0_1;",
        "DROP INDEX IF EXISTS idx_transaction_item_id_v0_1 "
        "ON transaction_record_v0_1;"
        "DROP TABLE IF EXISTS transaction_record_v0_1;",
    ],
}


COLUMNS = [
    "state",
    "connection_id",
    "thread_id",
    "comment",
    "signature_request",
    "signature_response",
    "timing",
    "formats",
    "messages_attach",
    "endorser_write_txn",
    "meta_data",
    "created_at",
    "updated_at",
]

# sample
# category=transaction, name=096f34af-8f2e-42a2-ac61-e6b8f9666dba,
# Sample transaction record (formatted for readability):
# value={
#   "connection_id": "ab69960c-4e4c-4144-adeb-96048728f3cc",
#   "state": "transaction_created",
#   "created_at": "2025-06-19T02:31:08.636777Z",
#   "updated_at": "2025-06-19T02:31:08.636777Z",
#   "comment": null,
#   "signature_request": [],
#   "signature_response": [],
#   "timing": {},
#   "formats": [{
#     "attach_id": "119a2bfa-f03b-4ee7-bc16-4135425d24fd",
#     "format": "dif/endorse-transaction/request@v1.0"
#   }],
#   "messages_attach": [{
#     "@id": "119a2bfa-f03b-4ee7-bc16-4135425d24fd",
#     "mime-type": "application/json",
#     "data": { ... }
#   }],
#   "thread_id": null,
#   "endorser_write_txn": null,
#   "meta_data": {
#     "context": {
#       "job_id": "c82cf7a98fdd43a0af2daba56f6ebdd0",
#       "schema_id": "BacujJ3zNmAR9afs9hPryb:2:person-demo-schema-1:0.001"
#     }
#   }
# },
# tags={
#   'connection_id': 'ab69960c-4e4c-4144-adeb-96048728f3cc',
#   'state': 'transaction_created'
# }
