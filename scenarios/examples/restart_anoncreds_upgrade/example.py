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
):
    # connect the 2 agents
    print(">>> connecting agents ...")
    (inviter_conn, invitee_conn) = await didexchange(inviter, invitee)

    # Issue a credential
    print(">>> issue credential ...")
    inviter_cred_ex, _ = await anoncreds_issue_credential_v2(
        inviter,
        invitee,
        inviter_conn.connection_id,
        invitee_conn.connection_id,
        inviter_cred_def.credential_definition_id,
        {"firstname": fname, "lastname": lname},
    )
    print(">>> cred_ex:", inviter_cred_ex)

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
    await inviter.post(
        url="/revocation/revoke",
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
        inviter_cred_def.credential_definition_id,
        {"firstname": "{fname}2", "lastname": "{lname}2"},
    )
    print(">>> Done!")

    return (inviter_conn, invitee_conn)


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

    alice_conns = {}
    bob_conns = {}
    async with Controller(base_url=ALICE) as alice, Controller(base_url=BOB_ASKAR) as bob:
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

    # at this point alice has issued 6 credentials (revocation registry size is 5) and revoked 3

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

        # run some more tests ...  alice should still be connected to bob for example ...
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
            print(">>> Done! (again)")

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
