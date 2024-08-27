"""Minimal reproducible example script.

This script is for you to use to reproduce a bug or demonstrate a feature.
"""

import asyncio
from os import getenv

from acapy_controller import Controller
from acapy_controller.logging import logging_to_stdout
from acapy_controller.protocols import (
    connection,
    didexchange,
    request_mediation_v1,
    trustping,
)

ALICE = getenv("ALICE", "http://alice:3001")
BOB = getenv("BOB", "http://bob:3001")
MEDIATOR = getenv("MEDIATOR", "http://mediator:3001")


async def main():
    """Test Controller protocols."""
    alice = Controller(base_url=ALICE)
    bob = Controller(base_url=BOB)
    mediator = Controller(base_url=MEDIATOR)

    async with alice, bob, mediator:
        ma, am = await didexchange(mediator, alice)
        mam, amm = await request_mediation_v1(
            mediator, alice, ma.connection_id, am.connection_id
        )
        await alice.put(f"/mediation/{amm.mediation_id}/default-mediator")
        ab, ba = await didexchange(alice, bob)
        await trustping(alice, ab)

        ab, ba = await connection(alice, bob)
        await trustping(alice, ab)


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
