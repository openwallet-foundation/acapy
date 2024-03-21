import json
import os

from bdd_support.agent_backchannel_client import (
    agent_container_GET,
    agent_container_POST,
    async_sleep,
)
from behave import given, then


def is_anoncreds(agent):
    return agent["agent"].wallet_type == "askar-anoncreds"


BDD_EXTRA_AGENT_ARGS = os.getenv("BDD_EXTRA_AGENT_ARGS")

#      And "<issuer>" lists revocation registries
#      And "<issuer>" rotates revocation registries


@given("wait {count} seconds")
@then("wait {count} seconds")
def step_impl(context, count=None):
    if count:
        print(f"sleeping for {count} seconds..")
        async_sleep(int(count))


@given('"{issuer}" lists revocation registries {count}')
@then('"{issuer}" lists revocation registries {count}')
def step_impl(context, issuer, count=None):
    agent = context.active_agents[issuer]

    if not is_anoncreds(agent):
        endpoint = "/revocation/registries/created"
    else:
        endpoint = "/anoncreds/revocation/registries"

    async_sleep(5.0)
    created_response = agent_container_GET(agent["agent"], endpoint)
    full_response = agent_container_GET(
        agent["agent"], endpoint, params={"state": "full"}
    )
    decommissioned_response = agent_container_GET(
        agent["agent"],
        endpoint,
        params={"state": "decommissioned"},
    )
    finished_response = agent_container_GET(
        agent["agent"], endpoint, params={"state": "finished"}
    )
    async_sleep(4.0)
    if count:
        print(
            f"\nlists revocation registries ({count} creds) = = = = = = = = = = = = = ="
        )
    else:
        print(
            "\nlists revocation registries = = = = = = = = = = = = = = = = = = = = = ="
        )
    print("\ncreated_response: ", len(created_response["rev_reg_ids"]))
    print("full_response: ", len(full_response["rev_reg_ids"]))
    print("decommissioned_response:", len(decommissioned_response["rev_reg_ids"]))
    print("finished_response: ", len(finished_response["rev_reg_ids"]))
    async_sleep(1.0)


@given('"{issuer}" rotates revocation registries')
@then('"{issuer}" rotates revocation registries')
def step_impl(context, issuer):
    agent = context.active_agents[issuer]

    if not is_anoncreds(agent):
        endpoint = "/revocation/active-registry/"
    else:
        endpoint = "/anoncreds/revocation/active-registry/"

    cred_def_id = context.cred_def_id
    original_active_response = agent_container_GET(
        agent["agent"], f"{endpoint}{cred_def_id}"
    )
    print("original_active_response:", json.dumps(original_active_response))

    rotate_response = agent_container_POST(
        agent["agent"],
        f"{endpoint}{cred_def_id}/rotate",
        data={},
    )
    print("rotate_response:", json.dumps(rotate_response))

    async_sleep(10.0)

    active_response = agent_container_GET(agent["agent"], f"{endpoint}{cred_def_id}")
    print("active_response:", json.dumps(active_response))
