"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from os import getenv
from secrets import randbelow
from typing import List
from uuid import uuid4

from acapy_controller import Controller
from acapy_controller.logging import logging_to_stdout
from acapy_controller.models import V10PresentationExchange
from acapy_controller.protocols import (
    DIDResult,
    IndyCredPrecis,
    didexchange,
    indy_anoncred_credential_artifacts,
    indy_auto_select_credentials_for_presentation_request,
    indy_issue_credential_v2,
    params,
)
from aiohttp import ClientSession

ALICE = getenv("ALICE", "http://alice:3001")
BOB = getenv("BOB", "http://bob:3001")


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=ALICE) as alice, Controller(base_url=BOB) as bob:
        # Connecting
        alice_conn, bob_conn = await didexchange(alice, bob)

        # Issuance prep
        config = (await alice.get("/status/config"))["config"]
        genesis_url = config.get("ledger.genesis_url")
        public_did = (await alice.get("/wallet/did/public", response=DIDResult)).result
        if not public_did:
            public_did = (
                await alice.post(
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

            await alice.post("/wallet/did/public", params=params(did=public_did.did))
        schema, cred_def = await indy_anoncred_credential_artifacts(
            alice,
            ["firstname", "lastname"],
            support_revocation=True,
        )
        schema, cred_def_age = await indy_anoncred_credential_artifacts(
            alice,
            ["age"],
            support_revocation=True,
        )

        # Issue a credential
        await indy_issue_credential_v2(
            alice,
            bob,
            alice_conn.connection_id,
            bob_conn.connection_id,
            cred_def.credential_definition_id,
            {"firstname": "Bob", "lastname": "Builder"},
        )
        await indy_issue_credential_v2(
            alice,
            bob,
            alice_conn.connection_id,
            bob_conn.connection_id,
            cred_def_age.credential_definition_id,
            {"age": "42"},
        )

        # Present the thing
        self_uuid = str(uuid4())
        alice_pres_ex = await alice.post(
            "/present-proof/send-request",
            json={
                "auto_verify": False,
                "comment": "Presentation request from minimal",
                "connection_id": alice_conn.connection_id,
                "proof_request": {
                    "name": "proof",
                    "version": "0.1.0",
                    "nonce": str(randbelow(10**10)),
                    "requested_attributes": {
                        str(uuid4()): {
                            "name": "firstname",
                            "restrictions": [
                                {"cred_def_id": cred_def.credential_definition_id}
                            ],
                        },
                        str(uuid4()): {
                            "name": "age",
                            "restrictions": [
                                {"cred_def_id": cred_def_age.credential_definition_id}
                            ],
                        },
                        self_uuid: {"name": "self-attested"},
                    },
                    "requested_predicates": {},
                    "non_revoked": None,
                },
                "trace": False,
            },
            response=V10PresentationExchange,
        )
        alice_pres_ex_id = alice_pres_ex.presentation_exchange_id

        bob_pres_ex = await bob.record_with_values(
            topic="present_proof",
            record_type=V10PresentationExchange,
            connection_id=bob_conn.connection_id,
            state="request_received",
        )
        assert bob_pres_ex.presentation_request
        bob_pres_ex_id = bob_pres_ex.presentation_exchange_id

        relevant_creds = await bob.get(
            f"/present-proof/records/{bob_pres_ex_id}/credentials",
            response=List[IndyCredPrecis],
        )
        pres_spec = indy_auto_select_credentials_for_presentation_request(
            bob_pres_ex.presentation_request.serialize(), relevant_creds
        )
        pres_spec.self_attested_attributes = {self_uuid: "self-attested data goes here"}
        bob_pres_ex = await bob.post(
            f"/present-proof/records/{bob_pres_ex_id}/send-presentation",
            json=pres_spec,
            response=V10PresentationExchange,
        )

        await alice.record_with_values(
            topic="present_proof",
            record_type=V10PresentationExchange,
            presentation_exchange_id=alice_pres_ex_id,
            state="presentation_received",
        )
        alice_pres_ex = await alice.post(
            f"/present-proof/records/{alice_pres_ex_id}/verify-presentation",
            json={},
            response=V10PresentationExchange,
        )
        alice_pres_ex = await alice.record_with_values(
            topic="present_proof",
            record_type=V10PresentationExchange,
            presentation_exchange_id=alice_pres_ex_id,
            state="verified",
        )

        bob_pres_ex = await bob.record_with_values(
            topic="present_proof",
            record_type=V10PresentationExchange,
            presentation_exchange_id=bob_pres_ex_id,
            state="presentation_acked",
        )


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
