from behave import *
import json
from agent_backchannel_client import agent_backchannel_GET, agent_backchannel_POST, expected_agent_state
from time import sleep
import time

# This step is defined in another feature file
# Given "Acme" and "Bob" have an existing connection


SCHEMA_TEMPLATE = {
    "schema_name": "test_schema.",
    "schema_version": "1.0.0",
    "attributes": ["attr_1","attr_2","attr_3"],
}

CRED_DEF_TEMPLATE = {
  "support_revocation": False,
  "schema_id": "",
  "tag": "default"
}

CREDENTIAL_ATTR_TEMPLATE = [
    {"name": "attr_1", "value": "value_1"},
    {"name": "attr_2", "value": "value_2"},
    {"name": "attr_3", "value": "value_3"}
]

@given('"{issuer}" has a public did')
def step_impl(context, issuer):
    issuer_url = context.config.userdata.get(issuer)

    (resp_status, resp_text) = agent_backchannel_GET(issuer_url + "/agent/command/", "did")
    assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'

    resp_json = json.loads(resp_text)
    issuer_did = resp_json

    if "schema" not in context:
        # check for a schema already loaded in the context. If it is not, load the template
        if "schema" not in context:
            context.schema = SCHEMA_TEMPLATE.copy()
            context.schema["schema_name"] = context.schema["schema_name"] + issuer

    #context.issuer_did = issuer_did["did"]
    if 'issuer_did_dict' in context:
        context.issuer_did_dict[context.schema['schema_name']] = issuer_did["did"]
    else:
        context.issuer_did_dict = {context.schema['schema_name']: issuer_did["did"]}

@given('"{issuer}" is ready to issue a credential')
def step_impl(context, issuer):
    # TODO remove these references to schema and cred def, move them to one call to the API and let the Backchannel take care of
    # what to do to be ready to issie a credential
    context.execute_steps('''
      When "''' + issuer + '''" creates a new schema
       And "''' + issuer + '''" creates a new credential definition
      Then "''' + issuer + '''" has an existing schema
       And "''' + issuer + '''" has an existing credential definition
    ''')

@when('"{issuer}" creates a new schema')
def step_impl(context, issuer):
    issuer_url = context.config.userdata.get(issuer)

    #if not "issuer_schema_id_dict" in context:
        # check for a schema template already loaded in the context. If it is, it was loaded from an external Schema, so use it.
    if "schema" in context:
        schema = context.schema
    else:   
        schema = SCHEMA_TEMPLATE.copy()
        schema["schema_name"] = schema["schema_name"] + issuer

    (resp_status, resp_text) = agent_backchannel_POST(issuer_url + "/agent/command/", "schema", data=schema)
    assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'

    resp_json = json.loads(resp_text)
    #context.issuer_schema_id = resp_json["schema_id"]
    if 'issuer_schema_id_dict' in context:
        context.issuer_schema_id_dict[context.schema['schema_name']] = resp_json["schema_id"]
    else:
        context.issuer_schema_id_dict = {context.schema['schema_name']: resp_json["schema_id"]}

@when('"{issuer}" creates a new credential definition')
def step_impl(context, issuer):
    issuer_url = context.config.userdata.get(issuer)

    #if not "credential_definition_id_dict" in context:
    cred_def = CRED_DEF_TEMPLATE.copy()
    cred_def["schema_id"] = context.issuer_schema_id_dict[context.schema['schema_name']]
    if "support_revocation" in context:
        cred_def["support_revocation"] = context.support_revocation

    (resp_status, resp_text) = agent_backchannel_POST(issuer_url + "/agent/command/", "credential-definition", data=cred_def)
    assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'

    resp_json = json.loads(resp_text)
    if "support_revocation" in context:
        # Could make a call to get the rev reg creation time for calculating non revocation intervals
        #context.cred_rev_creation_time = resp_json["created"]
        context.cred_rev_creation_time = time.time()

    if 'credential_definition_id_dict' in context:
        context.credential_definition_id_dict[context.schema['schema_name']] = resp_json["credential_definition_id"]
    else:
        context.credential_definition_id_dict = {context.schema['schema_name']: resp_json["credential_definition_id"]}

