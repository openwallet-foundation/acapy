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
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT cred_ex_v20_v0_1_unique_item_id UNIQUE (item_id),
            CONSTRAINT cred_ex_v20_v0_1_unique_thread_id UNIQUE (thread_id)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_cred_ex_item_id_v0_1 ON cred_ex_v20_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_cred_ex_thread_id_v0_1 ON cred_ex_v20_v0_1 (thread_id);",
        """
        CREATE TABLE IF NOT EXISTS cred_ex_v20_attributes_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cred_ex_v20_id INTEGER NOT NULL,
            attr_name TEXT NOT NULL,
            attr_value TEXT NOT NULL,
            FOREIGN KEY (cred_ex_v20_id) REFERENCES cred_ex_v20_v0_1(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_cred_ex_v20_attributes_attr_name_v0_1 ON cred_ex_v20_attributes_v0_1 (attr_name);",
        """
        CREATE TABLE IF NOT EXISTS cred_ex_v20_formats_v0_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cred_ex_v20_id INTEGER NOT NULL,
            format_id TEXT NOT NULL,
            format_type TEXT,
            FOREIGN KEY (cred_ex_v20_id) REFERENCES cred_ex_v20_v0_1(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_cred_ex_v20_formats_format_id_v0_1 ON cred_ex_v20_formats_v0_1 (format_id);",
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
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT cred_ex_v20_v0_1_unique_item_id UNIQUE (item_id),
            CONSTRAINT cred_ex_v20_v0_1_unique_thread_id UNIQUE (thread_id)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_cred_ex_item_id_v0_1 ON cred_ex_v20_v0_1 (item_id);",
        "CREATE INDEX IF NOT EXISTS idx_cred_ex_thread_id_v0_1 ON cred_ex_v20_v0_1 (thread_id);",
        """
        CREATE TABLE IF NOT EXISTS cred_ex_v20_attributes_v0_1 (
            id SERIAL PRIMARY KEY,
            cred_ex_v20_id INTEGER NOT NULL,
            attr_name TEXT NOT NULL,
            attr_value TEXT NOT NULL,
            CONSTRAINT fk_cred_ex_v20_id FOREIGN KEY (cred_ex_v20_id) REFERENCES cred_ex_v20_v0_1(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_cred_ex_v20_attributes_attr_name_v0_1 ON cred_ex_v20_attributes_v0_1 (attr_name);",
        """
        CREATE TABLE IF NOT EXISTS cred_ex_v20_formats_v0_1 (
            id SERIAL PRIMARY KEY,
            cred_ex_v20_id INTEGER NOT NULL,
            format_id TEXT NOT NULL,
            format_type TEXT,
            CONSTRAINT fk_cred_ex_v20_id FOREIGN KEY (cred_ex_v20_id) REFERENCES cred_ex_v20_v0_1(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_cred_ex_v20_formats_format_id_v0_1 ON cred_ex_v20_formats_v0_1 (format_id);",
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
            CONSTRAINT fk_item_id FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT cred_ex_v20_v0_1_unique_item_id UNIQUE (item_id),
            CONSTRAINT cred_ex_v20_v0_1_unique_thread_id UNIQUE (thread_id)
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_cred_ex_item_id_v0_1 ON cred_ex_v20_v0_1 (item_id);",
        "CREATE NONCLUSTERED INDEX idx_cred_ex_thread_id_v0_1 ON cred_ex_v20_v0_1 (thread_id);",
        """
        CREATE TABLE cred_ex_v20_attributes_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            cred_ex_v20_id INT NOT NULL,
            attr_name NVARCHAR(MAX) NOT NULL,
            attr_value NVARCHAR(MAX) NOT NULL,
            CONSTRAINT fk_cred_ex_v20_id FOREIGN KEY (cred_ex_v20_id) REFERENCES cred_ex_v20_v0_1(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_cred_ex_v20_attributes_attr_name_v0_1 ON cred_ex_v20_attributes_v0_1 (attr_name);",
        """
        CREATE TABLE cred_ex_v20_formats_v0_1 (
            id INT IDENTITY(1,1) PRIMARY KEY,
            cred_ex_v20_id INT NOT NULL,
            format_id NVARCHAR(255) NOT NULL,
            format_type NVARCHAR(255),
            CONSTRAINT fk_cred_ex_v20_id FOREIGN KEY (cred_ex_v20_id) REFERENCES cred_ex_v20_v0_1(id) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """,
        "CREATE NONCLUSTERED INDEX idx_cred_ex_v20_formats_format_id_v0_1 ON cred_ex_v20_formats_v0_1 (format_id);",
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
        "DROP TRIGGER IF EXISTS trg_update_cred_ex_v20_timestamp_v0_1 ON cred_ex_v20_v0_1;",
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
        "DROP INDEX IF EXISTS idx_cred_ex_v20_formats_format_id_v0_1 ON cred_ex_v20_formats_v0_1;",
        "DROP TABLE IF EXISTS cred_ex_v20_formats_v0_1;",
        "DROP INDEX IF EXISTS idx_cred_ex_v20_attributes_attr_name_v0_1 ON cred_ex_v20_attributes_v0_1;",
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


# sample
# category=cred_ex_v20, name=c3338aca-1c7c-42b0-8583-1cd7a665bf74
# json = {"thread_id": "9aa32904-2235-4eac-92d3-2e516429dc3e", "created_at": "2025-06-17T15:44:28.232584Z", "updated_at": "2025-06-17T15:44:28.232584Z", "connection_id": "13458fb2-c080-414c-94bd-b0f4745e5afa", "verification_method": null, "parent_thread_id": null, "initiator": "external", "role": "holder", "state": "offer-received", "auto_offer": false, "auto_issue": false, "auto_remove": false, "error_msg": null, "trace": true, "cred_offer": {"@type": "https://didcomm.org/issue-credential/2.0/offer-credential", "@id": "9aa32904-2235-4eac-92d3-2e516429dc3e", "~thread": {}, "~trace": {"target": "log", "full_thread": true, "trace_reports": []}, "credential_preview": {"@type": "https://didcomm.org/issue-credential/2.0/credential-preview", "attributes": [{"name": "person.name.family", "value": "DOE2"}, {"name": "person.name.given", "value": "John1"}, {"name": "person.birthDate", "value": "19501011"}]}, "formats": [{"attach_id": "anoncreds", "format": "anoncreds/credential-offer@v1.0"}], "offers~attach": [{"@id": "anoncreds", "mime-type": "application/json", "data": {"base64": "eyJzY2hlbWFfaWQiOiAiRldESEJyTWZ4TkxGZFVROWNHb2VUbjoyOnBlcnNvbi1kZW1vLXNjaGVtYTowLjI1IiwgImNyZWRfZGVmX2lkIjogIkZXREhCck1meE5MRmRVUTljR29lVG46MzpDTDoyODM4MzIxOmNkMC4xNCIsICJrZXlfY29ycmVjdG5lc3NfcHJvb2YiOiB7ImMiOiAiOTEzMjgwNTc1ODUzNjE1OTE1OTgzMzQzNDAyODYzNzE1OTYwNDQyNzQ2MzEyMzUyNzczODA3MjM4NTEwMDUwMjcyNDc4MTA1MjI3MzgiLCAieHpfY2FwIjogIjgxNzI3MDAwNDExNjE1ODEzOTMzNDgxOTIyNjY5MjgwMjk1MDQ3NTQ4MzEzMjkyNDE0NTY3MzQ3MDE3MTIzMzgyNDg2NTAzMDQ3NTYxODI3MDc3MTYyMTYwNjM0NDg5NTEzOTI2MjA5MjQ0NDIzODEyNjQ0MjY2NjcwMzIwOTUzODIzNjQwNTA2NzY2MzkzNDQ3OTUzNjQ5MDc3MjE0NDU5Mjc2NjkyNjUxODE1Mjg4MTIxMTgwOTYxMDU0MjE1MjM0MTczNjk1OTYwMzc0NDI4NTUxNzY4MjY0MDk1Mzg4MDE2MzMyNTAzOTA0NDY5NTk4NDMyODA2MjY2NTk1MzU4MjQ1Mjg2MDIzNjY5OTYyMDU5Mzk2MDI2NTgzNjAyNDgxMDE1NjY2ODgyNTI3ODA4OTAzNDU3MjMxMTIyMTIzMjY5Njg2MDE1NzUxNzEyODIwNDM1Mzg3MDI2NjIyNzMzMDQ1NTgyMTI1MTMxODM5Njk4NTM0NjY3MDMyOTc3Njc5ODMwMTE4MzEwODA1NjM1OTc0ODQ4NzM0OTc5NDk4NzkwMjU4MjIwNzE1ODUxMTY5MjU4MDM1MTgzNTgzMDA4ODM0NzMyNzI3NDM3Nzk3MTc4Nzg3MzAzMDU4NzA4OTAyNjMxNTM4NTY0NzY0ODUwODA0MDUwMzIxMjI2MjczMzM0MjUyOTI3Njk5Mjk1NTMwMDE5Njg5NjU4MTg3ODI4NDk5ODk4OTM5MDU0MTE4NzEyMzMxNjk4MjI5ODAxMTQ0MjgyMDAwOTgyNTg1NTM0MDE0MjUzNTEyNzA4ODg0MTk2NTYwMTc3MTc3NzI1MzE1NzIyNTcxMTA5MDAzMjk2NDI3MzU4MzQzMzkwMTE5MTIzNjIxNjU5NTY4ODg5MjAyNDY1MTU3MDYyNjI5NjMyOTA3NiIsICJ4cl9jYXAiOiBbWyJwZXJzb24ubmFtZS5naXZlbiIsICIzNTEzNTk4MzUxMzQxMDc1NzU0MTg0NzkxNTU2NDUyMTczNDE0NTc4MzQ0ODQ5MzQ3NDYwMjUxNTY2NDk1NTM2NTcyODQwOTMzNjUyMjQ0NTk0MDI0NTU3MTI0ODQyNDkyMTIyNTc0NDk5MTczNDgwOTIxMDI5MTQ5OTU4ODM3MTczNDI0OTI1MjM2NTk2NjQ2NDQzNjE2OTM3MTAyOTA0MzkzMDk5MjA5MjgxNzg0MDAxODM5MjgzMjg5NzcwNTg4NDIwMjc3OTgxNDgxMzUwNjI0NjY2NTczMTc5MDUwODg4Mzk5MzgzMTA0NzgyMzk0Mjc0NTI5MTA2NDI5Mjc1NDA3NDg0MDc3ODUwMjM0NDA3MTQ4Mzc4MDU0NzA5Mzc0MjUwMjkzMDA3NzMzODc4MzA5NjE3NDgyMzg5NjQ0MDY5MzYzMTA3NTQ2MDE2MzAxOTM2ODU2MDAxOTM1NDMxODI2MjU4OTYxMjAwOTkxOTE4MDEyMDQ1NjUwMTg3MjE4MjkzNDc5OTM3NDEzNjY2ODA5NjE1NDExMjYxODEwMzU1MjM4NDczMzg4NDE0OTE2ODQzODIwMDUxMjI0MDAyNzEwMzQyMjIwODU4MjkxNjg5MzI4ODI2NDQ0NTk4NDQxMzIzODEwNzYwNDQ5Nzk0NzE2NjcyOTgwNjc2NjMzMzkwMjIzMjE1MDUwMjU2NDg3MDI5NTYyODYyNTk2MjI3NjM3NTgwODk5MzUwNjMwOTcwNzE4ODM1MDA2MTg2OTEzMDE4MjIxODYyNDg3MTU0ODEzODM3NTM5MDA4MTM3MjgwODM3NjM0OTgwMzQ1NTQ5Mzc1MTc4MjQ2MjY1NTUxNDc2MTA1OTc5NjE5ODIzODgwNDUyNzU2NjY3NzQ5NjM2NjMzMTc5NDE3MjM5NTg2NDE2MDYiXSwgWyJtYXN0ZXJfc2VjcmV0IiwgIjE5Mjk4NjE0MDMzNjYzMDIzMzUwODcxMjEyNzYwNDEyMzg0Mzk1NzE0NTk4MzI3NTM2MjM4OTE0ODAwOTY2NTkwNzIwNjIwMDAwNTE0MDc2NjQ1ODM5MjEzOTc3MTY0NTY5MTI5OTY3NDM2MDEyNjExNjk5OTQxNDc1OTMwNDM2NzQwODQwNjI1NjU4MDM2OTkwNDgyNzE2ODgwNzg1MjkwMTE3MTA2ODAzMjI0MDE0NTY1NjExMDI1NjY4NDcyOTg5MDc5MjA2MjUzNjgxMjA3NjI2NzM4NTk0MTczNTEzMzIwNTExNzc1MTg1NDQyOTQ4MDkyOTExMDA0OTk4NzIyMjY5MjYwNTkxNDA2MzU0MzU0NDkzNTI5NTc0MDUxODUyMjk5NzY0MzE3NTM2NDY4ODczOTQyMTExMDYyNjU2Mzk1MDEwMzc5Njg4MzA2MTQwOTIzOTA5NTk1ODAyNDE4ODUwNjc0NDI5NDYxMzA5NTU1OTg1MzQ1MTQ3MjQ3NDUxMDQxNzYxNzE4NDcwOTc0NDk3OTIyOTExNDMxNTE3MzgxNjkyOTEwNTUxNTczMzQwMDQ2NDIxNjgyODI5ODYxMDUzNzYzNTk5MjAxNTU0MjUzMDgzODM3MTAyODgyODgyNDM1OTg1MjEzMjkwOTY3OTE0MTkwNDg1ODQzNzgzNDE0NTI2ODk4NDcxMjE1MjU3MTQyNjg4OTU0ODY1NzYwNTYwNDEwNjg3MDQ3NjA4NTg5MTcwODk3NzAyNTkzOTMzNTM2Nzg1OTcxMTg5MTczMzI1NTk5NTc4NjIzNjAyMDI2ODYyNzQ4MjE4MDQyNzQwODAzODg3ODA5MTExNDg3Mzk5ODY0MDY2MDg1Njk0NzkxNzU3Mjk2NTA3Mzc0MjI1MTcxMTExMzkxNTU0MzU1NDU2MSJdLCBbInBlcnNvbi5uYW1lLmZhbWlseSIsICIyMjYzMzc3NjQ4NzAyOTE3MzIyMTQwMTg1ODM1NTIwNTEzMDI5NDc1OTU0NTE4NjgxNjIzMjUxMTM5NDU3OTEwOTYwMDExMjUzMjgyMTA3NTk1Njg2OTI3MjQxNTIxMjgxODM2NjU4NzkxOTAwMzY0NDc3NTc1NjM0MDUyODIyODY0MDY3NjUwNzI4NzQ1Njk2NjcwNDM1NzYwMDE2NDE4MDExNTA1Njg4OTk2OTE3MjcwMDQ5NjgwOTU1MTc4ODY5MTEzMDA5NDMzNTQ2ODAzODQwMDk5NDQzODcyOTcwMDE3ODA1NzE4NzA0MzUxODEyNjAyMTY5Mjk2NTI4MjYzNjY0NzAyNTk4NzUyOTM0NjUzNzY1Njc1Nzk5NjUwNDA3OTI4NzY5MTU0MTkzNDg3NjI1MTQ5MTEyODAyMzYzMDcyMzYzMDM5MDA3NTc4NDA4NTA1ODUyODAwMDYxODk4MDU5MDI5MTE0NDYwMzgyMTg3NjY5ODE4NTg1NTk3NzYwOTQ3OTUzMjE3MzQ3MjM4NTc1NjE1ODU5NjYxMzAwNjY4OTk2MTg4MzI1NTY0NzM5Mjg5Mzc5OTYyMzk5NDMwMTc0NjQ1NTg2MjQ5NDM5OTA3Njg4MTg4MDIzMjk5NjM2OTU4MDMzNjgyOTM3OTg1OTMxMjk4OTExODM1NDY3ODQ2Mzc5NDk4MDkxODk4MzUzNjA2MzEwNTIyNzczOTE4NzU4MTk4MzM2NjIyMDA0NjQ5MTQzMjkwMTc2ODQwMDU4MTIyNTM4NjQ3NTY4MzgzMTE0MDAzMzg2MDMyNzEzMTA0MDcyNTM3NDkwOTM0OTk5MzU5MjEyMzc3NDQ4MTU4ODY4MTM0OTE4NjIwMTI1NjU2MTE4NzM5NjQxNjcxNDU2ODc5MDk0MjM0NDE4MDY4NTEzMDQ2Il0sIFsicGVyc29uLmJpcnRoZGF0ZSIsICI5MTcwMDI5NzkyNjU1ODM1NjYyNjQ1MDc5MTQwOTY4NTM2MjExMjA2OTkxMDYwODc1ODk1Nzc2NzM1MjkzNTY1ODI0NzU2NzcxMTEzOTI3MzMyMDAwMjkzMDE2ODAxNzU2NDcwMjQwMDYzMTAxMjc1NDYwMjgzMzAxNzkwNjM4MDI3MTMwNDM0Mzk1ODIzMTAwODA3MTUwMjI1NTUzNzkyMDg1MDc5NjAwNzMwNDQwNDI4NDA2NjIzMDkxMTg4ODc0MzIzMDczMjc4MDcwNTMwNzg2MDM1MzQ3MDE5MDQ2MjMxNDYxOTg0MjIzNDkwNTg3MzgyNjQwMDQ1MDYzMDIxODIyNjQxMzI4ODcyNDAxMzAxMTU0MTI3NDM3NzM2OTkzNDY5NDkwMDc3ODY3NTQzNzY5NzYxMTI2ODE4ODQ2NTE1ODU0Njg2OTM3MDIyMzc3MzQ1MzIwODA3MTQ5NjU0MTk0MjY4MTc5MzU1MzUxMDM0NTUzNjg5MTU1NDAxNDgyNzM0NzYyMjQzOTc0NTEyOTc3NjkwNzg5NTAxNzM2NTgwMTQ1OTU4NzkzODQ1NDY1Mzc1ODMyMTA0OTQ0MDc5OTgwNTUwNjM4Nzk0Nzk1NjQ4NTExODU5MzY1MTIwODU4MjI1MTE2Mjg5MjY1NjA5MDE4MjMzMTIxODg0ODE0NTE1MDU4MjkzNTE4NDEyMTY2MTM5NDE0NDAzOTQ2MzU4Nzk4Nzk0NDgzMzc3NDQwMDAxNjYxOTk1NzI5MDk3MzA0MzczNjA5MDUwMDc1MDg5OTg0MDgwMTU3NDY5NDA0MDQ2MTIwODk0Nzg5MTk1NDc4NjQ4MDIxMjUzODYzMDMyNDgxMzg5MTczNTUxMjc0Mjg5MDc3MzYxNzU4ODMxMjg3MTQzMDg1MzY0OTUwNjgzOTA1NzMiXV19LCAibm9uY2UiOiAiOTQyOTk4Mjc0MTQxMTI4MjYxMTk4MDAyIn0="}}]}}
# tags={'thread_id': '9aa32904-2235-4eac-92d3-2e516429dc3e'}
