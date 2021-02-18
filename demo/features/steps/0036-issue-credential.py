
from behave import given, when, then
import json
from time import sleep
import time

from bdd_support.agent_backchannel_client import (
    create_agent_container_with_args,
    aries_container_initialize,
    aries_container_generate_invitation,
    aries_container_receive_invitation,
    aries_container_detect_connection,
    aries_container_create_schema_cred_def,
    aries_container_issue_credential,
    aries_container_receive_credential,
    agent_backchannel_GET,
    agent_backchannel_POST,
    expected_agent_state
)
from runners.agent_container import AgentContainer


# This step is defined in another feature file
# Given "Acme" and "Bob" have an existing connection


SCHEMA_TEMPLATE = {
    "schema_name": "test_schema",
    "schema_version": "1.0.0",
    "attributes": ["attr_1","attr_2","attr_3"],
}

CRED_DEF_TEMPLATE = {
  "support_revocation": False,
  "schema_id": "",
  "tag": "default"
}

CREDENTIAL_ATTR_TEMPLATE = {
    "attr_1": "value_1",
    "attr_2": "value_2",
    "attr_3": "value_3",
}


@given('"{issuer}" is ready to issue a credential')
def step_impl(context, issuer):
    agent = context.active_agents[issuer]

    cred_def_id = aries_container_create_schema_cred_def(
        agent['agent'],
        SCHEMA_TEMPLATE["schema_name"],
        SCHEMA_TEMPLATE["attributes"],
    )

    context.cred_def_id = cred_def_id
    context.cred_attrs  = CREDENTIAL_ATTR_TEMPLATE


@when('"{issuer}" offers a credential')
def step_impl(context, issuer):
    agent = context.active_agents[issuer]

    aries_container_issue_credential(
        agent['agent'],
        context.cred_def_id,
        context.cred_attrs,
    )
        
    # TODO Check the issuers State
    #assert resp_json["state"] == "offer-sent"

    # TODO Check the state of the holder after issuers call of send-offer
    #assert expected_agent_state(context.holder_url, "issue-credential", context.cred_thread_id, "offer-received")

    
@when('"{holder}" requests the credential')
def step_impl(context, holder):
    # TODO
    pass


@when('"{issuer}" issues the credential')
def step_impl(context, issuer):
    # TODO
    pass


@when('"{holder}" acknowledges the credential issue')
def step_impl(context, holder):
    # TODO
    pass


@then('"{holder}" has the credential issued')
def step_impl(context, holder):
    agent = context.active_agents[holder]

    # TODO check the received credential status
    sleep(5)