@then('"{issuer}" has an existing schema')
def step_impl(context, issuer):
    issuer_url = context.config.userdata.get(issuer)
    issuer_schema_id = context.issuer_schema_id_dict[context.schema['schema_name']]

    (resp_status, resp_text) = agent_backchannel_GET(issuer_url + "/agent/command/", "schema", id=issuer_schema_id)
    assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'

    resp_json = json.loads(resp_text)
    #context.issuer_schema = resp_json
    if 'issuer_schema_dict' in context:
        context.issuer_schema_dict[context.schema['schema_name']] = resp_json
    else:
        context.issuer_schema_dict = {context.schema['schema_name']: resp_json}


@then('"{issuer}" has an existing credential definition')
def step_impl(context, issuer):
    issuer_url = context.config.userdata.get(issuer)
    issuer_credential_definition_id = context.credential_definition_id_dict[context.schema['schema_name']]

    (resp_status, resp_text) = agent_backchannel_GET(issuer_url + "/agent/command/", "credential-definition", id=issuer_credential_definition_id)
    assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'

    resp_json = json.loads(resp_text)
    #context.issuer_credential_definition = resp_json
    if 'issuer_credential_definition_dict' in context:
        context.issuer_credential_definition_dict[context.schema['schema_name']] = resp_json
    else:
        context.issuer_credential_definition_dict = {context.schema['schema_name']: resp_json}


@given('"{issuer}" has an existing schema and credential definition')
def step_impl(context, issuer):
    context.execute_steps(u'''
     Given "''' + issuer + '''" has a public did
      When "''' + issuer + '''" creates a new schema
       And "''' + issuer + '''" creates a new credential definition
      Then "''' + issuer + '''" has an existing schema
       And "''' + issuer + '''" has an existing credential definition
    ''')

@when('"{issuer}" initiates an automated credential issuance')
def step_impl(context, issuer):
    issuer_url = context.config.userdata.get(issuer)
    issuer_did = context.issuer_did
    issuer_connection_id = context.connection_id_dict[issuer][context.holder_name]
    issuer_schema_id = context.issuer_schema_id
    issuer_schema = context.issuer_schema
    issuer_credential_definition_id = context.credential_definition_id
    issuer_credential_definition = context.issuer_credential_definition

    credential_offer = {
        "schema_issuer_did": issuer_did,
        "issuer_did": issuer_did,
        "schema_name": issuer_schema["name"],
        "cred_def_id": issuer_credential_definition["id"],
        "schema_version": issuer_schema["version"],
        "credential_proposal": {
            "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/issue-credential/1.0/credential-preview",
            "attributes": CREDENTIAL_ATTR_TEMPLATE.copy(),
        },
        "connection_id": issuer_connection_id,
        "schema_id": issuer_schema["id"],
    }

    (resp_status, resp_text) = agent_backchannel_POST(issuer_url + "/agent/command/", "issue-credential", operation="send", data=credential_offer)
    assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'

    resp_json = json.loads(resp_text)
    issuer_credential_definition = resp_json

@given('"{holder}" proposes a credential to "{issuer}"')
@when('"{holder}" proposes a credential to "{issuer}"')
def step_impl(context, holder, issuer):
    holder_url = context.config.userdata.get(holder)

    # check for a schema template already loaded in the context. If it is, it was loaded from an external Schema, so use it.
    if "credential_data" in context:
        cred_data = context.credential_data
    else:   
        cred_data = CREDENTIAL_ATTR_TEMPLATE.copy()

    credential_offer = {
        "schema_issuer_did": context.issuer_did_dict[context.schema['schema_name']],
        "issuer_did": context.issuer_did_dict[context.schema['schema_name']],
        "schema_name": context.issuer_schema_dict[context.schema['schema_name']]["name"],
        "cred_def_id": context.issuer_credential_definition_dict[context.schema['schema_name']]["id"],
        "schema_version": context.issuer_schema_dict[context.schema['schema_name']]["version"],
        "credential_proposal": {
            "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/issue-credential/1.0/credential-preview",
            "attributes": cred_data,
        },
        "connection_id": context.connection_id_dict[holder][issuer],
        "schema_id": context.issuer_schema_dict[context.schema['schema_name']]["id"],
    }

    #(resp_status, resp_text) = agent_backchannel_POST(holder_url + "/agent/command/", "issue-credential", operation="send-proposal", id=holder_connection_id, data=credential_offer)
    (resp_status, resp_text) = agent_backchannel_POST(holder_url + "/agent/command/", "issue-credential", operation="send-proposal", data=credential_offer)
    assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'
    resp_json = json.loads(resp_text)

    # Check the State of the credential
    assert resp_json["state"] == "proposal-sent"

    # Get the thread ID from the response text.
    context.cred_thread_id = resp_json["thread_id"]

