from behave import given, when, then
import json
from time import sleep
import time

from bdd_support.agent_backchannel_client import (
    agent_container_GET,
    agent_container_POST,
    agent_container_PUT,
    async_sleep,
)


@given('"{issuer}" connects to a ledger that requires acceptance of the TAA')
def step_impl(context, issuer):
    agent = context.active_agents[issuer]

    taa_info = agent_container_GET(agent["agent"], "/ledger/taa")
    print("ledger taa_info:", taa_info)
    assert taa_info["result"]["taa_required"]


@given('"{issuer}" accepts the TAA')
@when('"{issuer}" accepts the TAA')
@then('"{issuer}" accepts the TAA')
def step_impl(context, issuer):
    agent = context.active_agents[issuer]

    taa_info = agent_container_GET(agent["agent"], "/ledger/taa")
    print("ledger taa_info:", taa_info)
    assert taa_info["result"]["taa_required"]

    taa_accept = {
        "mechanism": list(taa_info["result"]["aml_record"]["aml"].keys())[0],
        "version": taa_info["result"]["taa_record"]["version"],
        "text": taa_info["result"]["taa_record"]["text"],
    }
    print("taa_acceptance:", taa_accept)

    taa_status = agent_container_POST(
        agent["agent"],
        "/ledger/taa/accept",
        data=taa_accept,
    )


@given('"{issuer}" rejects the TAA')
@when('"{issuer}" rejects the TAA')
@then('"{issuer}" rejects the TAA')
def step_impl(context, issuer):
    agent = context.active_agents[issuer]

    taa_info = agent_container_GET(agent["agent"], "/ledger/taa")
    print("ledger taa_info:", taa_info)
    assert taa_info["result"]["taa_required"]

    # reject by "accepting" with the wrong text (this can override a prior acceptance)
    taa_accept = {
        "mechanism": list(taa_info["result"]["aml_record"]["aml"].keys())[0],
        "version": taa_info["result"]["taa_record"]["version"],
        "text": "Unacceptable text",
    }
    print("taa_rejectance:", taa_accept)

    taa_status = agent_container_POST(
        agent["agent"],
        "/ledger/taa/accept",
        data=taa_accept,
    )


@when('"{issuer}" posts a revocation correction to the ledger')
@then('"{issuer}" posts a revocation correction to the ledger')
def step_impl(context, issuer):
    agent = context.active_agents[issuer]

    # get the required revocation info from the last credential exchange
    cred_exchange = context.cred_exchange

    # post a correcting leger entry
    ledger_status = agent_container_PUT(
        agent["agent"],
        "/revocation/registry/"
        + cred_exchange["indy"]["rev_reg_id"]
        + "/fix-revocation-entry-state",
        params={
            "apply_ledger_update": "true",
        },
    )
