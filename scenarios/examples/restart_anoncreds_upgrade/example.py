"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
import json
from os import getenv

from acapy_controller import Controller
from acapy_controller.logging import logging_to_stdout
from acapy_controller.protocols import (
    didexchange,
    indy_anoncred_credential_artifacts,
    indy_anoncred_onboard,
)
from examples.util import (
    Settings,
    anoncreds_issue_credential_v2,
    anoncreds_present_proof_v2,
    get_wallet_name,
    update_wallet_type,
    wait_until_healthy,
)

import docker

ALICE = getenv("ALICE", "http://alice:3001")
BOB_ASKAR = getenv("BOB_ASKAR", "http://bob-askar:3001")
BOB_ANONCREDS = getenv("BOB_ANONCREDS", "http://bob-anoncreds:3001")
BOB_ASKAR_ANON = getenv("BOB_ASKAR_ANON", "http://bob-askar-anon:3001")


async def connect_agents_and_issue_credentials(
    inviter: Controller,
    invitee: Controller,
    inviter_cred_def,
    fname: str,
    lname: str,
    inviter_conn=None,
    invitee_conn=None,
):
    is_inviter_anoncreds = (await inviter.get("/settings", response=Settings)).get(
        "wallet.type"
    ) == "askar-anoncreds"

    # connect the 2 agents
    if (not inviter_conn) or (not invitee_conn):
        print(">>> connecting agents ...")
        (inviter_conn, invitee_conn) = await didexchange(inviter, invitee)

    # Issue a credential
    print(">>> issue credential ...")
    inviter_cred_ex, _ = await anoncreds_issue_credential_v2(
        inviter,
        invitee,
        inviter_conn.connection_id,
        invitee_conn.connection_id,
        {"firstname": fname, "lastname": lname},
        inviter_cred_def.credential_definition_id,
    )

    # Present the the credential's attributes
    print(">>> present proof ...")
    await anoncreds_present_proof_v2(
        invitee,
        inviter,
        invitee_conn.connection_id,
        inviter_conn.connection_id,
        requested_attributes=[{"name": "firstname"}],
    )

    # Revoke credential
    if is_inviter_anoncreds:
        await inviter.post(
            url="/anoncreds/revocation/revoke",  # TODO need to check agent type (askar vs anoncreds)
            json={
                "connection_id": inviter_conn.connection_id,
                "rev_reg_id": inviter_cred_ex.details.rev_reg_id,
                "cred_rev_id": inviter_cred_ex.details.cred_rev_id,
                "publish": True,
                "notify": True,
                "notify_version": "v1_0",
            },
        )
        await invitee.record(topic="revocation-notification")
    else:
        await inviter.post(
            url="/revocation/revoke",  # TODO need to check agent type (askar vs anoncreds)
            json={
                "connection_id": inviter_conn.connection_id,
                "rev_reg_id": inviter_cred_ex.details.rev_reg_id,
                "cred_rev_id": inviter_cred_ex.details.cred_rev_id,
                "publish": True,
                "notify": True,
                "notify_version": "v1_0",
            },
        )
        await invitee.record(topic="revocation-notification")

    # Issue a second credential
    print(">>> issue credential ...")
    inviter_cred_ex, _ = await anoncreds_issue_credential_v2(
        inviter,
        invitee,
        inviter_conn.connection_id,
        invitee_conn.connection_id,
        {"firstname": f"{fname}2", "lastname": f"{lname}2"},
        inviter_cred_def.credential_definition_id,
    )
    print(">>> Done!")

    return (inviter_conn, invitee_conn)


async def verify_schema_cred_def(issuer, schema_count, cred_def_count):
    is_issuer_anoncreds = (await issuer.get("/settings", response=Settings)).get(
        "wallet.type"
    ) == "askar-anoncreds"

    if is_issuer_anoncreds:
        schemas = await issuer.get("/anoncreds/schemas")
        assert schema_count == len(schemas["schema_ids"])

        cred_defs = await issuer.get("/anoncreds/credential-definitions")
        assert cred_def_count == len(cred_defs["credential_definition_ids"])
    else:
        schemas = await issuer.get("/schemas/created")
        assert schema_count == len(schemas["schema_ids"])

        cred_defs = await issuer.get("/credential-definitions/created")
        assert cred_def_count == len(cred_defs["credential_definition_ids"])