@given('"{issuer}" offers a credential')
@when('"{issuer}" offers a credential')
@when('"{issuer}" offers the credential')
@when('"{issuer}" sends a credential offer')
def step_impl(context, issuer):
    issuer_url = context.config.userdata.get(issuer)

    # if context does not have the credential thread id then the proposal was not the starting point for the protocol. 
    if not "cred_thread_id" in context:

        if "credential_data" in context:
            cred_data = context.credential_data
        else:   
            cred_data = CREDENTIAL_ATTR_TEMPLATE.copy()

        credential_offer = {
            "cred_def_id": context.issuer_credential_definition_dict[context.schema['schema_name']]["id"],
            "credential_preview": {
                "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/issue-credential/1.0/credential-preview",
                "attributes": cred_data,
            },
            "connection_id": context.connection_id_dict[issuer][context.holder_name],
        }

        (resp_status, resp_text) = agent_backchannel_POST(issuer_url + "/agent/command/", "issue-credential", operation="send-offer", data=credential_offer)
        assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'
        resp_json = json.loads(resp_text)
        context.cred_thread_id = resp_json["thread_id"]

    else:
        # If context has the credential thread id then the proposal was done. 
        (resp_status, resp_text) = agent_backchannel_POST(issuer_url + "/agent/command/", "issue-credential", operation="send-offer", id=context.cred_thread_id)
        assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'
        resp_json = json.loads(resp_text)
        
    # Check the issuers State
    assert resp_json["state"] == "offer-sent"

    # Check the state of the holder after issuers call of send-offer
    assert expected_agent_state(context.holder_url, "issue-credential", context.cred_thread_id, "offer-received")

    
@when('"{holder}" requests the credential')
@when('"{holder}" sends a credential request')
def step_impl(context, holder):
    holder_url = context.holder_url

    # If @indy then we can be sure we cannot start the protocol from this command. We can be sure that we have previously 
    # reveived the thread_id.
    if "Indy" in context.tags:
        sleep(1)
        (resp_status, resp_text) = agent_backchannel_POST(holder_url + "/agent/command/", "issue-credential", operation="send-request", id=context.cred_thread_id)

    # If we are starting from here in the protocol you won't have the cred_ex_id or the thread_id
    else:
        (resp_status, resp_text) = agent_backchannel_POST(holder_url + "/agent/command/", "issue-credential", operation="send-request", id=context.connection_id_dict[holder][context.issuer_name])
    
    assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'
    resp_json = json.loads(resp_text)
    assert resp_json["state"] == "request-sent"

    # Verify issuer status
    assert expected_agent_state(context.issuer_url, "issue-credential", context.cred_thread_id, "request-received")


@when('"{issuer}" issues the credential')
@when('"{issuer}" issues a credential')
def step_impl(context, issuer):
    issuer_url = context.config.userdata.get(issuer)

    if "credential_data" in context:
        cred_data = context.credential_data
    else:   
        cred_data = CREDENTIAL_ATTR_TEMPLATE.copy()

    # a credential preview shouldn't have to be here with a cred_ex_id being passed
    credential_preview = {
        "credential_preview": {
            "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/issue-credential/1.0/credential-preview",
            "attributes": cred_data,
        },
        "comment": "issuing credential",
    }

    (resp_status, resp_text) = agent_backchannel_POST(issuer_url + "/agent/command/", "issue-credential", operation="issue", id=context.cred_thread_id, data=credential_preview)
    assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'
    resp_json = json.loads(resp_text)
    assert resp_json["state"] == "credential-issued"

    # Verify holder status
    assert expected_agent_state(context.holder_url, "issue-credential", context.cred_thread_id, "credential-received")


