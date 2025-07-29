#poetry run python acapy_agent/database_manager/test/test_db_store_credex_insert.py
                   
import sqlite3
import json
import os
from acapy_agent.database_manager.databases.sqlite_normalized.handlers.custom.cred_ex_v20_custom_handler import CredExV20CustomHandler



# Configure logging
# logging.basicConfig(
#     level=logging.DEBUG,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     handlers=[logging.StreamHandler()]
# )


# Define the database path and ensure the directory exists
db_path = "test_credex_dbstore.db"
db_dir = os.path.dirname(db_path)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)

# SQLite database connection
conn = sqlite3.connect(db_path)
cursor = conn.cursor()


cursor.execute("PRAGMA busy_timeout = 10000")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY,
        profile_id INTEGER,
        kind INTEGER,
        category TEXT,
        name TEXT,
        value TEXT,
        expiry TEXT
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS cred_ex_v20_v0_1 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL UNIQUE,
        item_name TEXT NOT NULL,
        connection_id TEXT,
        cred_def_id TEXT,
        thread_id TEXT NOT NULL UNIQUE,
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
        FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS cred_ex_v20_attributes_v0_1 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cred_ex_v20_id INTEGER NOT NULL,
        attr_name TEXT NOT NULL,
        attr_value TEXT NOT NULL,
        FOREIGN KEY (cred_ex_v20_id) REFERENCES cred_ex_v20_v0_1(id) ON DELETE CASCADE
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS cred_ex_v20_formats_v0_1 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cred_ex_v20_id INTEGER NOT NULL,
        format_id TEXT NOT NULL,
        format_type TEXT,
        FOREIGN KEY (cred_ex_v20_id) REFERENCES cred_ex_v20_v0_1(id) ON DELETE CASCADE
    )
