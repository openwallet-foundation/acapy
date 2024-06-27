import json

from bdd_support.agent_backchannel_client import (
    agent_container_DELETE,
    agent_container_GET,
    agent_container_POST,
    aries_container_check_exists_cred_def,
    aries_container_create_schema_cred_def,
    aries_container_issue_credential,
    aries_container_receive_credential,
    async_sleep,
    read_credential_data,
    read_schema_data,
)
from behave import given, then, when
from runners.support.agent import (
    DID_METHOD_KEY,
    KEY_TYPE_BLS,
    SIG_TYPE_BLS,
)


def is_anoncreds(agent):
    return agent["agent"].wallet_type == "askar-anoncreds"


# This step is defined in another feature file
# Given "Acme" and "Bob" have an existing connection


@given('"{issuer}" is ready to issue a credential for {schema_name}')
@then('"{issuer}" is ready to issue a credential for {schema_name}')
def step_impl(context, issuer, schema_name):
    agent = context.active_agents[issuer]

    schema_info = read_schema_data(schema_name)
    cred_def_id = aries_container_create_schema_cred_def(
        agent["agent"],
        schema_info["schema"]["schema_name"],
        schema_info["schema"]["attributes"],
        version=schema_info["schema"]["schema_version"],
    )

    # confirm the cred def was actually created
    # TODO for anoncreds, this should call the anoncreds/cred-def endpoint
    async_sleep(2.0)
    cred_def_saved = aries_container_check_exists_cred_def(agent["agent"], cred_def_id)
    assert cred_def_saved

    context.schema_name = schema_name
    context.cred_def_id = cred_def_id


@when('"{issuer}" sets the credential type to {credential_type}')
def step_impl(context, issuer, credential_type):
    agent = context.active_agents[issuer]

    agent["agent"].set_cred_type(credential_type)

    assert agent["agent"].cred_type == credential_type


@given('"{issuer}" offers a credential with data {credential_data}')
@when('"{issuer}" offers a credential with data {credential_data}')
def step_impl(context, issuer, credential_data):
    agent = context.active_agents[issuer]

    cred_attrs = read_credential_data(context.schema_name, credential_data)
    cred_exchange = aries_container_issue_credential(
        agent["agent"],
        context.cred_def_id,
        cred_attrs,
    )

    context.cred_attrs = cred_attrs
    context.cred_exchange = cred_exchange

    # TODO Check the issuers State
    # assert resp_json["state"] == "offer-sent"

    # TODO Check the state of the holder after issuers call of send-offer
    # assert expected_agent_state(context.holder_url, "issue-credential", context.cred_thread_id, "offer-received")


@given('"{issuer}" offers and deletes a credential with data {credential_data}')
@when('"{issuer}" offers and deletes a credential with data {credential_data}')
def step_impl(context, issuer, credential_data):
    agent = context.active_agents[issuer]

    cred_attrs = read_credential_data(context.schema_name, credential_data)
    cred_exchange = aries_container_issue_credential(
        agent["agent"],
        context.cred_def_id,
        cred_attrs,
    )

    context.cred_attrs = cred_attrs
    context.cred_exchange = cred_exchange

    # delete this immediately, hopefully this is committed before the holder "accepts" it
    agent_container_DELETE(
        agent["agent"],
        f"/issue-credential-2.0/records/{cred_exchange['cred_ex_id']}",
    )

    # TODO Check the issuers State
    # assert resp_json["state"] == "offer-sent"

    # TODO Check the state of the holder after issuers call of send-offer
    # assert expected_agent_state(context.holder_url, "issue-credential", context.cred_thread_id, "abandoned")


@then('"{holder}" has the exchange abandoned')
def step_impl(context, holder):
    agent = context.active_agents[holder]

    # give time for the exchange to complete (as abandoned)
    async_sleep(5.0)
    resp = agent_container_GET(
        agent["agent"],
        "/issue-credential-2.0/records",
    )
    assert len(resp["results"]) == 1
    assert resp["results"][0]["cred_ex_record"]["state"] == "abandoned"


