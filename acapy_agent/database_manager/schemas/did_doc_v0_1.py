"""Module docstring."""

CATEGORY = "did_doc"

SCHEMAS = {
    "sqlite": [
        """
        CREATE TABLE IF NOT EXISTS did_doc_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            did TEXT,
            context TEXT,
            publickey TEXT,
            authentication TEXT,
            service TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_did_doc_item_id_v0_1 ON did_doc_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_did_doc_did_v0_1 ON did_doc_v0_1 (did);",
        """
        CREATE TABLE IF NOT EXISTS did_doc_keys_services_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            did_doc_id INTEGER NOT NULL,
            key_value TEXT,
            key_type TEXT CHECK (key_type IN 
                ('public_key', 'recipient_key', 'service_endpoint')),
            service_id TEXT,
            FOREIGN KEY (did_doc_id) REFERENCES did_doc_v0_1(id) 
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_did_doc_keys_services_key_value_v0_1 "
        "ON did_doc_keys_services_v0_1 (key_value);",
        "CREATE INDEX IF NOT EXISTS idx_did_doc_keys_services_service_id_v0_1 "
        "ON did_doc_keys_services_v0_1 (service_id);",
        """
        CREATE TRIGGER IF NOT EXISTS trg_insert_did_doc_keys_services_v0_1
        AFTER INSERT ON did_doc_v0_1
        FOR EACH ROW
        WHEN NEW.publickey IS NOT NULL OR NEW.service IS NOT NULL
        BEGIN
            INSERT INTO did_doc_keys_services_v0_1 
                (did_doc_id, key_value, key_type, service_id)
            SELECT NEW.id, json_extract(p.value, '$.publicKeyBase58'), 'public_key', NULL
            FROM json_each(NEW.publickey) p
            WHERE NEW.publickey IS NOT NULL AND json_valid(NEW.publickey)
              AND json_extract(p.value, '$.publicKeyBase58') IS NOT NULL;

            INSERT INTO did_doc_keys_services_v0_1 
                (did_doc_id, key_value, key_type, service_id)
            SELECT NEW.id, json_extract(s.value, '$.serviceEndpoint'), 
                'service_endpoint', json_extract(s.value, '$.id')
            FROM json_each(NEW.service) s
            WHERE NEW.service IS NOT NULL AND json_valid(NEW.service)
              AND json_extract(s.value, '$.serviceEndpoint') IS NOT NULL;

            INSERT INTO did_doc_keys_services_v0_1 
                (did_doc_id, key_value, key_type, service_id)
            SELECT NEW.id, r.value, 'recipient_key', json_extract(s.value, '$.id')
            FROM json_each(NEW.service) s
            CROSS JOIN json_each(json_extract(s.value, '$.recipientKeys')) r
            WHERE NEW.service IS NOT NULL AND json_valid(NEW.service)
              AND json_extract(s.value, '$.recipientKeys') IS NOT NULL
              AND r.value IS NOT NULL;
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS trg_update_did_doc_timestamp_v0_1
        AFTER UPDATE ON did_doc_v0_1
        FOR EACH ROW
        BEGIN
            UPDATE did_doc_v0_1
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = OLD.id;
        END;
        """,
    ],
    "postgresql": [
        """
        CREATE TABLE IF NOT EXISTS did_doc_v0_1 (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            did TEXT,
            context TEXT,
            publickey TEXT,
            authentication TEXT,
            service TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) 
                REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_did_doc_item_id_v0_1 ON did_doc_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_did_doc_did_v0_1 ON did_doc_v0_1 (did);",
        """
        CREATE TABLE IF NOT EXISTS did_doc_keys_services_v0_1 (
            id SERIAL PRIMARY KEY,
            did_doc_id INTEGER NOT NULL,
            key_value TEXT,
            key_type TEXT CHECK (key_type IN 
                ('public_key', 'recipient_key', 'service_endpoint')),
            service_id TEXT,
            CONSTRAINT fk_did_doc_id FOREIGN KEY (did_doc_id) 
                REFERENCES did_doc_v0_1(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_did_doc_keys_services_key_value_v0_1 "
        "ON did_doc_keys_services_v0_1 (key_value);",
        "CREATE INDEX IF NOT EXISTS idx_did_doc_keys_services_service_id_v0_1 "
        "ON did_doc_keys_services_v0_1 (service_id);",
        """
        CREATE OR REPLACE FUNCTION insert_did_doc_keys_services_v0_1()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.publickey IS NOT NULL AND NEW.publickey::jsonb IS NOT NULL THEN
                INSERT INTO did_doc_keys_services_v0_1 
                (did_doc_id, key_value, key_type, service_id)
                SELECT
                    NEW.id,
                    jsonb_extract_path_text(p.value, 'publicKeyBase58'),
                    'public_key',
                    NULL
                FROM jsonb_array_elements(NEW.publickey::jsonb) p
                WHERE jsonb_extract_path_text(p.value, 'publicKeyBase58') IS NOT NULL;
            END IF;

            IF NEW.service IS NOT NULL AND NEW.service::jsonb IS NOT NULL THEN
                INSERT INTO did_doc_keys_services_v0_1 
                (did_doc_id, key_value, key_type, service_id)
                SELECT
                    NEW.id,
                    jsonb_extract_path_text(s.value, 'serviceEndpoint'),
                    'service_endpoint',
                    jsonb_extract_path_text(s.value, 'id')
                FROM jsonb_array_elements(NEW.service::jsonb) s
                WHERE jsonb_extract_path_text(s.value, 'serviceEndpoint') IS NOT NULL;

                INSERT INTO did_doc_keys_services_v0_1 
                (did_doc_id, key_value, key_type, service_id)
                SELECT
                    NEW.id,
                    r.value,
                    'recipient_key',
                    jsonb_extract_path_text(s.value, 'id')
                FROM jsonb_array_elements(NEW.service::jsonb) s
                CROSS JOIN jsonb_array_elements(
                    jsonb_extract_path(s.value, 'recipientKeys')) r
                WHERE jsonb_extract_path(s.value, 'recipientKeys') IS NOT NULL
                  AND r.value IS NOT NULL;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        CREATE TRIGGER trg_insert_did_doc_keys_services_v0_1
        AFTER INSERT ON did_doc_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION insert_did_doc_keys_services_v0_1();
        """,
        """
        CREATE OR REPLACE FUNCTION update_did_doc_timestamp_v0_1()
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
        CREATE TRIGGER trg_update_did_doc_timestamp_v0_1
        BEFORE UPDATE ON did_doc_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION update_did_doc_timestamp_v0_1();
        """,
    ],
    "mssql": [
        """
        CREATE TABLE did_doc_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            item_id INT NOT NULL,
            item_name NVARCHAR(MAX) NOT NULL,
            did NVARCHAR(255),
            context NVARCHAR(MAX),
            publickey NVARCHAR(MAX),
            authentication NVARCHAR(MAX),
            service NVARCHAR(MAX),
            created_at DATETIME2 DEFAULT SYSDATETIME(),
            updated_at DATETIME2 DEFAULT SYSDATETIME(),
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) 
                REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_did_doc_item_id_v0_1 ON did_doc_v0_1 (item_id);",
        "CREATE NONCLUSTERED INDEX idx_did_doc_did_v0_1 ON did_doc_v0_1 (did);",
        """
        CREATE TABLE did_doc_keys_services_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            did_doc_id INT NOT NULL,
            key_value NVARCHAR(MAX),
            key_type NVARCHAR(50) CHECK (key_type IN 
                ('public_key', 'recipient_key', 'service_endpoint')),
            service_id NVARCHAR(255),
            CONSTRAINT fk_did_doc_id FOREIGN KEY (did_doc_id) 
                REFERENCES did_doc_v0_1(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_did_doc_keys_services_key_value_v0_1 "
        "ON did_doc_keys_services_v0_1 (key_value);",
        "CREATE NONCLUSTERED INDEX idx_did_doc_keys_services_service_id_v0_1 "
        "ON did_doc_keys_services_v0_1 (service_id);",
        """
        CREATE TRIGGER trg_insert_did_doc_keys_services_v0_1
        ON did_doc_v0_1
        AFTER INSERT
        AS
        BEGIN
            INSERT INTO did_doc_keys_services_v0_1 
                (did_doc_id, key_value, key_type, service_id)
            SELECT
                i.id,
                JSON_VALUE(p.value, '$.publicKeyBase58'),
                'public_key',
                NULL
            FROM inserted i
            CROSS APPLY OPENJSON(i.publickey) p
            WHERE i.publickey IS NOT NULL AND ISJSON(i.publickey) = 1
              AND JSON_VALUE(p.value, '$.publicKeyBase58') IS NOT NULL;

            INSERT INTO did_doc_keys_services_v0_1 
                (did_doc_id, key_value, key_type, service_id)
            SELECT
                i.id,
                JSON_VALUE(s.value, '$.serviceEndpoint'),
                'service_endpoint',
                JSON_VALUE(s.value, '$.id')
            FROM inserted i
            CROSS APPLY OPENJSON(i.service) s
            WHERE i.service IS NOT NULL AND ISJSON(i.service) = 1
              AND JSON_VALUE(s.value, '$.serviceEndpoint') IS NOT NULL;

            INSERT INTO did_doc_keys_services_v0_1 
                (did_doc_id, key_value, key_type, service_id)
            SELECT
                i.id,
                r.value,
                'recipient_key',
                JSON_VALUE(s.value, '$.id')
            FROM inserted i
            CROSS APPLY OPENJSON(i.service) s
            CROSS APPLY OPENJSON(JSON_VALUE(s.value, '$.recipientKeys')) r
            WHERE i.service IS NOT NULL AND ISJSON(i.service) = 1
              AND JSON_VALUE(s.value, '$.recipientKeys') IS NOT NULL
              AND r.value IS NOT NULL;
        END;
        """,
        """
        CREATE TRIGGER trg_update_did_doc_timestamp_v0_1
        ON did_doc_v0_1
        AFTER UPDATE
        AS
        BEGIN
            UPDATE did_doc_v0_1
            SET updated_at = SYSDATETIME()
            FROM did_doc_v0_1
            INNER JOIN inserted ON did_doc_v0_1.id = inserted.id
            WHERE inserted.updated_at IS NULL;
        END;
        """,
    ],
}


DROP_SCHEMAS = {
    "sqlite": [
        "DROP TRIGGER IF EXISTS trg_update_did_doc_timestamp_v0_1;",
        "DROP TRIGGER IF EXISTS trg_insert_did_doc_keys_services_v0_1;",
        "DROP INDEX IF EXISTS idx_did_doc_keys_services_service_id_v0_1;",
        "DROP INDEX IF EXISTS idx_did_doc_keys_services_key_value_v0_1;",
        "DROP TABLE IF EXISTS did_doc_keys_services_v0_1;",
        "DROP INDEX IF EXISTS idx_did_doc_did_v0_1;",
        "DROP INDEX IF EXISTS idx_did_doc_item_id_v0_1;",
        "DROP TABLE IF EXISTS did_doc_v0_1;",
    ],
    "postgresql": [
        "DROP TRIGGER IF EXISTS trg_update_did_doc_timestamp_v0_1 ON did_doc_v0_1;",
        "DROP FUNCTION IF EXISTS update_did_doc_timestamp_v0_1 CASCADE;",
        "DROP TRIGGER IF EXISTS trg_insert_did_doc_keys_services_v0_1 ON did_doc_v0_1;",
        "DROP FUNCTION IF EXISTS insert_did_doc_keys_services_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_did_doc_keys_services_service_id_v0_1;",
        "DROP INDEX IF EXISTS idx_did_doc_keys_services_key_value_v0_1;",
        "DROP TABLE IF EXISTS did_doc_keys_services_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_did_doc_did_v0_1;",
        "DROP INDEX IF EXISTS idx_did_doc_item_id_v0_1;",
        "DROP TABLE IF EXISTS did_doc_v0_1 CASCADE;",
    ],
    "mssql": [
        "DROP TRIGGER IF EXISTS trg_update_did_doc_timestamp_v0_1;",
        "DROP TRIGGER IF EXISTS trg_insert_did_doc_keys_services_v0_1;",
        "DROP INDEX IF EXISTS idx_did_doc_keys_services_service_id_v0_1 "
        "ON did_doc_keys_services_v0_1;",
        "DROP INDEX IF EXISTS idx_did_doc_keys_services_key_value_v0_1 "
        "ON did_doc_keys_services_v0_1;",
        "DROP TABLE IF EXISTS did_doc_keys_services_v0_1;",
        "DROP INDEX IF EXISTS idx_did_doc_did_v0_1 ON did_doc_v0_1;",
        "DROP INDEX IF EXISTS idx_did_doc_item_id_v0_1 ON did_doc_v0_1;",
        "DROP TABLE IF EXISTS did_doc_v0_1;",
    ],
}

COLUMNS = [
    "did",
    "context",
    "publickey",
    "authentication",
    "service",
    "created_at",
    "updated_at",
]

# sample
# category=did_doc, name=32e953b1a11a468da3500e9b12655b5d
# json={"@context": "https://w3id.org/did/v1", "id": "did:sov:3hQMdP4sNb1iQKN1L1VqLe",
#  "publicKey": [{"id": "did:sov:3hQMdP4sNb1iQKN1L1VqLe#1", "type":
#  "Ed25519VerificationKey2018", "controller": "did:sov:3hQMdP4sNb1iQKN1L1VqLe",
#  "publicKeyBase58": "2UFCSELfEF7tsBLJU5uhnDAyhDxe1vgaWqJiyBDhXvAx"}],
#  "authentication": [{"type": "Ed25519SignatureAuthentication2018",
#  "publicKey": "did:sov:3hQMdP4sNb1iQKN1L1VqLe#1"}], "service":
#  [{"id": "did:sov:3hQMdP4sNb1iQKN1L1VqLe;indy", "type": "IndyAgent",
#  "priority": 0, "recipientKeys": ["2UFCSELfEF7tsBLJU5uhnDAyhDxe1vgaWqJiyBDhXvAx"],
#  "serviceEndpoint": "https://477e-70-49-2-61.ngrok-free.app"}]}
#  tags={'did': '3hQMdP4sNb1iQKN1L1VqLe'}