""")
conn.commit()  # Ensure tables are created before insert

value = json.dumps({
    "thread_id": "34ec5d84-2760-43e7-b334-843a363a6b7e",
    "created_at": "2025-06-28T04:34:38.150413Z",
    "updated_at": "2025-06-28T04:34:38.150413Z",
    "connection_id": "c2d75e3a-2242-4a96-9eb9-f8de66e02272",
    "verification_method": None,
    "parent_thread_id": None,
    "initiator": "self",
    "role": "issuer",
    "state": "offer-sent",
    "auto_offer": False,
    "auto_issue": "true",
    "auto_remove": "false",
    "error_msg": None,
    "trace": True,
    "cred_proposal": {
        "@type": "https://didcomm.org/issue-credential/2.0/propose-credential",
        "@id": "3972204b-0f10-446f-be53-845d32a15a37",
        "~trace": {"target": "log", "full_thread": True, "trace_reports": []},
        "credential_preview": {
            "@type": "https://didcomm.org/issue-credential/2.0/credential-preview",
            "attributes": [
                {"name": "person.name.family", "value": "DOEs"},
                {"name": "person.name.given", "value": "John"},
                {"name": "person.birthDate", "value": "1950101"}
            ]
        },
        "formats": [{"attach_id": "anoncreds", "format": "anoncreds/credential-filter@v1.0"}],
        "filters~attach": [{"@id": "anoncreds", "mime-type": "application/json", "data": {"base64": "eyJjcmVkX2RlZl9pZCI6ICJIVVlvTjM1Uld5bUx5SDlhdGZ3ZkZVOjM6Q0w6Mjg1NjY5MDpjZDAuMiJ9"}}]
    },
    "cred_offer": {
        "@type": "https://didcomm.org/issue-credential/2.0/offer-credential",
        "@id": "34ec5d84-2760-43e7-b334-843a363a6b7e",
        "~thread": {},
        "~trace": {"target": "log", "full_thread": True, "trace_reports": []},
        "credential_preview": {
            "@type": "https://didcomm.org/issue-credential/2.0/credential-preview",
            "attributes": [
                {"name": "person.name.family", "value": "DOEs"},
                {"name": "person.name.given", "value": "John"},
                {"name": "person.birthDate", "value": "1950101"}
            ]
        },
        "formats": [{"attach_id": "anoncreds", "format": "anoncreds/credential-offer@v1.0"}],
        "offers~attach": [{"@id": "anoncreds", "mime-type": "application/json", "data": {"base64": "eyJzY2hlbWFfaWQiOiAiSFVZb04zNVJXeW1MeUg5YXRmd2ZGVToyOnBlcnNvbi1kZW1vLXNjaGVtYTowLjAyIiwgImNyZWRfZGVmX2lkIjogIkhVWW9OMzVSV3ltTHlIOWF0ZndmRlU6MzpDTDoyODU2NjkwOmNkMC4yIiwgImtleV9jb3JyZWN0bmVzc19wcm9vZiI6IHsiYyI6ICI5NjYxOTk0NDM1MDQ1MjM4MDI5MzM0ODkwMDAwNTcwNDQ4NTE2MTg1MjQ4NjI2MzM1NDg5MTIzODAzMTc5OTY4NTU2OTY0MTg5MzYyOCIsICJ4el9jYXAiOiAiMzk5MDcyMjI2Mjc5NjI1MDU0NDU4ODY2MDExMzY5MDg1NDc4MzI2NDYxMjM4NzkxOTU5OTIyOTk3MDg2NzQ0MDc1NDk1OTQ1ODk1NzQ1NDg2Mjc1MjQxNzYxNTYyNjk5NzA1MjcwMDE4NjY1ODQ4MDAwOTYwNTk4MTc5ODY1MTE2OTc5NTQ4NDI1NjUwMzQxOTI5MDYyOTQ4NTA5NzIzOTExMzAzNjk4MjI3NDUyMTAyMDEzMjU4NzE2ODM4NzA2OTQxODQ2NzA2Mzk3MDgxMDc2OTI1MTMyMDU1MzE0NTQ1OTgyNDg4MDE4NDc3MDQ2MjE4NTg2NjY5MjU0NzMzNDA1MzUzMTIwOTI2ODk4MDU0MDcyNzA5MDk1MjUyMDEwODExNTAxNjA5NjAwMDA4OTAyMzQyNjc3Nzk5Nzc2NjAyMjcwOTIzNTQ0NTkyMzg3MTM3NTU1MjQyOTY0NjY2MTA3MTE5NTgwMTUxNzQ0NzcyMzc4ODc1ODQ2MjUwMDAzNDc1NDM3MDExMDI0ODM1MDMzNzEyMjU5OTY1NzI5NjY0NjA2Njk2NjI5Njc2NjY1MzQ3MTE2MzYzMDczMTM0MTQ0MjA1MzU2OTM4OTc5NDA4NTA2MTkwMDMyODI0MDEzMjM5OTM5NzkwMDk4NjI5NTg3MzQwNzIxNDE3MjE1MjAxMjgwNzg5ODkzMzc2MzgwNzA0MzQ2NjA4MTI4NzEwMjE3NDAwMzExODIzNzA4MzI3MDk4Njk1OTYzNTIxOTcwNjMyNTg5ODQ3NDEwMTU5Nzg2NTI4MzY1OTM2MjQyODM1Mzg5MTE2ODYzNjA1ODA4MzE5ODM3MDYxNDExNDAyMTcyMjE4NjM5Mzc0ODI4NDUxMTEzNzk5NzMzODY5MTA2OTA0ODkyNzM5NDg2NzY5NDY2NDI2IiwgInhyX2NhcCI6IFtbInBlcnNvbi5uYW1lLmZhbWlseSIsICIyMDEwOTc0ODc1MjE3ODM0NzY1MzczMTM0OTQxMjY1NjY1ODkyMTMzNjQxMjA0MzYyMjI3NTY5NjYxODg4NTc1MTk1ODc5MzYzNzY4MjgzMDg1ODEwNDQwMTU2MDAyNzQ2NzU4MTIyMDY1MDg1ODQ3NjU3NTAwODg0OTkyMDE3NDI3NjAyODU1NDczNTE3Nzg2NDcwNTIzNzk3NzQ4NTc3Mzg0ODY5NDMyNjU5NDcyMjgwMTY0MjUxMTAyODE2ODkwMzQ4NDE5MjA0ODQ4OTE1OTc1MzA3MTc4NDQ3MjgzMjMzNjkyMjA2Mzk5MjQ0NjQ0MjIxMTQ4MjA2MTc2OTI0NzgxMDQ3NTQ0MTc3MDM5ODg1Mjc1MDA1Nzk1NTczNDk1NDQxMDM4OTgzMDY3ODMyNTY0MDgzMjk2NjIzOTExODU4MDgyNDc4ODAzMTM3NzQwMDAyNjUyNzI3NDYxMTk0MTA0NDc4Njg5Nzc3NjQ2ODcyMjUwMTE5OTg0OTkxMzkzMzY2ODg5MDA0Mzc0NDI0ODgxMjc3NTAyNDI4OTU1NTIzMDc1ODI0MTc2NDgxNzM0OTE4ODcxMjE5NTQxMDMxOTYzMjQ0NzQzNDgyMDQ5NTkxMjc0ODcxNTQ0MTg4MTk1MjIxMDE2NTk3MDE4NjAzODE3MDMzNjAxMzQ5NjI4NjAwNjIwODMwMjU2NzE1MDAzOTI3NzI1NTc5OTE1MTkwNDE4MjAyMTI3MDcwMzUyOTk4NTM5NjI1Mjc1NDE0NDIxNjQ5ODE2NzQxNTA3NjE5NDQ2ODkzOTc0NzUzNjA0MjQ0NDE5Mjk4NDMxOTgxNjQ2OTI5ODc4NjkyMjIxMjM3NDI0MjQ2MDMwMTAwMjkwMzQ4MjY1Mjg2MzU1NDE5NDU3MDMzMzI0NTY2NjkxNTI2MTcxNDY0Il0sIFsibWFzdGVyX3NlY3JldCIsICI1MTU3OTYxMzQ4OTMwNTY1NjQ5MTQzNDQ4NTYwMjc4MTE1NTA0MzM4MDY5OTMwNDgyNDIzNTkxNjc1MDA2NTEzMDk5NDYyMTMzMjI1NzQwODA0NDI5ODc2ODU0NDIzMjQ4NTIzNTUzODg4MjgzODM5Mzk0MzI3OTg0OTY5Njk3MzEyNjI4MTYxOTQwNzU3ODAxNjU5MjgyMjIyOTU3Mzc3MzgxNDQ4Nzk2ODQ2ODc5NDA3OTE3NDU1ODQ0OTMzODYxNzY3NjUwMTM5Njk2OTU2MjM3Nzk5Njk4NzM1MjA2NjI1MDA2NDY3NDk2MDk3NDcwMTM1ODM3NjYzNDQ5MjE0NjYwNDExOTY5OTc4Mjg4ODM0MTMyMzg2NDQzMzQwMjMxMjQ2MzY1NjgxMjYzNDI4MzYxNDQ4Nzg3NTgwMzE3NDQ5NTEyMjkzODM2NjMwODEzMDA5MzcwNTc0NjQ1NDAyNjI4NTg0NjA0MTMwMTczNTAyNjY1NjEyODM4NzU5OTA1ODgxNzM2NDMyMTc0MjE5Nzk4NTAzMTkzNjI4NDI3MzY1MjU5ODIxMDI3NTg2NjU5MTkxMDgyMzg5NDIzMDEyMTU3MzUxNzc2MjY4MzA1MjM1NTc5MjI1NzQzNjUzNTY2ODk1MjE0NDA3ODM2NTM3MTUxMTE1NDk3OTQyMzg4MTkzMjU2NjkzMDI0OTMyMjEyNDg1MjIyMjg4MjgxNjIyNjYyODkwMjk3ODQ3NTMwNTA5NTkwMTg0ODM0MTk3NTA4MTQ4NzIyMzQyMDA4Njk1OTM5ODk0NTQ0NTAwNjYzMjMyMjEzNjg5MDM3OTUxMjk0OTM5MjIyNzMzNTI5MTI0MjY4MDc3NTcwNzM1MDYwNDAzOTU3NzYzMzU0MDE3NjM4NTkxNTg4MjI3NzUzMDExNzk1MjMiXSwgWyJwZXJzb24uYmlydGhkYXRlIiwgIjE3MTExNjc1Njg5NjgzNzkyNzc3NDYxMjIxNDcwODY0ODUxMzM5OTQzMDQ0Njk1MDE4MTM1NzczNzMzNDYzNTU3NjYxNDQ3OTU4MjUxNTMxMDI1NTExMTc2ODgxMjY3NjczMzI5ODg1Mzc3MjYyMDI5ODI5MTA3NzQ0MDcyMzY0NjIxNDQzMTQzNjQzNDgyNDgyNzQ2OTU0NjM1MDg4NTc3NzE0ODExNTYyNzYyNDcwNjUxNTIyMzMwNjgzMzMxOTc4ODMzMzgxNTQ5NTAwNTk0MTYyMjQzNTA4MDU2MDQxNjc2NDg5MDQ5Mjc2NzQ0NTI2MDM2MDQ3NTMxNDQ4NTQ3MzM1Njc5NzI0NTA3MzM5NzkwODQxMzY4MTYxMjgzNjQ5NzY2ODYwNjY2NzcxMzQ1NDg3MzA2NzUzMjAzNjA4NTA4OTYxMzY1MjU4ODY4NjQxOTU0NzUxNjEzNzgyMDMzNzQwMDYxMzQzMDk4MTA3NDU4MDUzODA3NTQzOTIxMTY2MTY1NDU5ODY1MjE5NDYxNzM0NDA1NDMyNTA0MTIzODIxMDkzNTUyNzM2MDQ5NTcxOTcwNTc1NjcwNDU5ODMxOTI2ODgxNDA5NjAwNTYxNjg0OTQyNTM0MjUxNDk0MTk1NDUyMTY3Njg1MjI4NTgxNjU1NTYyOTE0NzM0MjUwMDIwNTU3Mjg2Mzc5NDA4NDE5NDgyMjkzMTgxMTI3NjE4MTE4NTE3NzY2Njg1NjQ2NjYzMDgyMDMxNjM4OTAyNDc3ODMwODAxNDkzOTAxNjMzMzEwMjQxMTAwNzk2NTAyOTcwNDMxMDc4OTE2NDMyMjQxOTkwNzUzMjI1Njg2NTk3ODAxMzgzMzI2NTU4NTA2MzE2MTE2OTg2NzQzMDI4ODc2ODA3ODQ5ODMyNzY1MjQ2NTY2OTEiXSwgWyJwZXJzb24ubmFtZS5naXZlbiIsICIxOTY0OTIyMTQ3OTcxNzQzNDY4ODIzNDU3Mzc0MDQ4NDQ5NDkwMTg3Njg1MDcwMzM1OTIzNTk0OTM0NDI5NTQ1NTYyMzgzOTA1NTgzNTEzMDkzODA0Nzc2ODUzMTM4NTA2MjUzODIwNDQ1MzU2MzQ1NjgzOTEzNjg5MDgxMjcyOTExMTM2NDY3MzA4Mzk4NjEwMzg0NTMyODQyMDQ2MjU0MzYyNDU4NDI0NTM3MTI1OTUyNTQ3MTM1OTM1MTkyMjIzNTM2MTcwODI2MTI3NjI0OTIxNDU2ODg4NjA3MTU2MTE2MzY3NDIwNDUxMzE5MjczNTQ1MzUwMTMwMDcxMjQyOTYwNTM1MjI0ODczNTc3MTk0OTE4NDA3ODA4MTEzNDU2ODgyNzEyOTEwODY2NzQ1Mjc2MjU4NDU0MTMzNTUxMzIzMjg0MjAxNDU0MjA4OTI3ODk0ODU1NTc0Mjg0MjM1ODc3NTU2NDYxODc3MDg3NTM4NTM4MzQwNzIyNTI3MDY0NjE1Nzk2ODg3MDU1NDg5MDQyNTI2Mjg0MDA5NDI2MDE4Njg4MzI3NzU1MjQ5Nzc4Nzc2MjM5NzMyMzU4MTQwMDE4MzI1ODY3NzQyOTE3NDc1MDg0NDgxMjY1MTk0NDU5MzA2NzU2Mzk2Mzc1OTU4NDM2NDUxMDQ5NTM0MTkzNTAwMDIwNTQwMjQ3Njk2MjUwMDAyMjQzMTM3ODk1NDg1ODc0NjgxODk0OTg1Mzg4MTI3NTYxNDkxOTY2MDA2MDkxNDM4MTYxMjY2NjcwMzUxNzI0NjQwMjkwMTU4NjczMjMyMjUyNDMwODYzODQ5MzM3MjMzNDkxMDI1NDc1NzU1NzAyOTc0OTU1OTU3NTUxNjg2OTU5NDY1MTc2MTE3MDE1NDE5MTM1ODM5OTk1NTM5MjM0MzMiXV19LCAibm9uY2UiOiAiNzAyMzAzMjY0NDA4NTcxMDEyMTk4ODU2In0="}}]
}})
tags = {"thread_id": "34ec5d84-2760-43e7-b334-843a363a6b7e"}

handler = CredExV20CustomHandler(category="cred_ex_v20_v0_1", columns=[
    "connection_id", "thread_id", "cred_def_id", "parent_thread_id", "verification_method",
    "initiator", "role", "state", "cred_proposal", "cred_offer", "cred_request", "cred_issue",
    "auto_offer", "auto_issue", "auto_remove", "error_msg", "trace", "created_at", "updated_at"
])
handler.insert(cursor, 1, "cred_ex_v20", "827f86b7-6751-4afb-996d-0309b7f6e528", value, tags, None)
conn.commit()
conn.close()