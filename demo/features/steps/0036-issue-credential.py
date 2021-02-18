
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
    read_schema_data,
    read_credential_data,
    read_proof_req_data,
    read_presentation_data,
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


@given('"{issuer}" is ready to issue a credential for {schema_name}')
def step_impl(context, issuer, schema_name):
    agent = context.active_agents[issuer]

    schema_info = read_schema_data(schema_name)
    cred_def_id = aries_container_create_schema_cred_def(
        agent['agent'],
        schema_info["schema"]["schema_name"],
        schema_info["schema"]["attributes"],
    )

    context.schema_name = schema_name
    context.cred_def_id = cred_def_id


@when('"{issuer}" offers a credential with data {credential_data}')
def step_impl(context, issuer, credential_data):
    agent = context.active_agents[issuer]

    cred_attrs = read_credential_data(context.schema_name, credential_data)
    aries_container_issue_credential(
        agent['agent'],
        context.cred_def_id,
        cred_attrs,
    )

    context.cred_attrs = cred_attrs
        
    # TODO Check the issuers State
    #assert resp_json["state"] == "offer-sent"

    # TODO Check the state of the holder after issuers call of send-offer
    #assert expected_agent_state(context.holder_url, "issue-credential", context.cred_thread_id, "offer-received")

    
@then('"{holder}" has the credential issued')
def step_impl(context, holder):
    agent = context.active_agents[holder]

    cred_def_id = context.cred_def_id
    cred_attrs = context.cred_attrs

    # check the received credential status (up to 10 seconds)
    for i in range(10):
        if aries_container_receive_credential(agent['agent'], cred_def_id, cred_attrs):
            return

    assert False
