"""Example of issuing multiple credentials with anoncreds in a clustered environment."""

import asyncio
from os import getenv
from secrets import token_hex

import aiohttp
from acapy_controller import Controller
from acapy_controller.logging import logging_to_stdout
from acapy_controller.protocols import (
    DIDResult,
    InvitationRecord,
    OobRecord,
    params,
)
from aiohttp import ClientSession
from examples.util import (
    CredDefResultAnonCreds,
    SchemaResultAnonCreds,
    V20CredExRecord,
)

CREDENTIALS_BASE_PATH = "/issue-credential-2.0"
REVOCATION_BASE_PATH = "/anoncreds"

FABER = getenv("FABER", "http://nginx")
ALICE = getenv("ALICE", "http://alice:6001")


async def check_unique_cred_rev_ids(
    agent: Controller, credential_exchange_ids: list[str]
) -> None:
    """Check that all credential revocation IDs are unique."""
    seen = []

    for cred_ex_id in credential_exchange_ids:
        result = (
            await agent.get(
                f"{REVOCATION_BASE_PATH}/revocation/credential-record?cred_ex_id={cred_ex_id}"
            )
        )["result"]

        cred_rev_id = int(result["cred_rev_id"])
        if cred_rev_id not in seen:
            seen.append(cred_rev_id)
        else:
            raise AssertionError(
                f"Duplicate cred_rev_id found: {cred_rev_id} for credential {cred_ex_id}"
            )

    print(f"Unique cred_rev_ids found: {len(seen)}")
    seen.sort()
    print(f"Credential revocation IDs: {seen}")


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=ALICE) as alice, Controller(base_url=FABER) as faber:
        # Connecting

        invite_record = await faber.post(
            "/out-of-band/create-invitation",
            json={
                "handshake_protocols": ["https://didcomm.org/didexchange/1.1"],
            },
            params=params(
                auto_accept=True,
            ),
            response=InvitationRecord,
        )

        await alice.post(
            "/out-of-band/receive-invitation",
            json=invite_record.invitation,
            response=OobRecord,
        )

        await asyncio.sleep(1)  # Wait for the invitation to be processed

        alice_conn = (await faber.get("connections"))["results"][0]

        # Issuance prep
        config = (await alice.get("/status/config"))["config"]
        genesis_url = config.get("ledger.genesis_url")
        public_did = (await alice.get("/wallet/did/public", response=DIDResult)).result
        if not public_did:
            public_did = (
                await faber.post(
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

            await faber.post("/wallet/did/public", params=params(did=public_did.did))
        schema_name = "anoncreds-test-" + token_hex(8)
        schema_version = "1.0"
        schema = await faber.post(
            "/anoncreds/schema",
            json={
                "schema": {
                    "name": schema_name,
                    "version": schema_version,
                    "attrNames": ["middlename"],
                    "issuerId": public_did.did,
                }
            },
            response=SchemaResultAnonCreds,
        )
        cred_def = await faber.post(
            "/anoncreds/credential-definition",
            json={
                "credential_definition": {
                    "issuerId": schema.schema_state["schema"]["issuerId"],
                    "schemaId": schema.schema_state["schema_id"],
                    "tag": token_hex(8),
                },
                "options": {"support_revocation": True, "revocation_registry_size": 100},
            },
            response=CredDefResultAnonCreds,
        )

        num_creds = 10  # Number of credentials to issue concurrently

        # Create and send credential offers concurrently
        faber_cred_ex_ids = []
        for i in range(num_creds):
            issuer_cred_ex = await faber.post(
                "/issue-credential-2.0/send-offer",
                json={
                    "auto_issue": True,
                    "auto_remove": False,
                    "comment": "Credential from minimal example",
                    "trace": False,
                    "connection_id": alice_conn["connection_id"],
                    "filter": {
                        "anoncreds": {
                            "cred_def_id": cred_def.credential_definition_state[
                                "credential_definition_id"
                            ],
                            "schema_name": schema_name,
                            "schema_version": schema_version,
                        }
                    },
                    "credential_preview": {
                        "type": "issue-credential-2.0/2.0/credential-preview",  # pyright: ignore
                        "attributes": [
                            {
                                "name": "middlename",
                                "value": f"MiddleName-{i + 1}",
                            }
                        ],
                    },
                },
                response=V20CredExRecord,
            )
            faber_cred_ex_ids.append(issuer_cred_ex.cred_ex_id)

        # Wait for all credentials to be received by Alice
        num_tries = 0
        credentials_returned = {"results": []}
        while (
            len(credentials_returned["results"]) != num_creds and num_tries < 20
        ):  # Increased timeout for many creds
            await asyncio.sleep(0.5)
            credentials_returned = await alice.get(f"{CREDENTIALS_BASE_PATH}/records")
            num_tries += 1

        print(f"Number of credentials returned: {len(credentials_returned['results'])}")

        assert len(credentials_returned["results"]) == num_creds, (
            f"Expected {num_creds} credentials to be issued; only got {credentials_returned}"
        )

        # Accept all credentials concurrently using asyncio.gather()
        request_tasks = []
        for cred in credentials_returned["results"]:
            task = alice.post(
                f"{CREDENTIALS_BASE_PATH}/records/{cred['cred_ex_record']['cred_ex_id']}/send-request",
                json={},
            )
            request_tasks.append(task)

        # Execute all credential requests concurrently
        await asyncio.gather(*request_tasks)

        # Wait for all credentials to be completed.
        # This could be done more efficiently with a webhook listener, but
        # is challenging with the current Controller library and multiple instances.
        await asyncio.sleep(3)
        async with aiohttp.ClientSession() as session:
            seen = []

            active_rev_reg = (
                await (
                    await session.get(
                        f"http://nginx/anoncreds/revocation/active-registry/{cred_def.credential_definition_state['credential_definition_id']}"
                    )
                ).json()
            )["result"]["revoc_reg_id"]

            results = await session.get(
                f"http://nginx/anoncreds/revocation/registry/{active_rev_reg}/issued/details"
            )

            for entry in await results.json():
                if entry["cred_rev_id"] not in seen:
                    seen.append(entry["cred_rev_id"])
                else:
                    raise AssertionError(
                        f"Duplicate cred_rev_id found: {entry['cred_rev_id']}"
                    )

            print(f"Credential revocation IDs created: {seen}")


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