@when('"{holder}" acknowledges the credential issue')
@when('"{holder}" receives and acknowledges the credential')
def step_impl(context, holder):
    holder_url = context.config.userdata.get(holder)
    
    # a credential id shouldn't be needed with a cred_ex_id being passed
    credential_id = {
        "credential_id": context.cred_thread_id,
    }

    # (resp_status, resp_text) = agent_backchannel_POST(holder_url + "/agent/command/", "credential", operation="store", id=context.holder_cred_ex_id)
    sleep(1)
    (resp_status, resp_text) = agent_backchannel_POST(holder_url + "/agent/command/", "issue-credential", operation="store", id=context.cred_thread_id, data=credential_id)
    assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'
    resp_json = json.loads(resp_text)
    assert resp_json["state"] == "done"
    #context.credential_id = resp_json["credential_id"]
    if 'credential_id_dict' in context:
        try:
            context.credential_id_dict[context.schema['schema_name']].append(resp_json["credential_id"])
        except KeyError:
            context.credential_id_dict[context.schema['schema_name']] = [resp_json["credential_id"]]
    else:
        context.credential_id_dict = {context.schema['schema_name']: [resp_json["credential_id"]]}

    # Verify issuer status
    # This is returning none instead of Done. Should this be the case. Needs investigation.
    #assert expected_agent_state(context.issuer_url, "issue-credential", context.cred_thread_id, "done")

    # if the credential supports revocation, get the Issuers webhook callback JSON from the store command
    # From that JSON save off the credential revocation identifier, and the revocation registry identifier.
    if "support_revocation" in context:
        if context.support_revocation:
            (resp_status, resp_text) = agent_backchannel_GET(context.config.userdata.get(context.issuer_name) + "/agent/response/", "revocation-registry", id=context.cred_thread_id)
            assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'
            resp_json = json.loads(resp_text)
            context.cred_rev_id = resp_json["revocation_id"]
            context.rev_reg_id = resp_json["revoc_reg_id"]
        

@then('"{holder}" has the credential issued')
def step_impl(context, holder):

        holder_url = context.config.userdata.get(holder)
        # get the credential from the holders wallet
        (resp_status, resp_text) = agent_backchannel_GET(holder_url + "/agent/command/", "credential", id=context.credential_id_dict[context.schema['schema_name']][len(context.credential_id_dict[context.schema['schema_name']])-1])
        assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'
        resp_json = json.loads(resp_text)
        assert resp_json["referent"] == context.credential_id_dict[context.schema['schema_name']][len(context.credential_id_dict[context.schema['schema_name']])-1]
        assert resp_json["schema_id"] == context.issuer_schema_id_dict[context.schema["schema_name"]]
        assert resp_json["cred_def_id"] == context.credential_definition_id_dict[context.schema["schema_name"]]

        # Make sure the issuer is not holding the credential
        # get the credential from the holders wallet
        # TODO this expected error is not displaying in the agent output until after all the tests are executed. Uncomment this out when
        # there is a solution to the error messaging happening at the end. 
        #(resp_status, resp_text) = agent_backchannel_GET(context.issuer_url + "/agent/command/", "credential", id=context.credential_id_dict[context.schema['schema_name']])
        #assert resp_status == 404, f'resp_status {resp_status} is not 404; {resp_text}'



@when(u'"{holder}" negotiates the offer with a proposal of the credential to "{issuer}"')
@when(u'"{holder}" negotiates the offer with another proposal of the credential to "{issuer}"')
def step_impl(context, holder, issuer):
    #context.execute_steps('''When "''' + holder + '''" proposes a credential to "''' + sender + ''')
    context.execute_steps('''
        When "''' + holder + '''" proposes a credential to "''' + issuer + '''"
    ''')
