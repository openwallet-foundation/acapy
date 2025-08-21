"""Module docstring."""

CATEGORY = "connection_invitation"

SCHEMAS = {
    "sqlite": [
        """
        CREATE TABLE IF NOT EXISTS connection_invitation_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            label TEXT,
            did TEXT,
            recipient_keys TEXT DEFAULT '[]',  -- JSON array of recipient public keys
            endpoint TEXT,
            routing_keys TEXT DEFAULT '[]',  -- JSON array of routing public keys
            image_url TEXT,
            handshake_protocols TEXT,  -- JSON array of handshake protocols
            services TEXT,  -- JSON array of service objects
            goal_code TEXT,
            goal TEXT,
            connection_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_invitation_item_id_v0_1 "
        "ON connection_invitation_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_invitation_connection_id_v0_1 "
        "ON connection_invitation_v0_1 (connection_id);",
        """
        CREATE TABLE IF NOT EXISTS connection_invitation_keys_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invitation_id INTEGER NOT NULL,
            key_type TEXT NOT NULL CHECK(key_type IN ('recipient', 'routing')),
            public_key TEXT NOT NULL,
            FOREIGN KEY (invitation_id) REFERENCES connection_invitation_v0_1(id) 
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_connection_invitation_key_v0_1 "
        "ON connection_invitation_keys_v0_1 (public_key);",
        """
        CREATE TRIGGER IF NOT EXISTS trg_insert_connection_invitation_keys_v0_1
        AFTER INSERT ON connection_invitation_v0_1
        FOR EACH ROW
        BEGIN
            INSERT INTO connection_invitation_keys_v0_1 (
                invitation_id, key_type, public_key
            )
            SELECT NEW.id, 'recipient', value
            FROM json_each(NEW.recipient_keys)
            WHERE NEW.recipient_keys IS NOT NULL AND NEW.recipient_keys != '' 
                AND json_valid(NEW.recipient_keys);

            INSERT INTO connection_invitation_keys_v0_1 (
                invitation_id, key_type, public_key
            )
            SELECT NEW.id, 'routing', value
            FROM json_each(NEW.routing_keys)
            WHERE NEW.routing_keys IS NOT NULL AND NEW.routing_keys != '' 
                AND json_valid(NEW.routing_keys);

            INSERT INTO connection_invitation_keys_v0_1 (
                invitation_id, key_type, public_key
            )
            SELECT NEW.id, 'recipient', json_extract(s.value, '$.recipientKeys[0]')
            FROM json_each(NEW.services) s
            WHERE NEW.services IS NOT NULL AND NEW.services != '' 
                AND json_valid(NEW.services)
              AND json_extract(s.value, '$.recipientKeys[0]') IS NOT NULL;

            INSERT INTO connection_invitation_keys_v0_1 (
                invitation_id, key_type, public_key
            )
            SELECT NEW.id, 'routing', json_extract(s.value, '$.routingKeys[0]')
            FROM json_each(NEW.services) s
            WHERE NEW.services IS NOT NULL AND NEW.services != '' 
                AND json_valid(NEW.services)
              AND json_extract(s.value, '$.routingKeys[0]') IS NOT NULL;
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS trg_populate_from_services_v0_1
        BEFORE INSERT ON connection_invitation_v0_1
        FOR EACH ROW
        WHEN NEW.services IS NOT NULL AND NEW.services != '' 
             AND json_valid(NEW.services)
             AND (NEW.recipient_keys IS NULL OR NEW.recipient_keys = '' 
             OR NEW.endpoint IS NULL OR NEW.endpoint = '')
        BEGIN
            INSERT INTO connection_invitation_v0_1 (
                item_id, item_name, label, did, recipient_keys, endpoint,
                routing_keys, image_url, handshake_protocols, services, goal_code, goal,
                connection_id, created_at, updated_at
            )
            SELECT
                NEW.item_id,
                NEW.item_name,
                NEW.label,
                NEW.did,
                COALESCE(NEW.recipient_keys, 
                         json_extract(s.value, '$.recipientKeys'), '[]'),
                COALESCE(NEW.endpoint, 
                         json_extract(s.value, '$.serviceEndpoint')),
                COALESCE(NEW.routing_keys, '[]'),
                NEW.image_url,
                NEW.handshake_protocols,
                NEW.services,
                NEW.goal_code,
                NEW.goal,
                NEW.connection_id,
                NEW.created_at,
                NEW.updated_at
            FROM json_each(NEW.services) s
            LIMIT 1;
            SELECT RAISE(IGNORE);
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS trg_update_connection_invitation_timestamp_v0_1
        AFTER UPDATE ON connection_invitation_v0_1
        FOR EACH ROW
        BEGIN
            UPDATE connection_invitation_v0_1
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = OLD.id;
        END;
        """,
    ],
    "postgresql": [
        """
        CREATE TABLE IF NOT EXISTS connection_invitation_v0_1 (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            label TEXT,
            did TEXT,
            recipient_keys TEXT DEFAULT '[]',  -- JSON array of recipient public keys
            endpoint TEXT,
            routing_keys TEXT DEFAULT '[]',  -- JSON array of routing public keys
            image_url TEXT,
            handshake_protocols TEXT,  -- JSON array of handshake protocols
            services TEXT,  -- JSON array of service objects
            goal_code TEXT,
            goal TEXT,
            connection_id TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_invitation_item_id_v0_1 "
        "ON connection_invitation_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_invitation_connection_id_v0_1 "
        "ON connection_invitation_v0_1 (connection_id);",
        """
        CREATE TABLE IF NOT EXISTS connection_invitation_keys_v0_1 (
            id SERIAL PRIMARY KEY,
            invitation_id INTEGER NOT NULL,
            key_type TEXT NOT NULL CHECK(key_type IN ('recipient', 'routing')),
            public_key TEXT NOT NULL,
            CONSTRAINT fk_invitation_id FOREIGN KEY (invitation_id) 
                REFERENCES connection_invitation_v0_1(id) 
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_connection_invitation_key_v0_1 "
        "ON connection_invitation_keys_v0_1 (public_key);",
        """
        CREATE OR REPLACE FUNCTION insert_connection_invitation_keys_v0_1()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO connection_invitation_keys_v0_1 (
                invitation_id, key_type, public_key
            )
            SELECT NEW.id, 'recipient', value
            FROM jsonb_array_elements_text(NEW.recipient_keys::jsonb)
            WHERE NEW.recipient_keys IS NOT NULL AND NEW.recipient_keys != '' 
                AND NEW.recipient_keys::jsonb IS NOT NULL;

            INSERT INTO connection_invitation_keys_v0_1 (
                invitation_id, key_type, public_key
            )
            SELECT NEW.id, 'routing', value
            FROM jsonb_array_elements_text(NEW.routing_keys::jsonb)
            WHERE NEW.routing_keys IS NOT NULL AND NEW.routing_keys != '' 
                AND NEW.routing_keys::jsonb IS NOT NULL;

            INSERT INTO connection_invitation_keys_v0_1 (
                invitation_id, key_type, public_key
            )
            SELECT NEW.id, 'recipient', 
                   jsonb_extract_path_text(s, 'recipientKeys', '0')
            FROM jsonb_array_elements(NEW.services::jsonb) s
            WHERE NEW.services IS NOT NULL AND NEW.services != '' 
                AND NEW.services::jsonb IS NOT NULL
              AND jsonb_extract_path_text(s, 'recipientKeys', '0') IS NOT NULL;

            INSERT INTO connection_invitation_keys_v0_1 (
                invitation_id, key_type, public_key
            )
            SELECT NEW.id, 'routing', 
                   jsonb_extract_path_text(s, 'routingKeys', '0')
            FROM jsonb_array_elements(NEW.services::jsonb) s
            WHERE NEW.services IS NOT NULL AND NEW.services != '' 
                AND NEW.services::jsonb IS NOT NULL
              AND jsonb_extract_path_text(s, 'routingKeys', '0') IS NOT NULL;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        CREATE TRIGGER trg_insert_connection_invitation_keys_v0_1
        AFTER INSERT ON connection_invitation_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION insert_connection_invitation_keys_v0_1();
        """,
        """
        CREATE OR REPLACE FUNCTION populate_from_services_v0_1()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.services IS NOT NULL AND NEW.services != '' 
               AND NEW.services::jsonb IS NOT NULL
               AND (NEW.recipient_keys IS NULL OR NEW.recipient_keys = '' 
               OR NEW.endpoint IS NULL OR NEW.endpoint = '') THEN
                SELECT
                    COALESCE(NEW.recipient_keys, 
                             jsonb_extract_path_text(s, 'recipientKeys')::text, 
                             '[]') AS recipient_keys,
                    COALESCE(NEW.endpoint, 
                             jsonb_extract_path_text(s, 'serviceEndpoint')) AS endpoint
                INTO NEW.recipient_keys, NEW.endpoint
                FROM jsonb_array_elements(NEW.services::jsonb) s
                LIMIT 1;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        CREATE TRIGGER trg_populate_from_services_v0_1
        BEFORE INSERT ON connection_invitation_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION populate_from_services_v0_1();
        """,
        """
        CREATE OR REPLACE FUNCTION update_connection_invitation_timestamp_v0_1()
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
        CREATE TRIGGER trg_update_connection_invitation_timestamp_v0_1
        BEFORE UPDATE ON connection_invitation_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION update_connection_invitation_timestamp_v0_1();
        """,
    ],
    "mssql": [
        """
        CREATE TABLE connection_invitation_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            item_id INT NOT NULL,
            item_name NVARCHAR(MAX) NOT NULL,
            label NVARCHAR(MAX),
            did NVARCHAR(255),
            recipient_keys NVARCHAR(MAX) DEFAULT '[]',  
                -- JSON array of recipient public keys
            endpoint NVARCHAR(MAX),
            routing_keys NVARCHAR(MAX) DEFAULT '[]',  -- JSON array of routing public keys
            image_url NVARCHAR(MAX),
            handshake_protocols NVARCHAR(MAX),  -- JSON array of handshake protocols
            services NVARCHAR(MAX),  -- JSON array of service objects
            goal_code NVARCHAR(255),
            goal NVARCHAR(MAX),
            connection_id NVARCHAR(255),
            created_at DATETIME2 DEFAULT SYSDATETIME(),
            updated_at DATETIME2 DEFAULT SYSDATETIME(),
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id) 
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_invitation_item_id_v0_1 "
        "ON connection_invitation_v0_1 (item_id);",
        "CREATE NONCLUSTERED INDEX idx_invitation_connection_id_v0_1 "
        "ON connection_invitation_v0_1 (connection_id);",
        """
        CREATE TABLE connection_invitation_keys_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            invitation_id INT NOT NULL,
            key_type NVARCHAR(50) NOT NULL CHECK(key_type IN ('recipient', 'routing')),
            public_key NVARCHAR(MAX) NOT NULL,
            CONSTRAINT fk_invitation_id FOREIGN KEY (invitation_id) 
                REFERENCES connection_invitation_v0_1(id) 
                ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_connection_invitation_key_v0_1 "
        "ON connection_invitation_keys_v0_1 (public_key);",
        """
        CREATE TRIGGER trg_insert_connection_invitation_keys_v0_1
        ON connection_invitation_v0_1
        AFTER INSERT
        AS
        BEGIN
            INSERT INTO connection_invitation_keys_v0_1 (
                invitation_id, key_type, public_key
            )
            SELECT i.id, 'recipient', j.value
            FROM inserted i
            CROSS APPLY OPENJSON(i.recipient_keys) j
            WHERE i.recipient_keys IS NOT NULL AND i.recipient_keys != '' 
                AND ISJSON(i.recipient_keys) = 1;

            INSERT INTO connection_invitation_keys_v0_1 (
                invitation_id, key_type, public_key
            )
            SELECT i.id, 'routing', j.value
            FROM inserted i
            CROSS APPLY OPENJSON(i.routing_keys) j
            WHERE i.routing_keys IS NOT NULL AND i.routing_keys != '' 
                AND ISJSON(i.routing_keys) = 1;

            INSERT INTO connection_invitation_keys_v0_1 (
                invitation_id, key_type, public_key
            )
            SELECT i.id, 'recipient', JSON_VALUE(s.value, '$.recipientKeys[0]')
            FROM inserted i
            CROSS APPLY OPENJSON(i.services) s
            WHERE i.services IS NOT NULL AND i.services != '' 
                AND ISJSON(i.services) = 1
              AND JSON_VALUE(s.value, '$.recipientKeys[0]') IS NOT NULL;

            INSERT INTO connection_invitation_keys_v0_1 (
                invitation_id, key_type, public_key
            )
            SELECT i.id, 'routing', JSON_VALUE(s.value, '$.routingKeys[0]')
            FROM inserted i
            CROSS APPLY OPENJSON(i.services) s
            WHERE i.services IS NOT NULL AND i.services != '' 
                AND ISJSON(i.services) = 1
              AND JSON_VALUE(s.value, '$.routingKeys[0]') IS NOT NULL;
        END;
        """,
        """
        CREATE TRIGGER trg_populate_from_services_v0_1
        ON connection_invitation_v0_1
        INSTEAD OF INSERT
        AS
        BEGIN
            INSERT INTO connection_invitation_v0_1 (
                item_id, item_name, label, did, recipient_keys, endpoint,
                routing_keys, image_url, handshake_protocols, services, goal_code, goal,
                connection_id, created_at, updated_at
            )
            SELECT
                i.item_id,
                i.item_name,
                i.label,
                i.did,
                COALESCE(i.recipient_keys, 
                         JSON_VALUE(s.value, '$.recipientKeys'), '[]'),
                COALESCE(i.endpoint, 
                         JSON_VALUE(s.value, '$.serviceEndpoint')),
                COALESCE(i.routing_keys, '[]'),
                i.image_url,
                i.handshake_protocols,
                i.services,
                i.goal_code,
                i.goal,
                i.connection_id,
                i.created_at,
                i.updated_at
            FROM inserted i
            OUTER APPLY (
                SELECT TOP 1 value
                FROM OPENJSON(i.services)
                WHERE i.services IS NOT NULL AND i.services != '' 
                AND ISJSON(i.services) = 1
            ) s
            WHERE i.services IS NOT NULL AND i.services != '' 
                AND ISJSON(i.services) = 1
              AND (i.recipient_keys IS NULL OR i.recipient_keys = '' 
              OR i.endpoint IS NULL OR i.endpoint = '')

            UNION ALL

            SELECT
                item_id, item_name, label, did, recipient_keys, endpoint,
                routing_keys, image_url, handshake_protocols, services, goal_code, goal,
                connection_id, created_at, updated_at
            FROM inserted
            WHERE services IS NULL OR services = '' OR ISJSON(services) = 0
               OR (recipient_keys IS NOT NULL AND recipient_keys != '' 
               AND endpoint IS NOT NULL AND endpoint != '');
        END;
        """,
        """
        CREATE TRIGGER trg_update_connection_invitation_timestamp_v0_1
        ON connection_invitation_v0_1
        AFTER UPDATE
        AS
        BEGIN
            UPDATE connection_invitation_v0_1
            SET updated_at = SYSDATETIME()
            FROM connection_invitation_v0_1
            INNER JOIN inserted ON connection_invitation_v0_1.id = inserted.id
            WHERE inserted.updated_at IS NULL;
        END;
        """,
    ],
}

DROP_SCHEMAS = {
    "sqlite": [
        "DROP TRIGGER IF EXISTS trg_update_connection_invitation_timestamp_v0_1;",
        "DROP TRIGGER IF EXISTS trg_populate_from_services_v0_1;",
        "DROP TRIGGER IF EXISTS trg_insert_connection_invitation_keys_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_invitation_key_v0_1;",
        "DROP TABLE IF EXISTS connection_invitation_keys_v0_1;",
        "DROP INDEX IF EXISTS idx_invitation_connection_id_v0_1;",
        "DROP INDEX IF EXISTS idx_invitation_item_id_v0_1;",
        "DROP TABLE IF EXISTS connection_invitation_v0_1;",
    ],
    "postgresql": [
        "DROP TRIGGER IF EXISTS trg_update_connection_invitation_timestamp_v0_1 "
        "ON connection_invitation_v0_1;",
        "DROP FUNCTION IF EXISTS update_connection_invitation_timestamp_v0_1 CASCADE;",
        "DROP TRIGGER IF EXISTS trg_populate_from_services_v0_1 "
        "ON connection_invitation_v0_1;",
        "DROP FUNCTION IF EXISTS populate_from_services_v0_1 CASCADE;",
        "DROP TRIGGER IF EXISTS trg_insert_connection_invitation_keys_v0_1 "
        "ON connection_invitation_v0_1;",
        "DROP FUNCTION IF EXISTS insert_connection_invitation_keys_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_connection_invitation_key_v0_1;",
        "DROP TABLE IF EXISTS connection_invitation_keys_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_invitation_connection_id_v0_1;",
        "DROP INDEX IF EXISTS idx_invitation_item_id_v0_1;",
        "DROP TABLE IF EXISTS connection_invitation_v0_1 CASCADE;",
    ],
    "mssql": [
        "DROP TRIGGER IF EXISTS trg_update_connection_invitation_timestamp_v0_1;",
        "DROP TRIGGER IF EXISTS trg_populate_from_services_v0_1;",
        "DROP TRIGGER IF EXISTS trg_insert_connection_invitation_keys_v0_1;",
        "DROP INDEX IF EXISTS idx_connection_invitation_key_v0_1 "
        "ON connection_invitation_keys_v0_1;",
        "DROP TABLE IF EXISTS connection_invitation_keys_v0_1;",
        "DROP INDEX IF EXISTS idx_invitation_connection_id_v0_1 "
        "ON connection_invitation_v0_1;",
        "DROP INDEX IF EXISTS idx_invitation_item_id_v0_1 ON connection_invitation_v0_1;",
        "DROP TABLE IF EXISTS connection_invitation_v0_1;",
    ],
}

COLUMNS = [
    "label",
    "did",
    "recipient_keys",
    "endpoint",
    "routing_keys",
    "image_url",
    "handshake_protocols",
    "services",
    "goal_code",
    "goal",
    "connection_id",
]


# sample
# Sample invitation JSON (formatted for readability):
# {
#   "@type": "https://didcomm.org/out-of-band/1.1/invitation",
#   "@id": "2fd58cec-82a3-493b-b7c0-4d8bf6930d1b",
#   "label": "veridid.normalized.agent.anon",
#   "handshake_protocols": ["https://didcomm.org/didexchange/1.0"],
#   "services": [{
#     "id": "#inline",
#     "type": "did-communication",
#     "recipientKeys": [
#       "did:key:z6MkiUGB7fRvEL2um7zw86hmMF1cTKxE4VutQTh86mjkm4jV#..."
#     ],
#     "serviceEndpoint": "https://477e-70-49-2-61.ngrok-free.app"
#   }],
#   "goal_code": "issue-vc",
#   "goal": "To issue a Faber College Graduate credential"
# }
# tags={'connection_id': 'dd5816f7-cb10-43e0-a91f-d2f94d946bdf'}
