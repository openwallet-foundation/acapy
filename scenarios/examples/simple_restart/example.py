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
from docker.models.networks import Network

from acapy_controller import Controller
from acapy_controller.logging import logging_to_stdout
from acapy_controller.protocols import connection, didexchange

ALICE = getenv("ALICE", "http://alice:3001")
BOB = getenv("BOB", "http://bob:3001")


def healthy(container: Container) -> bool:
    """Check if container is healthy."""
    inspect_results = container.attrs
    return inspect_results["State"]["Running"] and inspect_results["State"]["Health"]["Status"] == "healthy"


def wait_until_healthy(container: Container, attempts: int = 350):
    """Wait until container is healthy."""
    print((container.name, container.status))
    for _ in range(attempts):
        if healthy(container):
            return
        else:
            time.sleep(1)
    raise TimeoutError("Timed out waiting for container")


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=ALICE) as alice, Controller(base_url=BOB) as bob:
        await connection(alice, bob)
        await didexchange(alice, bob)

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
    print(">>> container:", 'alice', json.dumps(alice_container.attrs))

    bob_docker_container = docker_containers['bob']
    bob_container = client.containers.get(bob_docker_container['Id'])
    print(">>> container:", 'bob', json.dumps(bob_container.attrs))

    alice_container.stop()
    alice_container.remove()

    print(">>> waiting for alice container to exit")
    time.sleep(10)

    print(">>> start new alice container")
    new_alice_container = client.containers.run(
        'acapy-test',
        command=alice_container.attrs['Config']['Cmd'],
        detach=True,
        environment={'RUST_LOG': 'aries-askar::log::target=error'},
        healthcheck=alice_container.attrs['Config']['Healthcheck'],
        name='alice',
        ports=alice_container.attrs['NetworkSettings']['Ports'],
    )
    print(">>> new container:", 'alice', json.dumps(new_alice_container.attrs))

    wait_until_healthy(new_alice_container)

    # TODO run some more tests ...  alice should still be connected to bob for example ...


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