@when(
    '"{holder}" requests a credential with data {credential_data} from "{issuer}" it fails'
)
def step_impl(context, issuer, holder, credential_data):
    issuer_agent = context.active_agents[issuer]
    holder_agent = context.active_agents[holder]

    cred_attrs = read_credential_data(context.schema_name, credential_data)

    cred_preview = {
        "@type": "https://didcomm.org/issue-credential/2.0/credential-preview",
        "attributes": cred_attrs,
    }
    data = {
        "connection_id": holder_agent["agent"].agent.connection_id,
        "comment": f"Offer on cred def id {context.cred_def_id}",
        "auto_remove": False,
        "credential_preview": cred_preview,
        "filter": {"indy": {"cred_def_id": context.cred_def_id}},
    }

    try:
        resp = agent_container_POST(
            holder_agent["agent"],
            "/issue-credential-2.0/send-request",
            data,
        )
    except Exception as err:
        # this is not allowed, unprocessable
        assert err


@given('"{holder}" revokes the credential')
@when('"{holder}" revokes the credential')
@then('"{holder}" revokes the credential')
def step_impl(context, holder):
    agent = context.active_agents[holder]

    # get the required revocation info from the last credential exchange
    cred_exchange = context.cred_exchange

    cred_ex_id = (
        cred_exchange["cred_ex_id"]
        if "cred_ex_id" in cred_exchange
        else cred_exchange["cred_ex_record"]["cred_ex_id"]
    )

    cred_exchange = agent_container_GET(
        agent["agent"], "/issue-credential-2.0/records/" + cred_ex_id
    )
    context.cred_exchange = cred_exchange
    print("rev_reg_id:", cred_exchange["indy"]["rev_reg_id"])
    print("cred_rev_id:", cred_exchange["indy"]["cred_rev_id"])
    print("connection_id:", cred_exchange["cred_ex_record"]["connection_id"])

    # revoke the credential
    if is_anoncreds(agent):
        endpoint = "/anoncreds/revocation/revoke"
    else:
        endpoint = "/revocation/revoke"

    agent_container_POST(
        agent["agent"],
        endpoint,
        data={
            "rev_reg_id": cred_exchange["indy"]["rev_reg_id"],
            "cred_rev_id": cred_exchange["indy"]["cred_rev_id"],
            "publish": "Y",
            "connection_id": cred_exchange["cred_ex_record"]["connection_id"],
        },
    )

    # pause for a few seconds
    async_sleep(3.0)
    cred_exchange = agent_container_GET(
        agent["agent"], "/issue-credential-2.0/records/" + cred_ex_id
    )
    context.cred_exchange = cred_exchange
    print("cred_exchange:", json.dumps(cred_exchange))


@given('"{holder}" successfully revoked the credential')
@when('"{holder}" successfully revoked the credential')
@then('"{holder}" successfully revoked the credential')
def step_impl(context, holder):
    agent = context.active_agents[holder]

    # get the required revocation info from the last credential exchange
    cred_exchange = context.cred_exchange
    print("rev_reg_id:", cred_exchange["indy"]["rev_reg_id"])
    print("cred_rev_id:", cred_exchange["indy"]["cred_rev_id"])
    print("connection_id:", cred_exchange["cred_ex_record"]["connection_id"])

    # check wallet status
    wallet_revoked_creds = agent_container_GET(
        agent["agent"],
        "/revocation/registry/"
        + cred_exchange["indy"]["rev_reg_id"]
        + "/issued/details",
    )
    print("wallet_revoked_creds:", wallet_revoked_creds)
    matched = False
    for rec in wallet_revoked_creds:
        if rec["cred_rev_id"] == cred_exchange["indy"]["cred_rev_id"]:
            matched = True
            assert rec["state"] == "revoked"
    assert matched

    # check ledger status
    ledger_revoked_creds = agent_container_GET(
        agent["agent"],
        "/revocation/registry/"
        + cred_exchange["indy"]["rev_reg_id"]
        + "/issued/indy_recs",
    )
    print("ledger_revoked_creds:", ledger_revoked_creds)
    print(
        "assert",
        cred_exchange["indy"]["cred_rev_id"],
        "in",
        ledger_revoked_creds["rev_reg_delta"]["value"]["revoked"],
    )
    assert (
        int(cred_exchange["indy"]["cred_rev_id"])
        in ledger_revoked_creds["rev_reg_delta"]["value"]["revoked"]
    )