async def verify_issued_credentials(issuer, issued_cred_count, revoked_cred_count):
    is_issuer_anoncreds = (await issuer.get("/settings", response=Settings)).get(
        "wallet.type"
    ) == "askar-anoncreds"

    cred_exch_recs = await issuer.get("/issue-credential-2.0/records")
    cred_exch_recs = cred_exch_recs["results"]
    assert len(cred_exch_recs) == issued_cred_count
    registries = {}
    active_creds = 0
    revoked_creds = 0
    for cred_exch in cred_exch_recs:
        cred_type = (
            "indy"
            if "indy" in cred_exch
            and cred_exch["indy"]
            and "rev_reg_id" in cred_exch["indy"]
            else "anoncreds"
        )
        rev_reg_id = cred_exch[cred_type]["rev_reg_id"]
        cred_rev_id = cred_exch[cred_type]["cred_rev_id"]
        cred_rev_id = int(cred_rev_id)
        if rev_reg_id not in registries:
            if is_issuer_anoncreds:
                registries[rev_reg_id] = await issuer.get(
                    f"/anoncreds/revocation/registry/{rev_reg_id}/issued/indy_recs",
                )
            else:
                registries[rev_reg_id] = await issuer.get(
                    f"/revocation/registry/{rev_reg_id}/issued/indy_recs",
                )
        registry = registries[rev_reg_id]
        if cred_rev_id in registry["rev_reg_delta"]["value"]["revoked"]:
            revoked_creds = revoked_creds + 1
        else:
            active_creds = active_creds + 1
    assert revoked_creds == revoked_cred_count
    assert (revoked_creds + active_creds) == issued_cred_count


async def verify_recd_credentials(holder, active_cred_count, revoked_cred_count):
    is_holder_anoncreds = (await holder.get("/settings", response=Settings)).get(
        "wallet.type"
    ) == "askar-anoncreds"

    credentials = await holder.get("/credentials")
    credentials = credentials["results"]
    assert len(credentials) == (active_cred_count + revoked_cred_count)
    registries = {}
    active_creds = 0
    revoked_creds = 0
    for credential in credentials:
        rev_reg_id = credential["rev_reg_id"]
        cred_rev_id = int(credential["cred_rev_id"])
        if rev_reg_id not in registries:
            if is_holder_anoncreds:
                registries[rev_reg_id] = await holder.get(
                    f"/anoncreds/revocation/registry/{rev_reg_id}/issued/indy_recs",
                )
            else:
                registries[rev_reg_id] = await holder.get(
                    f"/revocation/registry/{rev_reg_id}/issued/indy_recs",
                )
        registry = registries[rev_reg_id]
        if cred_rev_id in registry["rev_reg_delta"]["value"]["revoked"]:
            revoked_creds = revoked_creds + 1
        else:
            active_creds = active_creds + 1
    assert revoked_creds == revoked_cred_count
    assert active_creds == active_cred_count


async def verify_recd_presentations(verifier, recd_pres_count):
    presentations = await verifier.get("/present-proof-2.0/records")
    presentations = presentations["results"]

    assert recd_pres_count == len(presentations)


async def upgrade_wallet_and_shutdown_container(
    client,
    agent_controller,
    agent_container,
):
    agent_command = agent_container.attrs["Config"]["Cmd"]

    # command is a List, find the wallet type and replace "askar" with "askar-anoncreds"
    correct_wallet_type = update_wallet_type(agent_command, "askar-anoncreds")
    wallet_name = get_wallet_name(agent_command)

    # call the wallet upgrade endpoint to upgrade to askar-anoncreds
    await agent_controller.post(
        "/anoncreds/wallet/upgrade",
        params={
            "wallet_name": wallet_name,
        },
    )

    # Wait for the upgrade ...
    await asyncio.sleep(2)

    print(">>> waiting for container to exit ...")
    agent_id = agent_container.attrs["Id"]
    wait_until_healthy(client, agent_id, is_healthy=False)
    agent_container.remove()

    return agent_command


