# -----------------------------------------------------------
# Behave Step Definitions for the Connection Protocol 0160
# used to establish connections between Aries Agents.
# 0160 connection-protocol RFC:
# https://github.com/hyperledger/aries-rfcs/tree/9b0aaa39df7e8bd434126c4b33c097aae78d65bf/features/0160-connection-protocol#0160-connection-protocol
#
# Current AIP version level of test coverage: 1.0
#
# -----------------------------------------------------------

from behave import given, when, then
import json
import os

from bdd_support.agent_backchannel_client import (
    create_agent_container_with_args,
    aries_container_initialize,
    aries_container_generate_invitation,
    aries_container_receive_invitation,
    aries_container_detect_connection,
    agent_container_GET,
    agent_container_POST,
)
from runners.agent_container import AgentContainer


BDD_EXTRA_AGENT_ARGS = os.getenv("BDD_EXTRA_AGENT_ARGS")


@given("{n} agents")
@given("we have {n} agents")
def step_impl(context, n):
    """Startup 'n' agents based on the options provided in the context table parameters."""

    start_port = 8020

    extra_args = None
    if BDD_EXTRA_AGENT_ARGS:
        print("Got extra args:", BDD_EXTRA_AGENT_ARGS)
        extra_args = json.loads(BDD_EXTRA_AGENT_ARGS)

    context.active_agents = {}
    for row in context.table:
        agent_name = row["name"]
        agent_role = row["role"]
        agent_params = row["capabilities"]
        in_args = [
            "--ident",
            agent_name,
            "--port",
            str(start_port),
        ]
        if agent_params and 0 < len(agent_params):
            in_args.extend(agent_params.split(" "))
        if extra_args and extra_args.get("wallet-type"):
            in_args.extend(
                [
                    "--wallet-type",
                    extra_args.get("wallet-type"),
                ]
            )

        context.active_agents[agent_name] = {
            "name": agent_name,
            "role": agent_role,
            "agent": None,
        }

        # startup an agent with the provided params
        print("Create agent with:", in_args)
        agent = create_agent_container_with_args(in_args)

        # keep reference to the agent so we can shut it down later
        context.active_agents[agent_name]["agent"] = agent

        aries_container_initialize(
            agent,
        )
        start_port = start_port + 10


@when('"{inviter}" generates a connection invitation')
def step_impl(context, inviter):
    agent = context.active_agents[inviter]

    invitation = aries_container_generate_invitation(agent["agent"])
    context.inviter_invitation = invitation["invitation"]

    # get connection and verify status
    # assert expected_agent_state(inviter_url, "connection", context.temp_connection_id_dict[inviter], "invited")


@when('"{invitee}" receives the connection invitation')
def step_impl(context, invitee):
    agent = context.active_agents[invitee]

    invite_data = context.inviter_invitation
    connection = aries_container_receive_invitation(agent["agent"], invite_data)

    # get connection and verify status
    # assert expected_agent_state(invitee_url, "connection", context.connection_id_dict[invitee][context.inviter_name], "invited")


@then('"{agent_name}" has an active connection')
def step_impl(context, agent_name):
    agent = context.active_agents[agent_name]

    # throws an exception if the connection isn't established in time
    aries_container_detect_connection(agent["agent"])


@given('"{sender}" and "{receiver}" have an existing connection')
def step_impl(context, sender, receiver):
    context.execute_steps(
        '''
        When "'''
        + sender
        + '''" generates a connection invitation
        And "'''
        + receiver
        + '''" receives the connection invitation
        Then "'''
        + sender
        + '''" has an active connection
        And "'''
        + receiver
        + """" has an active connection
    """
    )