@given('"{holder}" attempts to revoke the credential')
@when('"{holder}" attempts to revoke the credential')
@then('"{holder}" attempts to revoke the credential')
def step_impl(context, holder):
    agent = context.active_agents[holder]

    # get the required revocation info from the last credential exchange
    cred_exchange = context.cred_exchange
    print("cred_exchange:", json.dumps(cred_exchange))

    cred_ex_id = (
        cred_exchange["cred_ex_id"]
        if "cred_ex_id" in cred_exchange
        else cred_exchange["cred_ex_record"]["cred_ex_id"]
    )

    cred_exchange = agent_container_GET(
        agent["agent"], "/issue-credential-2.0/records/" + cred_ex_id
    )
    context.cred_exchange = cred_exchange
    print("rev_reg_id:", cred_exchange["indy"]["rev_reg_id"])
    print("cred_rev_id:", cred_exchange["indy"]["cred_rev_id"])
    print("connection_id:", cred_exchange["cred_ex_record"]["connection_id"])

    # revoke the credential
    try:
        revoke_status = agent_container_POST(
            agent["agent"],
            "/revocation/revoke",
            data={
                "rev_reg_id": cred_exchange["indy"]["rev_reg_id"],
                "cred_rev_id": cred_exchange["indy"]["cred_rev_id"],
                "publish": "Y",
                "connection_id": cred_exchange["cred_ex_record"]["connection_id"],
            },
        )
    except:
        # ignore exceptions, we will check status later
        pass

    # pause for a second
    async_sleep(1.0)


@given('"{holder}" fails to publish the credential revocation')
@when('"{holder}" fails to publish the credential revocation')
@then('"{holder}" fails to publish the credential revocation')
def step_impl(context, holder):
    agent = context.active_agents[holder]

    # get the required revocation info from the last credential exchange
    cred_exchange = context.cred_exchange
    print("rev_reg_id:", cred_exchange["indy"]["rev_reg_id"])
    print("cred_rev_id:", cred_exchange["indy"]["cred_rev_id"])
    print("connection_id:", cred_exchange["cred_ex_record"]["connection_id"])

    # check wallet status
    wallet_revoked_creds = agent_container_GET(
        agent["agent"],
        "/revocation/registry/"
        + cred_exchange["indy"]["rev_reg_id"]
        + "/issued/details",
    )
    matched = False
    for rec in wallet_revoked_creds:
        if rec["cred_rev_id"] == cred_exchange["indy"]["cred_rev_id"]:
            matched = True
            assert rec["state"] == "revoked"
    assert matched

    # check ledger status
    ledger_revoked_creds = agent_container_GET(
        agent["agent"],
        "/revocation/registry/"
        + cred_exchange["indy"]["rev_reg_id"]
        + "/issued/indy_recs",
    )
    print("ledger_revoked_creds:", ledger_revoked_creds)
    assert (
        int(cred_exchange["indy"]["cred_rev_id"])
        not in ledger_revoked_creds["rev_reg_delta"]["value"]["revoked"]
    )


@when('"{holder}" has the credential issued')
@then('"{holder}" has the credential issued')
def step_impl(context, holder):
    agent = context.active_agents[holder]

    cred_def_id = context.cred_def_id
    cred_attrs = context.cred_attrs

    # check the received credential status (up to 10 seconds)
    for i in range(10):
        if aries_container_receive_credential(agent["agent"], cred_def_id, cred_attrs):
            return

    assert False


@given('"{issuer}" is ready to issue a json-ld credential for {schema_name}')
def step_impl(context, issuer, schema_name):
    # create a "did:key" to use as issuer
    agent = context.active_agents[issuer]

    data = {"method": DID_METHOD_KEY, "options": {"key_type": KEY_TYPE_BLS}}
    new_did = agent_container_POST(
        agent["agent"],
        "/wallet/did/create",
        data=data,
    )
    agent["agent"].agent.did = new_did["result"]["did"]
    # TODO test for goodness
    pass


@given('"{holder}" is ready to receive a json-ld credential')
def step_impl(context, holder):
    # create a "did:key" to use as holder identity
    agent = context.active_agents[holder]

    data = {"method": DID_METHOD_KEY, "options": {"key_type": KEY_TYPE_BLS}}
    new_did = agent_container_POST(
        agent["agent"],
        "/wallet/did/create",
        data=data,
    )
    agent["agent"].agent.did = new_did["result"]["did"]

    # TODO test for goodness
    pass