def start_new_container(
    client,
    agent_command,
    agent_container,
    agent_label,
):
    print(">>> start new container ...")
    new_agent_container = client.containers.run(
        "acapy-test",
        command=agent_command,
        detach=True,
        environment={"RUST_LOG": "aries-askar::log::target=error"},
        healthcheck=agent_container.attrs["Config"]["Healthcheck"],
        name=agent_label,
        network=agent_container.attrs["HostConfig"]["NetworkMode"],
        ports=agent_container.attrs["NetworkSettings"]["Ports"],
    )
    print(">>> new container:", agent_label, json.dumps(new_agent_container.attrs))
    new_agent_id = new_agent_container.attrs["Id"]

    wait_until_healthy(client, new_agent_id)
    print(">>> new container is healthy")

    return (new_agent_container, new_agent_id)


def stop_and_remove_container(client, agent_id):
    # cleanup - shut down agent (not part of docker compose)
    print(">>> shut down agent ...")
    agent_container = client.containers.get(agent_id)
    agent_container.stop()
    wait_until_healthy(client, agent_id, is_healthy=False)
    agent_container.remove()


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=ALICE) as alice:
        # setup alice as an issuer
        print(">>> setting up alice as issuer ...")
        await indy_anoncred_onboard(alice)
        schema, cred_def = await indy_anoncred_credential_artifacts(
            alice,
            ["firstname", "lastname"],
            support_revocation=True,
            revocation_registry_size=5,
        )

        # confirm alice has 1 schema and 1 cred def
        await verify_schema_cred_def(alice, 1, 1)

    alice_conns = {}
    bob_conns = {}
    async with (
        Controller(base_url=ALICE) as alice,
        Controller(base_url=BOB_ASKAR) as bob,
    ):
        # connect to Bob (Askar wallet) and issue (and revoke) some credentials
        (alice_conn, bob_conn) = await connect_agents_and_issue_credentials(
            alice,
            bob,
            cred_def,
            "Bob",
            "Askar",
        )
        alice_conns["askar"] = alice_conn
        bob_conns["askar"] = bob_conn
        await verify_recd_credentials(bob, 1, 1)

    async with (
        Controller(base_url=ALICE) as alice,
        Controller(base_url=BOB_ANONCREDS) as bob,
    ):
        # connect to Bob (Anoncreds wallet) and issue (and revoke) some credentials
        (alice_conn, bob_conn) = await connect_agents_and_issue_credentials(
            alice,
            bob,
            cred_def,
            "Bob",
            "Anoncreds",
        )
        alice_conns["anoncreds"] = alice_conn
        bob_conns["anoncreds"] = bob_conn
        await verify_recd_credentials(bob, 1, 1)

    async with (
        Controller(base_url=ALICE) as alice,
        Controller(base_url=BOB_ASKAR_ANON) as bob,
    ):
        # connect to Bob (Askar wallet which will be upgraded) and issue (and revoke) some credentials
        (alice_conn, bob_conn) = await connect_agents_and_issue_credentials(
            alice,
            bob,
            cred_def,
            "Bob",
            "Askar_Anon",
        )
        alice_conns["askar-anon"] = alice_conn
        bob_conns["askar-anon"] = bob_conn
        await verify_recd_credentials(bob, 1, 1)
        await verify_issued_credentials(alice, 6, 3)
        await verify_recd_presentations(alice, 3)

    # at this point alice has issued 6 credentials (revocation registry size is 5) and revoked 3
    # TODO verify counts of credentials, revocations etc for each agent

    # play with docker - get a list of all our running containers
    client = docker.from_env()
    containers = client.containers.list(all=True)
    docker_containers = {}
    for container in containers:
        if "com.docker.compose.service" in container.attrs["Config"]["Labels"]:
            container_name = container.attrs["Config"]["Labels"][
                "com.docker.compose.service"
            ]
            container_id = container.attrs["Id"]
            container_is_running = container.attrs["State"]["Running"]
            docker_containers[container_name] = {
                "Id": container_id,
                "Running": container_is_running,
            }
            print(">>> container:", container_name, docker_containers[container_name])

    alice_docker_container = docker_containers["alice"]
    alice_container = client.containers.get(alice_docker_container["Id"])
    async with Controller(base_url=ALICE) as alice:
        alice_command = await upgrade_wallet_and_shutdown_container(
            client,
            alice,
            alice_container,
        )

    bob_docker_container = docker_containers["bob-askar-anon"]
    bob_container = client.containers.get(bob_docker_container["Id"])
    async with Controller(base_url=BOB_ASKAR_ANON) as bob:
        bob_command = await upgrade_wallet_and_shutdown_container(
            client,
            bob,
            bob_container,
        )

    new_alice_container = None
    alice_id = None
    new_bob_container = None
    bob_id = None
    try:
        (new_alice_container, alice_id) = start_new_container(
            client,
            alice_command,
            alice_container,
            "alice",
        )

        (new_bob_container, bob_id) = start_new_container(
            client,
            bob_command,
            bob_container,
            "bob-askar-anon",
        )

        # TODO verify counts of credentials, revocations etc for each upgraded agent
        async with (
            Controller(base_url=ALICE) as alice,
            Controller(base_url=BOB_ASKAR_ANON) as bob,
        ):
            await verify_schema_cred_def(alice, 1, 1)

        # run some more tests ...  alice should still be connected to bob for example ...
        async with (
            Controller(base_url=ALICE) as alice,
            Controller(base_url=BOB_ANONCREDS) as bob,
        ):
            # Present the the credential's attributes
            print(">>> present proof ... again ...")
            await anoncreds_present_proof_v2(
                bob,
                alice,
                bob_conns["anoncreds"].connection_id,
                alice_conns["anoncreds"].connection_id,
                requested_attributes=[{"name": "firstname"}],
            )
            await connect_agents_and_issue_credentials(
                alice,
                bob,
                cred_def,
                "Bob",
                "Anoncreds",
                inviter_conn=alice_conns["anoncreds"],
                invitee_conn=bob_conns["anoncreds"],
            )
            await verify_recd_credentials(bob, 2, 2)
            print(">>> Done! (again)")

        async with (
            Controller(base_url=ALICE) as alice,
            Controller(base_url=BOB_ASKAR_ANON) as bob,
        ):
            # Present the the credential's attributes
            print(">>> present proof ... again ...")
            await anoncreds_present_proof_v2(
                bob,
                alice,
                bob_conns["askar-anon"].connection_id,
                alice_conns["askar-anon"].connection_id,
                requested_attributes=[{"name": "firstname"}],
            )
            await connect_agents_and_issue_credentials(
                alice,
                bob,
                cred_def,
                "Bob",
                "Askar_Anon",
                inviter_conn=alice_conns["askar-anon"],
                invitee_conn=bob_conns["askar-anon"],
            )
            await verify_recd_credentials(bob, 2, 2)
            print(">>> Done! (again)")

        async with (
            Controller(base_url=ALICE) as alice,
            Controller(base_url=BOB_ASKAR) as bob,
        ):
            # Present the the credential's attributes
            print(">>> present proof ... again ...")
            await anoncreds_present_proof_v2(
                bob,
                alice,
                bob_conns["askar"].connection_id,
                alice_conns["askar"].connection_id,
                requested_attributes=[{"name": "firstname"}],
            )
            await connect_agents_and_issue_credentials(
                alice,
                bob,
                cred_def,
                "Bob",
                "Askar",
                inviter_conn=alice_conns["askar"],
                invitee_conn=bob_conns["askar"],
            )
            await verify_recd_credentials(bob, 2, 2)
            await verify_issued_credentials(alice, 12, 6)
            await verify_recd_presentations(alice, 9)
            print(">>> Done! (again)")

    finally:
        if alice_id and new_alice_container:
            # cleanup - shut down alice agent (not part of docker compose)
            stop_and_remove_container(client, alice_id)
        if bob_id and new_bob_container:
            # cleanup - shut down bob agent (not part of docker compose)
            stop_and_remove_container(client, bob_id)


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
