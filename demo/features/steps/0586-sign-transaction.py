from behave import given, when, then
import json
from time import sleep
import time

from bdd_support.agent_backchannel_client import (
    agent_container_register_did,
    agent_container_GET,
    agent_container_POST,
)
from runners.agent_container import AgentContainer


# This step is defined in another feature file
# Given "Acme" and "Bob" have an existing connection


@when('"{agent_name}" has a DID with role "{did_role}"')
def step_impl(context, agent_name, did_role):
    agent = context.active_agents[agent_name]

    # create a new DID in the current wallet
    created_did = agent_container_POST(agent['agent'], "/wallet/did/create")

    # publish to the ledger with did_role
    registered_did = agent_container_register_did(
        agent['agent'],
        created_did["result"]["did"],
        created_did["result"]["verkey"],
        "ENDORSER" if did_role == "ENDORSER" else "",
    )

    # make the new did the wallet's public did
    created_did = agent_container_POST(agent['agent'], "/wallet/did/public", params={"did": created_did["result"]["did"]})

    if not "public_dids" in context:
        context.public_dids = {}
    context.public_dids[did_role] = created_did["result"]["did"]


@when('"{agent_name}" connection has job role "{connection_job_role}"')
def step_impl(context, agent_name, connection_job_role):
    agent = context.active_agents[agent_name]

    # current connection_id for the selected agent
    connection_id = agent['agent'].agent.connection_id

    # set role for agent's connection
    #updated_connection = agent_container_POST(
    #    agent['agent'],
    #    "/transaction/set-job",
    #    params={"connection": connection_id, "my_job": connection_job_role}
    #)
    pass