@when('"{issuer}" offers "{holder}" a json-ld credential with data {credential_data}')
def step_impl(context, issuer, holder, credential_data):
    # initiate a cred exchange with a json-ld credential
    agent = context.active_agents[issuer]
    holder_agent = context.active_agents[holder]

    offer_request = {
        "connection_id": agent["agent"].agent.connection_id,
        "filter": {
            "ld_proof": {
                "credential": {
                    "@context": [
                        "https://www.w3.org/2018/credentials/v1",
                        "https://w3id.org/citizenship/v1",
                    ],
                    "type": [
                        "VerifiableCredential",
                        "PermanentResident",
                    ],
                    "id": "https://credential.example.com/residents/1234567890",
                    "issuer": agent["agent"].agent.did,
                    "issuanceDate": "2020-01-01T12:00:00Z",
                    "credentialSubject": {
                        "type": ["PermanentResident"],
                        # let the holder set this
                        # "id": holder_agent["agent"].agent.did,
                        "givenName": "ALICE",
                        "familyName": "SMITH",
                        "gender": "Female",
                        "birthCountry": "Bahamas",
                        "birthDate": "1958-07-17",
                    },
                },
                "options": {"proofType": SIG_TYPE_BLS},
            }
        },
    }

    agent_container_POST(
        agent["agent"],
        "/issue-credential-2.0/send-offer",
        offer_request,
    )

    # TODO test for goodness
    pass


@when(
    '"{issuer}" offers and deletes "{holder}" a json-ld credential with data {credential_data}'
)
def step_impl(context, issuer, holder, credential_data):
    # initiate a cred exchange with a json-ld credential
    agent = context.active_agents[issuer]
    holder_agent = context.active_agents[holder]

    # holder and issuer have no records...
    resp = agent_container_GET(
        agent["agent"],
        "/issue-credential-2.0/records",
    )
    assert len(resp["results"]) == 0

    resp = agent_container_GET(
        holder_agent["agent"],
        "/issue-credential-2.0/records",
    )
    assert len(resp["results"]) == 0

    offer_request = {
        "connection_id": agent["agent"].agent.connection_id,
        "filter": {
            "ld_proof": {
                "credential": {
                    "@context": [
                        "https://www.w3.org/2018/credentials/v1",
                        "https://w3id.org/citizenship/v1",
                    ],
                    "type": [
                        "VerifiableCredential",
                        "PermanentResident",
                    ],
                    "id": "https://credential.example.com/residents/1234567890",
                    "issuer": agent["agent"].agent.did,
                    "issuanceDate": "2020-01-01T12:00:00Z",
                    "credentialSubject": {
                        "type": ["PermanentResident"],
                        # let the holder set this
                        # "id": holder_agent["agent"].agent.did,
                        "givenName": "ALICE",
                        "familyName": "SMITH",
                        "gender": "Female",
                        "birthCountry": "Bahamas",
                        "birthDate": "1958-07-17",
                    },
                },
                "options": {"proofType": SIG_TYPE_BLS},
            }
        },
    }

    resp = agent_container_POST(
        agent["agent"],
        "/issue-credential-2.0/send-offer",
        offer_request,
    )
    cred_ex_id = resp["cred_ex_id"]

    # issuer has one record
    resp = agent_container_GET(
        agent["agent"],
        "/issue-credential-2.0/records",
    )
    assert len(resp["results"]) == 1

    # delete this immediately, hopefully this is committed before the holder "accepts" it
    # for json-ld this should turn into a request from the holder
    resp = agent_container_DELETE(
        agent["agent"],
        f"/issue-credential-2.0/records/{cred_ex_id}",
    )

    # now issuer has no records
    resp = agent_container_GET(
        agent["agent"],
        "/issue-credential-2.0/records",
    )
    assert len(resp["results"]) == 0


@given('"{issuer}" has the exchange completed')
@then('"{issuer}" has the exchange completed')
def step_impl(context, issuer):
    agent = context.active_agents[issuer]

    # new exchange is initiated by the holder, so issuer has one record
    async_sleep(5.0)
    resp = agent_container_GET(
        agent["agent"],
        "/issue-credential-2.0/records",
    )
    assert len(resp["results"]) == 1
    assert resp["results"][0]["cred_ex_record"]["state"] == "done"


