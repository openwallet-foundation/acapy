"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from os import getenv
import json
import time

import docker
from docker.errors import NotFound
from docker.models.containers import Container

from acapy_controller import Controller
from acapy_controller.logging import logging_to_stdout
from acapy_controller.protocols import (
    connection,
    didexchange,
    indy_anoncred_credential_artifacts,
    indy_anoncred_onboard,
    indy_anoncreds_publish_revocation,
    indy_anoncreds_revoke,
    indy_issue_credential_v2,
    indy_present_proof_v2,
)

from examples.util import (
    healthy,
    unhealthy,
    wait_until_healthy,
)


ALICE = getenv("ALICE", "http://alice:3001")
BOB = getenv("BOB", "http://bob:3001")


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=ALICE) as alice, Controller(base_url=BOB) as bob:
        # connect the 2 agents
        print(">>> connecting agents ...")
        (alice_conn, bob_conn) = await didexchange(alice, bob)

        # setup alice as an issuer
        print(">>> setting up alice as issuer ...")
        await indy_anoncred_onboard(alice)
        schema, cred_def = await indy_anoncred_credential_artifacts(
            alice,
            ["firstname", "lastname"],
            support_revocation=True,
        )

        # Issue a credential
        print(">>> issue credential ...")
        alice_cred_ex, _ = await indy_issue_credential_v2(
            alice,
            bob,
            alice_conn.connection_id,
            bob_conn.connection_id,
            cred_def.credential_definition_id,
            {"firstname": "Bob", "lastname": "Builder"},
        )

        # Present the the credential's attributes
        print(">>> present proof ...")
        await indy_present_proof_v2(
            bob,
            alice,
            bob_conn.connection_id,
            alice_conn.connection_id,
            requested_attributes=[{"name": "firstname"}],
        )
        print(">>> Done!")

    # play with docker
    client = docker.from_env()
    containers = client.containers.list(all=True)
    docker_containers = {}
    for container in containers:
        if 'com.docker.compose.service' in container.attrs['Config']['Labels']:
            container_name = container.attrs['Config']['Labels']['com.docker.compose.service']
            container_id = container.attrs['Id']
            container_is_running = container.attrs['State']['Running']
            docker_containers[container_name] = {'Id': container_id, 'Running': container_is_running}
            print(">>> container:", container_name, docker_containers[container_name])

    # try to restart a container (stop alice and start alice-upgrade)
    alice_docker_container = docker_containers['alice']
    alice_container = client.containers.get(alice_docker_container['Id'])

    print(">>> shut down alice ...")
    alice_container.stop()

    print(">>> waiting for alice container to exit ...")
    alice_id = alice_container.attrs['Id']
    wait_until_healthy(client, alice_id, is_healthy=False)
    alice_container.remove()

    new_alice_container = None
    alice_id = None
    try:
        print(">>> start new alice container ...")
        new_alice_container = client.containers.run(
            'acapy-test',
            command=alice_container.attrs['Config']['Cmd'],
            detach=True,
            environment={'RUST_LOG': 'aries-askar::log::target=error'},
            healthcheck=alice_container.attrs['Config']['Healthcheck'],
            name='alice',
            network=alice_container.attrs['HostConfig']['NetworkMode'],
            ports=alice_container.attrs['NetworkSettings']['Ports'],
        )
        alice_id = new_alice_container.attrs['Id']

        wait_until_healthy(client, alice_id)
        print(">>> new alice container is healthy")

        # run some more tests ...  alice should still be connected to bob for example ...
        async with Controller(base_url=ALICE) as alice, Controller(base_url=BOB) as bob:
            # Present the the credential's attributes
            print(">>> present proof ... again ...")
            await indy_present_proof_v2(
                bob,
                alice,
                bob_conn.connection_id,
                alice_conn.connection_id,
                requested_attributes=[{"name": "firstname"}],
            )
            print(">>> Done! (again)")
    finally:
        if alice_id and new_alice_container:
            # cleanup - shut down alice agent (not part of docker compose)
            print(">>> shut down alice ...")
            alice_container = client.containers.get(alice_id)
            alice_container.stop()
            wait_until_healthy(client, alice_id, is_healthy=False)
            alice_container.remove()


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
