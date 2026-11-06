"""Integration tests for Basic Message Storage."""

# pylint: disable=redefined-outer-name

import os
import time
import uuid

import pytest
import pytest_asyncio

from . import ALICE, FABER, MULTI, Agent, logger


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def faber():
    """faber agent fixture."""
    agent = Agent(FABER)
    yield agent
    await agent.close()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def alice():
    """resolver agent fixture."""
    agent = Agent(ALICE)
    yield agent
    await agent.close()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def multi_one():
    """resolver agent fixture."""
    agent = Agent(MULTI)
    wallet_name = f"multi_one_{str(uuid.uuid4())[0:8]}"
    resp = await agent.create_tenant(wallet_name, "changeme")
    wallet_id = resp["wallet_id"]
    token = resp["token"]
    agent.headers = {"Authorization": f"Bearer {token}"}
    yield agent
    await agent.close()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def alice_faber_connection(faber, alice):
    """Established connection filter."""
    logger.info("faber create invitation to alice")
    invite = (await faber.create_invitation(auto_accept="true"))["invitation"]
    logger.info(f"invitation = {invite}")
    logger.info("alice receive invitation")
    resp = await alice.receive_invite(invite, auto_accept="true")
    result = resp["connection_id"]
    logger.info(f"alice/faber connection_id = {result}")
    return result


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def faber_alice_connection(faber, alice):
    """Established connection filter."""
    logger.info("alice create invitation to faber")
    invite = (await alice.create_invitation(auto_accept="true"))["invitation"]
    logger.info(f"invitation = {invite}")
    logger.info("faber receive invitation")
    resp = await faber.receive_invite(invite, auto_accept="true")
    result = resp["connection_id"]
    logger.info(f"faber/alice connection_id = {result}")
    return result


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def alice_multi_one_connection(multi_one, alice):
    """Established connection filter."""
    logger.info("multi_one create invitation to alice")
    invite = (await multi_one.create_invitation(auto_accept="true"))["invitation"]
    logger.info(f"invitation = {invite}")
    logger.info("alice receive invitation")
    resp = await alice.receive_invite(invite, auto_accept="true")
    result = resp["connection_id"]
    logger.info(f"alice/multi_one connection_id = {result}")
    return result


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def multi_one_alice_connection(multi_one, alice):
    """Established connection filter."""
    logger.info("alice create invitation to multi_one")
    invite = (await alice.create_invitation(auto_accept="true"))["invitation"]
    logger.info(f"invitation = {invite}")
    logger.info("faber receive invitation")
    resp = await multi_one.receive_invite(invite, auto_accept="true")
    result = resp["connection_id"]
    logger.info(f"multi_one/alice connection_id = {result}")
    return result


@pytest.mark.skipif(
    os.getenv("MEDIATOR_INVITATION_URL") not in [None, "", " "],
    reason="MEDIATOR_INVITATION_URL is set. Running only tests that require mediator.",
)
@pytest.mark.asyncio
async def test_single_tenants(
    faber, alice, faber_alice_connection, alice_faber_connection
):
    faber_alice_connection_active = False
    attempts = 0
    while not faber_alice_connection_active and attempts < 5:
        time.sleep(1)
        connection_resp = await faber.get_connection(faber_alice_connection)
        faber_alice_connection_active = connection_resp["state"] == "active"
        logger.info(f"faber/alice active?  {faber_alice_connection_active}")
        attempts = attempts + 1

    alice_faber_connection_active = False
    attempts = 0
    while not alice_faber_connection_active and attempts < 5:
        time.sleep(1)
        connection_resp = await alice.get_connection(alice_faber_connection)
        alice_faber_connection_active = connection_resp["state"] == "active"
        logger.info(f"alice/faber active?  {alice_faber_connection_active}")
        attempts = attempts + 1

    assert faber_alice_connection_active is True
    assert alice_faber_connection_active is True

    logger.info("faber alice pinging...")
    pings = 0
    while pings < 10:
        resp = await faber.ping_connection(faber_alice_connection, "faber")
        logger.info(f"faber ping alice =  {resp}")
        time.sleep(1)
        await alice.ping_connection(alice_faber_connection, "alice")
        logger.info(f"alice ping faber =  {resp}")
        time.sleep(1)
        pings = pings + 1


@pytest.mark.skipif(
    os.getenv("MEDIATOR_INVITATION_URL") not in [None, "", " "],
    reason="MEDIATOR_INVITATION_URL is set. Running only tests that require mediator.",
)
@pytest.mark.asyncio
async def test_multi_tenants(
    multi_one, alice, multi_one_alice_connection, alice_multi_one_connection
):
    multi_one_alice_connection_active = False
    attempts = 0
    while not multi_one_alice_connection_active and attempts < 5:
        time.sleep(1)
        connection_resp = await multi_one.get_connection(multi_one_alice_connection)
        multi_one_alice_connection_active = connection_resp["state"] == "active"
        logger.info(f"multi_one/alice active?  {multi_one_alice_connection_active}")
        attempts = attempts + 1

    alice_multi_one_connection_active = False
    attempts = 0
    while not alice_multi_one_connection_active and attempts < 5:
        time.sleep(1)
        connection_resp = await alice.get_connection(alice_multi_one_connection)
        alice_multi_one_connection_active = connection_resp["state"] == "active"
        logger.info(f"alice/multi_one active?  {alice_multi_one_connection_active}")
        attempts = attempts + 1

    assert multi_one_alice_connection_active is True
    assert alice_multi_one_connection_active is True

    logger.info("multi_one alice pinging...")
    pings = 0
    while pings < 10:
        resp = await multi_one.ping_connection(multi_one_alice_connection, "multi_one")
        logger.info(f"multi_one ping alice =  {resp}")
        time.sleep(1)
        await alice.ping_connection(alice_multi_one_connection, "alice")
        logger.info(f"alice ping multi_one =  {resp}")
        time.sleep(1)
        pings = pings + 1
