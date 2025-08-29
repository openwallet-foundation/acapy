"""Module docstring."""

CATEGORY = "anoncreds_cred_ex_v20"

SCHEMAS = {
    "sqlite": [
        """
        CREATE TABLE IF NOT EXISTS anoncreds_cred_ex_v20_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            cred_ex_id TEXT,
            cred_id_stored TEXT,
            cred_request_metadata TEXT,  -- JSON string
            rev_reg_id TEXT,
            cred_rev_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_anoncreds_cred_ex_item_id_v0_1
        ON anoncreds_cred_ex_v20_v0_1 (item_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_anoncreds_cred_ex_cred_ex_id_v0_1
        ON anoncreds_cred_ex_v20_v0_1 (cred_ex_id);
        """,
        """
        CREATE TRIGGER IF NOT EXISTS trg_update_anoncreds_cred_ex_timestamp_v0_1
        AFTER UPDATE ON anoncreds_cred_ex_v20_v0_1
        FOR EACH ROW
        BEGIN
            UPDATE anoncreds_cred_ex_v20_v0_1
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = OLD.id;
        END;
        """,
    ],
    "postgresql": [
        """
        CREATE TABLE IF NOT EXISTS anoncreds_cred_ex_v20_v0_1 (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            cred_ex_id TEXT,
            cred_id_stored TEXT,
            cred_request_metadata TEXT,  -- JSON string
            rev_reg_id TEXT,
            cred_rev_id TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_item_id FOREIGN KEY (item_id)
            REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_anoncreds_cred_ex_item_id_v0_1
        ON anoncreds_cred_ex_v20_v0_1 (item_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_anoncreds_cred_ex_cred_ex_id_v0_1
        ON anoncreds_cred_ex_v20_v0_1 (cred_ex_id);
        """,
        """
        CREATE OR REPLACE FUNCTION update_anoncreds_cred_ex_timestamp_v0_1()
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
        CREATE TRIGGER trg_update_anoncreds_cred_ex_timestamp_v0_1
        BEFORE UPDATE ON anoncreds_cred_ex_v20_v0_1
        FOR EACH ROW
        EXECUTE FUNCTION update_anoncreds_cred_ex_timestamp_v0_1();
        """,
    ],
    "mssql": [
        """
        CREATE TABLE anoncreds_cred_ex_v20_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            item_id INT NOT NULL,
            item_name NVARCHAR(MAX) NOT NULL,
            cred_ex_id NVARCHAR(255),
            cred_id_stored NVARCHAR(255),
            cred_request_metadata NVARCHAR(MAX),  -- JSON string
            rev_reg_id NVARCHAR(255),
            cred_rev_id NVARCHAR(255),
            created_at DATETIME2 DEFAULT SYSDATETIME(),
            updated_at DATETIME2 DEFAULT SYSDATETIME(),
            CONSTRAINT fk_item_id FOREIGN KEY (item_id)
            REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        """
        CREATE NONCLUSTERED INDEX idx_anoncreds_cred_ex_item_id_v0_1
        ON anoncreds_cred_ex_v20_v0_1 (item_id);
        """,
        """
        CREATE NONCLUSTERED INDEX idx_anoncreds_cred_ex_cred_ex_id_v0_1
        ON anoncreds_cred_ex_v20_v0_1 (cred_ex_id);
        """,
        """
        CREATE TRIGGER trg_update_anoncreds_cred_ex_timestamp_v0_1
        ON anoncreds_cred_ex_v20_v0_1
        AFTER UPDATE
        AS
        BEGIN
            UPDATE anoncreds_cred_ex_v20_v0_1
            SET updated_at = SYSDATETIME()
            FROM anoncreds_cred_ex_v20_v0_1
            INNER JOIN inserted ON anoncreds_cred_ex_v20_v0_1.id = inserted.id
            WHERE inserted.updated_at IS NULL;
        END;
        """,
    ],
}

DROP_SCHEMAS = {
    "sqlite": [
        "DROP TRIGGER IF EXISTS trg_update_anoncreds_cred_ex_timestamp_v0_1;",
        "DROP INDEX IF EXISTS idx_anoncreds_cred_ex_cred_ex_id_v0_1;",
        "DROP INDEX IF EXISTS idx_anoncreds_cred_ex_item_id_v0_1;",
        "DROP TABLE IF EXISTS anoncreds_cred_ex_v20_v0_1;",
    ],
    "postgresql": [
        """
        DROP TRIGGER IF EXISTS trg_update_anoncreds_cred_ex_timestamp_v0_1
        ON anoncreds_cred_ex_v20_v0_1;
        """,
        "DROP FUNCTION IF EXISTS update_anoncreds_cred_ex_timestamp_v0_1 CASCADE;",
        "DROP INDEX IF EXISTS idx_anoncreds_cred_ex_cred_ex_id_v0_1;",
        "DROP INDEX IF EXISTS idx_anoncreds_cred_ex_item_id_v0_1;",
        "DROP TABLE IF EXISTS anoncreds_cred_ex_v20_v0_1 CASCADE;",
    ],
    "mssql": [
        "DROP TRIGGER IF EXISTS trg_update_anoncreds_cred_ex_timestamp_v0_1;",
        """
        DROP INDEX IF EXISTS idx_anoncreds_cred_ex_cred_ex_id_v0_1
        ON anoncreds_cred_ex_v20_v0_1;
        """,
        """
        DROP INDEX IF EXISTS idx_anoncreds_cred_ex_item_id_v0_1
        ON anoncreds_cred_ex_v20_v0_1;
        """
        "DROP TABLE IF EXISTS anoncreds_cred_ex_v20_v0_1;",
    ],
}


COLUMNS = [
    "cred_ex_id",
    "cred_id_stored",
    "cred_request_metadata",
    "rev_reg_id",
    "cred_rev_id",
    "created_at",
    "updated_at",
]


# Sample data
# {
#     "cred_ex_id": "eb7fed7c-5e7e-4bb6-bb82-32780fd63a45",
#     "created_at": "2025-06-17T13:47:26.291502Z",
#     "updated_at": "2025-06-17T13:47:27.301751Z",
#     "cred_id_stored": "c9444d1a-f8e0-4ed6-b0f8-3a600402fa04",
#     "cred_request_metadata": {
#         "link_secret_blinding_data": {
#             "v_prime": """
#                 9406562820507241585983287454989437486514032699441347054259920783951534
#                 163973711344650680682754794669443080900213783063166059198909406664279688
#                 300598945564399079004055344262800274334938514137551891266326615276723415
#                 714788037189349063581609860265405338650594771465454190744481496575071563
#                 455134962252576233641169753169075939245823997475573680713130602223423635
#                 148426947726462608510446340271448068887500520207926004434844895029036726
#                 315804140396167166070473718387770185351312778839036880939063529220363836
#                 106784029340973709865343042065905808741119097205434298720074854309820461
#                 914299351004530310626644354596154866168024340425118908990026324699
#                 """,
#             "vr_prime": """
#                 18594B31E16EBF1672A3D7C764B5094942FC6BF2B0B3F4690E100348ED1113AE
#                 """
#         },
#         "nonce": "182313473409180134758352",
#         "link_secret_name": "default"
#     },
#     "rev_reg_id": """
#         FWDHBrMfxNLFdUQ9cGoeTn:4:FWDHBrMfxNLFdUQ9cGoeTn:3:CL:2838321:cd0.14:
#         CL_ACCUM:0f8b06b6-d775-4fc5-a4fe-a5e614ee796c
#         """,
#     "cred_rev_id": null
# }
