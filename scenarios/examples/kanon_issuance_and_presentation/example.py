"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
import json
from datetime import datetime
from os import getenv
from secrets import token_hex

from acapy_controller import Controller
from acapy_controller.logging import logging_to_stdout
from acapy_controller.models import V20PresExRecord
from acapy_controller.protocols import (
    DIDResult,
    didexchange,
    params,
)
from aiohttp import ClientSession
from examples.util import (
    CredDefResultAnonCreds,
    SchemaResultAnonCreds,
    _presentation_request_payload,
    anoncreds_issue_credential_v2,
    anoncreds_present_proof_v2,
)

KANON_POSTGRES = getenv("KANON_POSTGRES", "http://kanon-postgres:3001")
BOB = getenv("BOB", "http://bob:3001")


def summary(presentation: V20PresExRecord) -> str:
    """Summarize a presentation exchange record."""
    request = _presentation_request_payload(presentation)
    return "Summary: " + json.dumps(
        {
            "state": presentation.state,
            "verified": presentation.verified,
            "presentation_request": request,
        },
        indent=2,
        sort_keys=True,
    )


async def main():
    """Test Controller protocols."""
    async with (
        Controller(base_url=KANON_POSTGRES) as kanon_postgres,
        Controller(base_url=BOB) as bob,
    ):
        # Anoncreds issuance and presentation with revocation
        # Connecting
        kanon_postgres_conn, bob_conn = await didexchange(kanon_postgres, bob)

        # Issuance prep
        config = (await kanon_postgres.get("/status/config"))["config"]
        genesis_url = config.get("ledger.genesis_url")
        public_did = (
            await kanon_postgres.get("/wallet/did/public", response=DIDResult)
        ).result
        if not public_did:
            public_did = (
                await kanon_postgres.post(
                    "/wallet/did/create",
                    json={"method": "sov", "options": {"key_type": "ed25519"}},
                    response=DIDResult,
                )
            ).result
            assert public_did

            async with ClientSession() as session:
                register_url = genesis_url.replace("/genesis", "/register")
                async with session.post(
                    register_url,
                    json={
                        "did": public_did.did,
                        "verkey": public_did.verkey,
                        "alias": None,
                        "role": "ENDORSER",
                    },
                ) as resp:
                    assert resp.ok

            await kanon_postgres.post(
                "/wallet/did/public", params=params(did=public_did.did)
            )
        # Create a new schema and cred def with different attributes on new
        # anoncreds endpoints
        schema_name = "anoncreds-test-" + token_hex(8)
        schema_version = "1.0"
        schema = await kanon_postgres.post(
            "/anoncreds/schema",
            json={
                "schema": {
                    "name": schema_name,
                    "version": schema_version,
                    "attrNames": ["firstname", "lastname"],
                    "issuerId": public_did.did,
                }
            },
            response=SchemaResultAnonCreds,
        )
        cred_def = await kanon_postgres.post(
            "/anoncreds/credential-definition",
            json={
                "credential_definition": {
                    "issuerId": schema.schema_state["schema"]["issuerId"],
                    "schemaId": schema.schema_state["schema_id"],
                    "tag": token_hex(8),
                },
                "options": {"support_revocation": True, "revocation_registry_size": 10},
                "wait_for_revocation_setup": True,
            },
            response=CredDefResultAnonCreds,
        )

        # Issue a credential
        kanon_postgres_cred_ex, _ = await anoncreds_issue_credential_v2(
            kanon_postgres,
            bob,
            kanon_postgres_conn.connection_id,
            bob_conn.connection_id,
            {"firstname": "Bob", "lastname": "Builder"},
            cred_def_id=cred_def.credential_definition_state["credential_definition_id"],
            issuer_id=public_did.did,
            schema_id=schema.schema_state["schema_id"],
            schema_issuer_id=public_did.did,
            schema_name=schema_name,
        )

        # Present the credential's attributes
        _, verifier_ex = await anoncreds_present_proof_v2(
            bob,
            kanon_postgres,
            bob_conn.connection_id,
            kanon_postgres_conn.connection_id,
            requested_attributes=[{"name": "firstname"}],
            non_revoked={"to": int(datetime.now().timestamp())},
            cred_rev_id=kanon_postgres_cred_ex.details.cred_rev_id,
        )
        assert verifier_ex.verified == "true"

        # Revoke credential
        await kanon_postgres.post(
            url="/anoncreds/revocation/revoke",
            json={
                "connection_id": kanon_postgres_conn.connection_id,
                "rev_reg_id": kanon_postgres_cred_ex.details.rev_reg_id,
                "cred_rev_id": kanon_postgres_cred_ex.details.cred_rev_id,
                "publish": True,
                "notify": True,
                "notify_version": "v1_0",
            },
        )
        await bob.record(topic="revocation-notification")

        _, verifier_ex = await anoncreds_present_proof_v2(
            bob,
            kanon_postgres,
            bob_conn.connection_id,
            kanon_postgres_conn.connection_id,
            requested_attributes=[{"name": "firstname"}],
            non_revoked={"to": int(datetime.now().timestamp())},
            cred_rev_id=kanon_postgres_cred_ex.details.cred_rev_id,
        )
        assert verifier_ex.verified == "false"


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
