"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from os import getenv

from acapy_controller import Controller
from acapy_controller.logging import logging_to_stdout
from acapy_controller.models import CreateWalletResponse
from acapy_controller.protocols import (
    DIDResult,
    didexchange,
    indy_anoncred_credential_artifacts,
    indy_issue_credential_v2,
    params,
)
from aiohttp import ClientSession
from examples.util import indy_present_proof_v2

AGENCY = getenv("AGENCY", "http://agency:3001")


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=AGENCY) as agency:
        alice = await agency.post(
            "/multitenancy/wallet",
            json={
                "label": "Alice",
                "wallet_type": "askar",
            },
            response=CreateWalletResponse,
        )
        bob = await agency.post(
            "/multitenancy/wallet",
            json={
                "label": "Bob",
                "wallet_type": "askar",
            },
            response=CreateWalletResponse,
        )

    async with (
        Controller(
            base_url=AGENCY, wallet_id=alice.wallet_id, subwallet_token=alice.token
        ) as alice,
        Controller(
            base_url=AGENCY, wallet_id=bob.wallet_id, subwallet_token=bob.token
        ) as bob,
    ):
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
        _, cred_def = await indy_anoncred_credential_artifacts(
            alice,
            ["firstname", "lastname"],
            support_revocation=True,
        )

        # Connecting
        alice_conn, bob_conn = await didexchange(alice, bob)

        # Issue a credential
        await indy_issue_credential_v2(
            alice,
            bob,
            alice_conn.connection_id,
            bob_conn.connection_id,
            cred_def.credential_definition_id,
            {"firstname": "Bob", "lastname": "Builder"},
        )

        # Present the credential's attributes
        await indy_present_proof_v2(
            bob,
            alice,
            bob_conn.connection_id,
            alice_conn.connection_id,
            requested_attributes=[{"name": "firstname"}],
        )


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
