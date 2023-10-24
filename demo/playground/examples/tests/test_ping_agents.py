"""Integration tests for Basic Message Storage."""

# pylint: disable=redefined-outer-name

import os
import pytest
import time

from . import logger, Agent, FABER, ALICE


@pytest.fixture(scope="session")
def faber():
    """faber agent fixture."""
    yield Agent(FABER)


@pytest.fixture(scope="session")
def alice():
    """resolver agent fixture."""
    yield Agent(ALICE)


@pytest.fixture(scope="session", autouse=True)
def faber_alice_connection(faber, alice):
    """Established connection filter."""
    invite = faber.create_invitation(auto_accept="true")["invitation"]
    resp = alice.receive_invite(invite, auto_accept="true")
    yield resp["connection_id"]


@pytest.mark.skipif(
    os.getenv("INVITATION_URL") not in [None, "", " "],
    reason="INVITATION_URL is set, use mediator",
)
def test_ping(faber, alice, faber_alice_connection):
    # make sure connection is active...
    time.sleep(2)

    # alice ping faber
    resp = alice.ping_connection(faber_alice_connection, "faber")
    assert True
