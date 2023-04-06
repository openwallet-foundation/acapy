import os

from controller.controller import Controller
from controller.protocols import (
    indy_anoncred_onboard,
    didexchange,
    indy_issue_credential_v2,
    indy_present_proof_v2,
)
from controller.logging import logging_to_stdout

ALICE = os.getenv("ALICE", "http://alice:3001")
BOB = os.getenv("BOB", "http://bob:3005")


async def main():
    logging_to_stdout()
    async with Controller(base_url=ALICE) as alice, Controller(base_url=BOB) as bob:
        # DID Setup
        public_did = await indy_anoncred_onboard(alice)

        # Register a Schema using legacy Indy
        response = await alice.post(
            "/anoncreds/schema",
            json={
                "schema": {
                    "attrNames": ["name", "age"],
                    "issuerId": public_did.did,
                    "name": "anoncreds-testing",
                    "version": "0.1",
                },
                "options": {},
            },
        )
        schema_id = response["schema_state"]["schema_id"]
        schema = await alice.get(f"/anoncreds/schema/{schema_id}")
        schemas = await alice.get("/anoncreds/schemas")

        cred_def = await alice.post(
            "/anoncreds/credential-definition",
            json={
                "credential_definition": {
                    "tag": "default",
                    "schemaId": schema_id,
                    "issuerId": public_did.did,
                },
                "options": {
                    "support_revocation": True,
                },
            },
        )
        cred_def_id = cred_def["credential_definition_state"][
            "credential_definition_id"
        ]
        cred_def = await alice.get(f"/anoncreds/credential-definition/{cred_def_id}")
        cred_defs = await alice.get("/anoncreds/credential-definitions")

        alice_conn, bob_conn = await didexchange(alice, bob)
        await indy_issue_credential_v2(
            alice,
            bob,
            alice_conn.connection_id,
            bob_conn.connection_id,
            cred_def_id,
            {"name": "Bob", "age": "42"},
        )
        bob_pres, alice_pres = await indy_present_proof_v2(
            bob,
            alice,
            bob_conn.connection_id,
            alice_conn.connection_id,
            name="proof-1",
            version="0.1",
            comment="testing",
            requested_attributes=[
                {"name": "name", "restrictions": [{"cred_def_id": cred_def_id}]},
                {"name": "age", "restrictions": [{"cred_def_id": cred_def_id}]},
            ],
        )
        print(alice_pres.verified)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
