"""Integration tests for Basic Message Storage."""

# pylint: disable=redefined-outer-name

import base64
import os
import pytest
import time

import json as jsonlib

from . import logger, Agent, FABER, ALICE

# add a blank line...
logger.info("start testing mediated connections...")


@pytest.fixture(scope="session")
def faber():
    """faber agent fixture."""
    logger.info(f"faber = {FABER}")
    yield Agent(FABER)


@pytest.fixture(scope="session")
def alice():
    """resolver agent fixture."""
    logger.info(f"alice = {ALICE}")
    yield Agent(ALICE)


@pytest.fixture(scope="session")
def mediation_invite():
    invitation_url = os.getenv("INVITATION_URL")
    logger.info(f"INVITATION_URL = {invitation_url}")
    base64_message = invitation_url.split("=", maxsplit=1)[1]
    base64_bytes = base64_message.encode("ascii")
    message_bytes = base64.b64decode(base64_bytes)
    data = message_bytes.decode("ascii")
    logger.info(f"invitation_block = {data}")
    yield data


def initialize_mediation(agent: Agent, invitation):
    connection_id = None
    mediator_connection_state = None
    mediation_id = None
    mediation_granted = False

    invitation_json = agent.receive_invite(
        invitation, auto_accept="true", alias="mediator"
    )
    connection_id = invitation_json["connection_id"]
    logger.info(f"connection_id: {connection_id}")
    time.sleep(2)

    attempts = 0
    while mediator_connection_state != "active" and attempts < 5:
        time.sleep(1)
        connection_json = agent.get_connection(connection_id)
        mediator_connection_state = connection_json["state"]
        logger.info(f"mediator_connection_state: {mediator_connection_state}")
        attempts = attempts + 1

    if mediator_connection_state == "active":
        mediation_request_json = agent.request_for_mediation(connection_id)
        mediation_id = mediation_request_json["mediation_id"]
        logger.info(f"mediation_id: {mediation_id}")
        mediation_granted = False
        attempts = 0
        while not mediation_granted and attempts < 5:
            time.sleep(1)
            granted_json = agent.get_mediation_request(mediation_id)
            mediation_granted = granted_json["state"] == "granted"
            logger.info(f"mediation_granted: {mediation_granted}")
            attempts = attempts + 1

    result = {
        "connection_id": connection_id,
        "mediation_id": mediation_id,
        "mediator_connection_state": mediator_connection_state,
        "mediation_granted": mediation_granted,
    }
    return result


@pytest.fixture(scope="session")
def faber_mediator(faber, mediation_invite):
    logger.info(f"faber_mediator...")
    result = initialize_mediation(faber, mediation_invite)
    logger.info(f"...faber_mediator = {result}")
    yield result


@pytest.fixture(scope="session")
def alice_mediator(alice, mediation_invite):
    logger.info(f"alice_mediator...")
    result = initialize_mediation(alice, mediation_invite)
    logger.info(f"...alice_mediator = {result}")
    yield result


@pytest.mark.skipif(
    os.getenv("INVITATION_URL") in [None, "", " "],
    reason="INVITATION_URL not set, cannot connect with mediator",
)
def test_mediated_single_tenants(
    faber, alice, faber_mediator, alice_mediator, mediation_invite
):
    assert faber_mediator["mediation_granted"] == True
    assert alice_mediator["mediation_granted"] == True

    resp = faber.create_invitation(
        alias="alice",
        auto_accept="true",
        json={"my_label": "faber", "mediation_id": faber_mediator["mediation_id"]},
    )
    faber_alice_connection_id = resp["connection_id"]
    logger.info(f"faber_alice_connection_id = {faber_alice_connection_id}")
    assert faber_alice_connection_id
    invite = resp["invitation"]
    logger.info(f"invite = {invite}")
    assert invite

    mediation_invite_json = jsonlib.loads(mediation_invite)
    logger.info(f"invitation service endpoint = {invite['serviceEndpoint']}")
    logger.info(
        f"mediator service endpoint = {mediation_invite_json['serviceEndpoint']}"
    )
    assert invite["serviceEndpoint"] == mediation_invite_json["serviceEndpoint"]

    resp = alice.receive_invite(invite, alias="faber", auto_accept="true")
    alice_faber_connection_id = resp["connection_id"]
    logger.info(f"alice_faber_connection_id = {alice_faber_connection_id}")
    assert alice_faber_connection_id

    faber_alice_connection_active = False
    attempts = 0
    while not faber_alice_connection_active and attempts < 5:
        time.sleep(1)
        connection_resp = faber.get_connection(faber_alice_connection_id)
        faber_alice_connection_active = connection_resp["state"] == "active"
        logger.info(f"faber/alice active?  {faber_alice_connection_active}")
        attempts = attempts + 1

    alice_faber_connection_active = False
    attempts = 0
    while not alice_faber_connection_active and attempts < 5:
        time.sleep(1)
        connection_resp = alice.get_connection(alice_faber_connection_id)
        alice_faber_connection_active = connection_resp["state"] == "active"
        logger.info(f"alice/faber active?  {alice_faber_connection_active}")
        attempts = attempts + 1

    assert faber_alice_connection_active == True
    assert alice_faber_connection_active == True

    logger.info("faber alice pinging...")
    pings = 0
    while pings < 10:
        resp = faber.ping_connection(faber_alice_connection_id, "faber")
        logger.info(f"faber ping alice =  {resp}")
        time.sleep(1)
        alice.ping_connection(alice_faber_connection_id, "alice")
        logger.info(f"alice ping faber =  {resp}")
        time.sleep(1)
        pings = pings + 1


# @pytest.mark.skipif(
#     os.getenv("INVITATION_URL") in [None, "", " "],
#     reason="INVITATION_URL not set, cannot connect with mediator",
# )
# def test_faber_mediation_granted(faber, faber_mediator_connection, faber_mediation_id):
#     assert faber_mediation_id["mediation_granted"]


# @pytest.mark.skipif(
#     os.getenv("INVITATION_URL") in [None, "", " "],
#     reason="INVITATION_URL not set, cannot connect with mediator",
# )
# def test_alice_connect_mediator(alice, alice_mediator_connection):
#     # make sure connection is active...
#     time.sleep(5)

#     # resp = alice.ping_connection(alice_mediator_connection, "alice")
#     # assert True

#     resp = alice.list_connections(alias="mediator")
#     logger.info(f"alice connections = {resp}")