@when(
    '"{holder}" requests a json-ld credential with data {credential_data} from "{issuer}"'
)
def step_impl(context, issuer, holder, credential_data):
    issuer_agent = context.active_agents[issuer]
    holder_agent = context.active_agents[holder]
    data = {
        "auto_remove": False,
        "comment": "I would like this credential please",
        "connection_id": holder_agent["agent"].agent.connection_id,
        "filter": {
            "ld_proof": {
                "credential": {
                    "@context": [
                        "https://www.w3.org/2018/credentials/v1",
                        "https://w3id.org/citizenship/v1",
                    ],
                    "type": [
                        "VerifiableCredential",
                        "PermanentResident",
                    ],
                    "id": "https://credential.example.com/residents/1234567890",
                    "issuer": issuer_agent["agent"].agent.did,
                    "issuanceDate": "2020-01-01T12:00:00Z",
                    "credentialSubject": {
                        "type": ["PermanentResident"],
                        "id": holder_agent["agent"].agent.did,
                        "givenName": "ALICE",
                        "familyName": "SMITH",
                        "gender": "Female",
                        "birthCountry": "Bahamas",
                        "birthDate": "1958-07-17",
                    },
                },
                "options": {"proofType": SIG_TYPE_BLS},
            }
        },
    }

    resp = agent_container_POST(
        holder_agent["agent"],
        "/issue-credential-2.0/send-request",
        data,
    )
    assert resp["state"] == "request-sent"


@when(
    '"{issuer}" offers "{holder}" an anoncreds credential with data {credential_data}'
)
def step_impl(context, issuer, holder, credential_data):
    # initiate a cred exchange with an anoncreds credential
    agent = context.active_agents[issuer]
    holder_agent = context.active_agents[holder]

    offer_request = {
        "connection_id": agent["agent"].agent.connection_id,
        "filter": {
            "ld_proof": {
                "credential": {
                    "@context": [
                        "https://www.w3.org/2018/credentials/v1",
                        "https://w3id.org/citizenship/v1",
                    ],
                    "type": [
                        "VerifiableCredential",
                        "PermanentResident",
                    ],
                    "id": "https://credential.example.com/residents/1234567890",
                    "issuer": agent["agent"].agent.did,
                    "issuanceDate": "2020-01-01T12:00:00Z",
                    "credentialSubject": {
                        "type": ["PermanentResident"],
                        # let the holder set this
                        # "id": holder_agent["agent"].agent.did,
                        "givenName": "ALICE",
                        "familyName": "SMITH",
                        "gender": "Female",
                        "birthCountry": "Bahamas",
                        "birthDate": "1958-07-17",
                    },
                },
                "options": {"proofType": SIG_TYPE_BLS},
            }
        },
    }

    agent_container_POST(
        agent["agent"],
        "/issue-credential-2.0/send-offer",
        offer_request,
    )

    # TODO test for goodness
    pass


@then('"{holder}" has the json-ld credential issued')
def step_impl(context, holder):
    # verify the holder has a w3c credential
    agent = context.active_agents[holder]

    for i in range(10):
        async_sleep(1.0)
        w3c_creds = agent_container_POST(
            agent["agent"],
            "/credentials/w3c",
            {},
        )
        if 0 < len(w3c_creds["results"]):
            return

    assert False


@given(
    '"{holder}" has an issued json-ld {schema_name} credential {credential_data} from "{issuer}"'
)
def step_impl(context, holder, schema_name, credential_data, issuer):
    context.execute_steps(
        '''
        Given "'''
        + issuer
        + """" is ready to issue a json-ld credential for """
        + schema_name
        + '''
        And "'''
        + holder
        + """" is ready to receive a json-ld credential """
        + '''
        When "'''
        + issuer
        + '''" offers "'''
        + holder
        + """" a json-ld credential with data """
        + credential_data
        + '''
        Then "'''
        + holder
        + """" has the json-ld credential issued
    """
    )


@given(
    '"{holder}" has an issued {schema_name} credential {credential_data} from "{issuer}"'
)
def step_impl(context, holder, schema_name, credential_data, issuer):
    context.execute_steps(
        '''
        Given "'''
        + issuer
        + """" is ready to issue a credential for """
        + schema_name
        + '''
        When "'''
        + issuer
        + """" offers a credential with data """
        + credential_data
        + '''
        Then "'''
        + holder
        + """" has the credential issued
    """
    )


@given(
    '"{holder}" has another issued {schema_name} credential {credential_data} from "{issuer}"'
)
def step_impl(context, holder, schema_name, credential_data, issuer):
    context.execute_steps(
        # TODO possibly check that the requested schema is "active" (if there are multiple schemas)
        '''
        When "'''
        + issuer
        + """" offers a credential with data """
        + credential_data
        + '''
        Then "'''
        + holder
        + """" has the credential issued
    """
    )
