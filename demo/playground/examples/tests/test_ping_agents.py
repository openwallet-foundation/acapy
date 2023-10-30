"""Integration tests for Basic Message Storage."""

# pylint: disable=redefined-outer-name

import os
import pytest
import time
import uuid

from . import logger, Agent, FABER, ALICE, MULTI


@pytest.fixture(scope="session")
def faber():
    """faber agent fixture."""
    yield Agent(FABER)


@pytest.fixture(scope="session")
def alice():
    """resolver agent fixture."""
    yield Agent(ALICE)


@pytest.fixture(scope="session")
def multi_one():
    """resolver agent fixture."""
    agent = Agent(MULTI)
    wallet_name = f"multi_one_{str(uuid.uuid4())[0:8]}"
    resp = agent.create_tenant(wallet_name, "changeme")
    wallet_id = resp["wallet_id"]
    token = resp["token"]
    agent.headers = {"Authorization": f"Bearer {token}"}
    yield agent


@pytest.fixture(scope="session", autouse=True)
def alice_faber_connection(faber, alice):
    """Established connection filter."""
    logger.info("faber create invitation to alice")
    invite = faber.create_invitation(auto_accept="true")["invitation"]
    logger.info(f"invitation = {invite}")
    logger.info(f"alice receive invitation")
    resp = alice.receive_invite(invite, auto_accept="true")
    result = resp["connection_id"]
    logger.info(f"alice/faber connection_id = {result}")
    return result


@pytest.fixture(scope="session", autouse=True)
def faber_alice_connection(faber, alice):
    """Established connection filter."""
    logger.info("alice create invitation to faber")
    invite = alice.create_invitation(auto_accept="true")["invitation"]
    logger.info(f"invitation = {invite}")
    logger.info(f"faber receive invitation")
    resp = faber.receive_invite(invite, auto_accept="true")
    result = resp["connection_id"]
    logger.info(f"faber/alice connection_id = {result}")
    return result


@pytest.fixture(scope="session", autouse=True)
def alice_multi_one_connection(multi_one, alice):
    """Established connection filter."""
    logger.info("multi_one create invitation to alice")
    invite = multi_one.create_invitation(auto_accept="true")["invitation"]
    logger.info(f"invitation = {invite}")
    logger.info(f"alice receive invitation")
    resp = alice.receive_invite(invite, auto_accept="true")
    result = resp["connection_id"]
    logger.info(f"alice/multi_one connection_id = {result}")
    return result


@pytest.fixture(scope="session", autouse=True)
def multi_one_alice_connection(multi_one, alice):
    """Established connection filter."""
    logger.info("alice create invitation to multi_one")
    invite = alice.create_invitation(auto_accept="true")["invitation"]
    logger.info(f"invitation = {invite}")
    logger.info(f"faber receive invitation")
    resp = multi_one.receive_invite(invite, auto_accept="true")
    result = resp["connection_id"]
    logger.info(f"multi_one/alice connection_id = {result}")
    return result


@pytest.mark.skipif(
    os.getenv("MEDIATOR_INVITATION_URL") not in [None, "", " "],
    reason="MEDIATOR_INVITATION_URL is set. Running only tests that require mediator.",
)
def test_single_tenants(faber, alice, faber_alice_connection, alice_faber_connection):
    faber_alice_connection_active = False
    attempts = 0
    while not faber_alice_connection_active and attempts < 5:
        time.sleep(1)
        connection_resp = faber.get_connection(faber_alice_connection)
        faber_alice_connection_active = connection_resp["state"] == "active"
        logger.info(f"faber/alice active?  {faber_alice_connection_active}")
        attempts = attempts + 1

    alice_faber_connection_active = False
    attempts = 0
    while not alice_faber_connection_active and attempts < 5:
        time.sleep(1)
        connection_resp = alice.get_connection(alice_faber_connection)
        alice_faber_connection_active = connection_resp["state"] == "active"
        logger.info(f"alice/faber active?  {alice_faber_connection_active}")
        attempts = attempts + 1

    assert faber_alice_connection_active == True
    assert alice_faber_connection_active == True

    logger.info("faber alice pinging...")
    pings = 0
    while pings < 10:
        resp = faber.ping_connection(faber_alice_connection, "faber")
        logger.info(f"faber ping alice =  {resp}")
        time.sleep(1)
        alice.ping_connection(alice_faber_connection, "alice")
        logger.info(f"alice ping faber =  {resp}")
        time.sleep(1)
        pings = pings + 1


@pytest.mark.skipif(
    os.getenv("MEDIATOR_INVITATION_URL") not in [None, "", " "],
    reason="MEDIATOR_INVITATION_URL is set. Running only tests that require mediator.",
)
def test_multi_tenants(
    multi_one, alice, multi_one_alice_connection, alice_multi_one_connection
):
    multi_one_alice_connection_active = False
    attempts = 0
    while not multi_one_alice_connection_active and attempts < 5:
        time.sleep(1)
        connection_resp = multi_one.get_connection(multi_one_alice_connection)
        multi_one_alice_connection_active = connection_resp["state"] == "active"
        logger.info(f"multi_one/alice active?  {multi_one_alice_connection_active}")
        attempts = attempts + 1

    alice_multi_one_connection_active = False
    attempts = 0
    while not alice_multi_one_connection_active and attempts < 5:
        time.sleep(1)
        connection_resp = alice.get_connection(alice_multi_one_connection)
        alice_multi_one_connection_active = connection_resp["state"] == "active"
        logger.info(f"alice/multi_one active?  {alice_multi_one_connection_active}")
        attempts = attempts + 1

    assert multi_one_alice_connection_active == True
    assert alice_multi_one_connection_active == True

    logger.info("multi_one alice pinging...")
    pings = 0
    while pings < 10:
        resp = multi_one.ping_connection(multi_one_alice_connection, "multi_one")
        logger.info(f"multi_one ping alice =  {resp}")
        time.sleep(1)
        alice.ping_connection(alice_multi_one_connection, "alice")
        logger.info(f"alice ping multi_one =  {resp}")
        time.sleep(1)
        pings = pings + 1
