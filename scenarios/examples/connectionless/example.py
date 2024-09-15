"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from dataclasses import dataclass
from os import getenv

from acapy_controller import Controller
from acapy_controller.controller import Minimal
from acapy_controller.logging import logging_to_stdout
from acapy_controller.protocols import (
    DIDResult,
    InvitationRecord,
    V20CredExRecordDetail,
    V20CredExRecordIndy,
    indy_anoncred_credential_artifacts,
    params,
)
from aiohttp import ClientSession

ALICE = getenv("ALICE", "http://alice:3001")
BOB = getenv("BOB", "http://bob:3001")


@dataclass
class ConnectionlessV20CredExRecord(Minimal):
    """Minimal record for connectionless v2 cred ex record."""

    cred_ex_id: str


async def icv2():
    """Test Controller protocols."""
    async with Controller(base_url=ALICE) as alice, Controller(base_url=BOB) as bob:
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
                print(genesis_url)
                async with session.post(
                    genesis_url.replace("/genesis", "/register"),
                    json={
                        "did": public_did.did,
                        "verkey": public_did.verkey,
                        "alias": None,
                        "role": "ENDORSER",
                    },
                ) as resp:
                    assert resp.ok

            await alice.post("/wallet/did/public", params=params(did=public_did.did))

        _, cred_def = await indy_anoncred_credential_artifacts(
            alice, ["firstname", "lastname"]
        )

        attributes = {"firstname": "Bob", "lastname": "Builder"}
        offer = await alice.post(
            "/issue-credential-2.0/create-offer",
            json={
                "auto_issue": False,
                "auto_remove": False,
                "comment": "Credential from minimal example",
                "trace": False,
                "filter": {"indy": {"cred_def_id": cred_def.credential_definition_id}},
                "credential_preview": {
                    "type": "issue-credential-2.0/2.0/credential-preview",  # pyright: ignore
                    "attributes": [
                        {
                            "mime_type": None,
                            "name": name,
                            "value": value,
                        }
                        for name, value in attributes.items()
                    ],
                },
            },
            response=ConnectionlessV20CredExRecord,
        )
        invite = await alice.post(
            "/out-of-band/create-invitation",
            json={"attachments": [{"id": offer.cred_ex_id, "type": "credential-offer"}]},
            response=InvitationRecord,
        )
        bob.event_queue.flush()
        await bob.post("/out-of-band/receive-invitation", json=invite.invitation)
        bob_cred_ex = await bob.event_with_values(
            topic="issue_credential_v2_0",
            state="offer-received",
            event_type=ConnectionlessV20CredExRecord,
        )
        bob_cred_ex_id = bob_cred_ex.cred_ex_id

        alice.event_queue.flush()
        bob_cred_ex = await bob.post(
            f"/issue-credential-2.0/records/{bob_cred_ex_id}/send-request",
            response=ConnectionlessV20CredExRecord,
        )

        alice_cred_ex = await alice.event_with_values(
            topic="issue_credential_v2_0",
            state="request-received",
            event_type=ConnectionlessV20CredExRecord,
        )
        alice_cred_ex_id = alice_cred_ex.cred_ex_id

        alice_cred_ex = await alice.post(
            f"/issue-credential-2.0/records/{alice_cred_ex_id}/issue",
            json={},
            response=V20CredExRecordDetail,
        )

        await bob.event_with_values(
            topic="issue_credential_v2_0",
            cred_ex_id=bob_cred_ex_id,
            state="credential-received",
        )

        bob_cred_ex = await bob.post(
            f"/issue-credential-2.0/records/{bob_cred_ex_id}/store",
            json={},
            response=V20CredExRecordDetail,
        )
        alice_cred_ex = await alice.event_with_values(
            topic="issue_credential_v2_0",
            event_type=ConnectionlessV20CredExRecord,
            cred_ex_id=alice_cred_ex_id,
            state="done",
        )
        await alice.event_with_values(
            topic="issue_credential_v2_0_indy",
            event_type=V20CredExRecordIndy,
        )

        bob_cred_ex = await bob.event_with_values(
            topic="issue_credential_v2_0",
            event_type=ConnectionlessV20CredExRecord,
            cred_ex_id=bob_cred_ex_id,
            state="done",
        )
        await bob.event_with_values(
            topic="issue_credential_v2_0_indy",
            event_type=V20CredExRecordIndy,
        )


@dataclass
class ConnectionlessV10CredExRecord(Minimal):
    """Minimal record for v1 cred ex record."""

    credential_exchange_id: str


async def icv1():
    """Issue credential v1."""
    async with Controller(base_url=ALICE) as alice, Controller(base_url=BOB) as bob:
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
                    if resp.ok:
                        return await resp.json()

            await alice.post("/wallet/did/public", params=params(did=public_did.did))

        _, cred_def = await indy_anoncred_credential_artifacts(
            alice, ["firstname", "lastname"]
        )

        attributes = {"firstname": "Bob", "lastname": "Builder"}
        offer = await alice.post(
            "/issue-credential/create-offer",
            json={
                "auto_issue": False,
                "auto_remove": False,
                "comment": "Credential from minimal example",
                "trace": False,
                "cred_def_id": cred_def.credential_definition_id,
                "credential_preview": {
                    "@type": "issue-credential/1.0/credential-preview",
                    "attributes": [
                        {
                            "mime_type": None,
                            "name": name,
                            "value": value,
                        }
                        for name, value in attributes.items()
                    ],
                },
            },
            response=ConnectionlessV10CredExRecord,
        )
        invite = await alice.post(
            "/out-of-band/create-invitation",
            json={
                "attachments": [
                    {"id": offer.credential_exchange_id, "type": "credential-offer"}
                ]
            },
            response=InvitationRecord,
        )
        bob.event_queue.flush()
        await bob.post("/out-of-band/receive-invitation", json=invite.invitation)
        bob_cred_ex = await bob.event_with_values(
            topic="issue_credential",
            state="offer_received",
            event_type=ConnectionlessV10CredExRecord,
        )
        bob_cred_ex_id = bob_cred_ex.credential_exchange_id

        alice.event_queue.flush()
        bob_cred_ex = await bob.post(
            f"/issue-credential/records/{bob_cred_ex_id}/send-request",
            response=ConnectionlessV10CredExRecord,
        )

        alice_cred_ex = await alice.event_with_values(
            topic="issue_credential",
            state="request_received",
            event_type=ConnectionlessV10CredExRecord,
        )
        alice_cred_ex_id = alice_cred_ex.credential_exchange_id

        alice_cred_ex = await alice.post(
            f"/issue-credential/records/{alice_cred_ex_id}/issue",
            json={},
            response=ConnectionlessV10CredExRecord,
        )

        await bob.event_with_values(
            topic="issue_credential",
            credential_exchange_id=bob_cred_ex_id,
            state="credential_received",
        )

        bob_cred_ex = await bob.post(
            f"/issue-credential/records/{bob_cred_ex_id}/store",
            json={},
            response=ConnectionlessV10CredExRecord,
        )
        alice_cred_ex = await alice.event_with_values(
            topic="issue_credential",
            event_type=ConnectionlessV10CredExRecord,
            credential_exchange_id=alice_cred_ex_id,
            state="credential_acked",
        )

        bob_cred_ex = await bob.event_with_values(
            topic="issue_credential",
            event_type=ConnectionlessV10CredExRecord,
            credential_exchange_id=bob_cred_ex_id,
            state="credential_acked",
        )


async def main():
    """Run."""
    await icv1()
    await icv2()


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
