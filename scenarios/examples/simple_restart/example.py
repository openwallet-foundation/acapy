"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from os import getenv

import docker

from acapy_controller import Controller
from acapy_controller.logging import logging_to_stdout
from acapy_controller.protocols import connection, didexchange

ALICE = getenv("ALICE", "http://alice:3001")
BOB = getenv("BOB", "http://bob:3001")


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
        container_name = container.attrs['Config']['Labels']['com.docker.compose.service']
        container_id = container.attrs['Id']
        container_is_running = container.attrs['State']['Running']
        docker_containers[container_name] = {'Id': container_id, 'Running': container_is_running}
        print(">>> container:", container_name, docker_containers[container_name])

    # try to restart a container (stop alice and start alice-upgrade)


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
