import time

from bdd_support.agent_backchannel_client import (
    agent_container_GET,
    agent_container_PATCH,
    agent_container_POST,
    agent_container_PUT,
    agent_container_register_did,
    aries_container_fetch_cred_def,
    aries_container_fetch_cred_defs,
    aries_container_fetch_schemas,
    async_sleep,
    read_json_data,
    read_schema_data,
)
from behave import given, then, when


def is_anoncreds(agent):
    return agent["agent"].wallet_type == "askar-anoncreds"


# This step is defined in another feature file
# Given "Acme" and "Bob" have an existing connection


@when('"{agent_name}" has a DID with role "{did_role}"')
def step_impl(context, agent_name, did_role):
    agent = context.active_agents[agent_name]

    # create a new DID in the current wallet
    created_did = agent_container_POST(agent["agent"], "/wallet/did/create")

    # publish to the ledger with did_role
    agent_container_register_did(
        agent["agent"],
        created_did["result"]["did"],
        created_did["result"]["verkey"],
        "ENDORSER" if did_role == "ENDORSER" else "",
    )

    # make the new did the wallet's public did
    retries = 5
    for retry in range(retries):
        async_sleep(1.0)
        published_did = agent_container_POST(
            agent["agent"],
            "/wallet/did/public",
            params={"did": created_did["result"]["did"]},
            raise_error=retries - 1 == retry,
        )
        if "result" in published_did or "txn" in published_did:
            break

    if "result" in published_did:
        # published right away!
        pass
    elif "txn" in published_did:
        # we are an author and need to go through the endorser process
        # assume everything works!
        async_sleep(3.0)

    if "public_dids" not in context:
        context.public_dids = {}
    context.public_dids[did_role] = created_did["result"]["did"]


@when('"{agent_name}" connection has job role "{connection_job_role}"')
def step_impl(context, agent_name, connection_job_role):
    agent = context.active_agents[agent_name]

    # current connection_id for the selected agent
    connection_id = agent["agent"].agent.connection_id

    # set role for agent's connection
    print("Updating role for connection:", connection_id, connection_job_role)
    updated_connection = agent_container_POST(
        agent["agent"],
        "/transactions/" + connection_id + "/set-endorser-role",
        params={"transaction_my_job": connection_job_role},
    )

    # assert goodness
    assert updated_connection["transaction_my_job"] == connection_job_role
    async_sleep(1.0)


@when('"{agent_name}" connection sets endorser info')
def step_impl(context, agent_name):
    agent = context.active_agents[agent_name]

    # current connection_id for the selected agent
    connection_id = agent["agent"].agent.connection_id
    endorser_did = context.public_dids["ENDORSER"]

    updated_connection = agent_container_POST(
        agent["agent"],
        "/transactions/" + connection_id + "/set-endorser-info",
        params={"endorser_did": endorser_did},
    )

    # assert goodness
    assert updated_connection["endorser_did"] == endorser_did
    async_sleep(1.0)


@when('"{agent_name}" authors a schema transaction with {schema_name}')
def step_impl(context, agent_name, schema_name):
    agent = context.active_agents[agent_name]

    schema_info = read_schema_data(schema_name)
    connection_id = agent["agent"].agent.connection_id
    if "txn_ids" not in context:
        context.txn_ids = {}

    if not is_anoncreds(agent):
        created_txn = agent_container_POST(
            agent["agent"],
            "/schemas",
            data=schema_info["schema"],
            params={
                "conn_id": connection_id,
                "create_transaction_for_endorser": "true",
            },
        )
        # assert goodness
        if agent["agent"].endorser_role and agent["agent"].endorser_role == "author":
            assert created_txn["txn"]["state"] == "request_sent"
        else:
            assert created_txn["txn"]["state"] == "transaction_created"

        context.txn_ids["AUTHOR"] = created_txn["txn"]["transaction_id"]
    else:
        schema_info["schema"]["issuerId"] = context.public_dids["AUTHOR"]
        schema_info["options"]["create_transaction_for_endorser"] = True
        schema_info["options"]["endorser_connection_id"] = connection_id
        created_txn = agent_container_POST(
            agent["agent"],
            "/anoncreds/schema",
            data=schema_info,
        )

        if agent["agent"].endorser_role and agent["agent"].endorser_role == "author":
            assert (
                created_txn["registration_metadata"]["txn"]["state"] == "request_sent"
            )
            assert created_txn["schema_state"]["state"] == "wait"
            assert created_txn["job_id"] is not None

        context.txn_ids["AUTHOR"] = created_txn["registration_metadata"]["txn"][
            "transaction_id"
        ]


@when('"{agent_name}" requests endorsement for the transaction')
def step_impl(context, agent_name):
    agent = context.active_agents[agent_name]

    async_sleep(1.0)
    txn_id = context.txn_ids["AUTHOR"]

    data = read_json_data("expires_time.json")

    requested_txn = agent_container_POST(
        agent["agent"],
        "/transactions/create-request",
        data=data,
        params={"tran_id": txn_id},
    )

    # assert goodness
    assert requested_txn["state"] == "request_sent"


@when('"{agent_name}" endorses the transaction')
def step_impl(context, agent_name):
    agent = context.active_agents[agent_name]

    # find the transaction with state "request_received"
    txns = {"results": []}
    i = 5
    while 0 == len(txns["results"]) and i > 0:
        async_sleep(1.0)
        txns_queued = agent_container_GET(agent["agent"], "/transactions")
        for j in range(len(txns_queued["results"])):
            if txns_queued["results"][j]["state"] == "request_received":
                txns["results"].append(txns_queued["results"][j])
        i = i - 1
    requested_txn = txns["results"][0]
    assert requested_txn["state"] == "request_received"
    txn_id = requested_txn["transaction_id"]

    endorsed_txn = agent_container_POST(
        agent["agent"], "/transactions/" + txn_id + "/endorse"
    )

    assert endorsed_txn["state"] == "transaction_endorsed"


@when('"{agent_name}" can write the transaction to the ledger')
@then('"{agent_name}" can write the transaction to the ledger')
def step_impl(context, agent_name):
    agent = context.active_agents[agent_name]
    txn_id = context.txn_ids["AUTHOR"]

    async_sleep(1.0)
    txn = agent_container_GET(agent["agent"], "/transactions/" + txn_id)
    requested_txn = txn
    assert requested_txn["state"] == "transaction_endorsed"

    written_txn = agent_container_POST(
        agent["agent"], "/transactions/" + txn_id + "/write"
    )

    assert written_txn["state"] == "transaction_acked"


@given('"{agent_name}" has written the schema {schema_name} to the ledger')
@when('"{agent_name}" has written the schema {schema_name} to the ledger')
@then('"{agent_name}" has written the schema {schema_name} to the ledger')
def step_impl(context, agent_name, schema_name):
    agent = context.active_agents[agent_name]

    schemas = {"schema_ids": []}
    i = 5
    while 0 == len(schemas["schema_ids"]) and i > 0:
        async_sleep(1.0)
        schemas = aries_container_fetch_schemas(agent["agent"])
        i = i - 1
    assert len(schemas["schema_ids"]) == 1

    schema_id = schemas["schema_ids"][0]
    if not is_anoncreds(agent):
        agent_container_GET(agent["agent"], "/schemas/" + schema_id)
    else:
        agent_container_GET(agent["agent"], "/anoncreds/schema/" + schema_id)

    context.schema_name = schema_name

    # TODO assert goodness


@when('"{agent_name}" authors a credential definition transaction with {schema_name}')
@then('"{agent_name}" authors a credential definition transaction with {schema_name}')
def step_impl(context, agent_name, schema_name):
    agent = context.active_agents[agent_name]

    connection_id = agent["agent"].agent.connection_id

    # TODO for now assume there is a single schema; should find the schema based on the supplied name
    schemas = aries_container_fetch_schemas(agent["agent"])
    assert len(schemas["schema_ids"]) == 1

    schema_id = schemas["schema_ids"][0]

    if not is_anoncreds(agent):
        created_txn = agent_container_POST(
            agent["agent"],
            "/credential-definitions",
            data={
                "schema_id": schema_id,
                "tag": "test_cred_def_with_endorsement",
                "support_revocation": True,
                "revocation_registry_size": 1000,
            },
            params={
                "conn_id": connection_id,
                "create_transaction_for_endorser": "true",
            },
        )
    else:
        anoncreds_cred_def_result = agent_container_POST(
            agent["agent"],
            "/anoncreds/credential-definition",
            data={
                "credential_definition": {
                    "issuerId": schema_id.split(":")[0],
                    "schemaId": schema_id,
                    "tag": "test_cred_def_with_endorsement",
                },
                "options": {
                    "endorser_connection_id": connection_id,
                    "create_transaction_for_endorser": True,
                    "support_revocation": True,
                    "revocation_registry_size": 1000,
                },
            },
        )
        created_txn = anoncreds_cred_def_result["registration_metadata"]

    # assert goodness
    if agent["agent"].endorser_role and agent["agent"].endorser_role == "author":
        assert created_txn["txn"]["state"] == "request_sent"
    else:
        assert created_txn["txn"]["state"] == "transaction_created"
    if "txn_ids" not in context:
        context.txn_ids = {}
    context.txn_ids["AUTHOR"] = created_txn["txn"]["transaction_id"]


@given(
    '"{agent_name}" has written the credential definition for {schema_name} to the ledger'
)
@when(
    '"{agent_name}" has written the credential definition for {schema_name} to the ledger'
)
@then(
    '"{agent_name}" has written the credential definition for {schema_name} to the ledger'
)
def step_impl(context, agent_name, schema_name):
    agent = context.active_agents[agent_name]

    schema_info = read_schema_data(schema_name)

    cred_defs = {"credential_definition_ids": []}
    i = 5
    while 0 == len(cred_defs["credential_definition_ids"]) and i > 0:
        async_sleep(1.0)
        cred_defs = aries_container_fetch_cred_defs(agent["agent"])
        i = i - 1
    assert len(cred_defs["credential_definition_ids"]) == 1

    cred_def_id = cred_defs["credential_definition_ids"][0]
    cred_def = aries_container_fetch_cred_def(agent["agent"], cred_def_id)

    context.cred_def_id = cred_def_id

    # TODO assert goodness


@when(
    '"{agent_name}" authors a revocation registry definition transaction for the credential definition matching {schema_name}'
)
@then(
    '"{agent_name}" authors a revocation registry definition transaction for the credential definition matching {schema_name}'
)
def step_impl(context, agent_name, schema_name):
    agent = context.active_agents[agent_name]

    connection_id = agent["agent"].agent.connection_id

    if not is_anoncreds(agent):
        # generate revocation registry transaction
        rev_reg = agent_container_POST(
            agent["agent"],
            "/revocation/create-registry",
            data={
                "credential_definition_id": context.cred_def_id,
                "max_cred_num": 1000,
            },
            params={},
        )
        rev_reg_id = rev_reg["result"]["revoc_reg_id"]
        assert rev_reg_id is not None

        # update revocation registry
        agent_container_PATCH(
            agent["agent"],
            f"/revocation/registry/{rev_reg_id}",
            data={
                "tails_public_uri": f"http://host.docker.internal:6543/revocation/registry/{rev_reg_id}/tails-file"
            },
            params={},
        )

        # create rev_reg transaction
        created_txn = agent_container_POST(
            agent["agent"],
            f"/revocation/registry/{rev_reg_id}/definition",
            data={},
            params={
                "conn_id": connection_id,
                "create_transaction_for_endorser": "true",
            },
        )
    else:
        # generate revocation registry transaction
        anoncreds_rev_reg_result = agent_container_POST(
            agent["agent"],
            "/anoncreds/revocation-registry-definition",
            data={
                "revocation_registry_definition": {
                    "credDefId": context.cred_def_id,
                    "issuerId": context.cred_def_id.split(":")[0],
                    "maxCredNum": 666,
                    "tag": "default",
                },
                "options": {
                    "endorser_connection_id": connection_id,
                    "create_transaction_for_endorser": True,
                },
            },
            params={},
        )
        created_txn = anoncreds_rev_reg_result["registration_metadata"]

    assert created_txn["txn"]["state"] == "transaction_created"
    if "txn_ids" not in context:
        context.txn_ids = {}
    context.txn_ids["AUTHOR"] = created_txn["txn"]["transaction_id"]


@given('"{agent_name}" has written the revocation registry definition to the ledger')
@when('"{agent_name}" has written the revocation registry definition to the ledger')
@then('"{agent_name}" has written the revocation registry definition to the ledger')
def step_impl(context, agent_name):
    agent = context.active_agents[agent_name]

    if not is_anoncreds(agent):
        endpoint = "/revocation/registries/created"
    else:
        endpoint = "/anoncreds/revocation/registries"

    rev_regs = {"rev_reg_ids": []}
    i = 5
    while 0 == len(rev_regs["rev_reg_ids"]) and i > 0:
        async_sleep(1.0)
        rev_regs = agent_container_GET(
            agent["agent"],
            endpoint,
            params={
                "cred_def_id": context.cred_def_id,
            },
        )
        # anoncreds returns a job_id here immediately
        # check id is a rev_reg_def_id or reset list
        if [x for x in rev_regs["rev_reg_ids"] if str(x).count(":") > 0].__len__() == 0:
            rev_regs = {"rev_reg_ids": []}
        i = i - 1
    assert len(rev_regs["rev_reg_ids"]) >= 1

    rev_reg_id = [x for x in rev_regs["rev_reg_ids"] if str(x).count(":") > 0][0]

    context.rev_reg_id = rev_reg_id


@when(
    '"{agent_name}" has activated the tails file, and uploaded it to the tails server'
)
@then(
    '"{agent_name}" has has activated the tails file, and uploaded it to the tails server'
)
def step_impl(context, agent_name):
    agent = context.active_agents[agent_name]

    if not is_anoncreds(agent):
        # activate rev_reg
        agent_container_PATCH(
            agent["agent"],
            f"/revocation/registry/{context.rev_reg_id}/set-state",
            data={},
            params={"state": "active"},
        )

        # upload rev_reg
        agent_container_PUT(
            agent["agent"],
            f"/revocation/registry/{context.rev_reg_id}/tails-file",
            data={},
            params={},
        )
    else:
        # activate rev_reg
        agent_container_PUT(
            agent["agent"],
            f"/anoncreds/registry/{context.rev_reg_id}/active",
            data={},
            params={},
        )

        # upload rev_reg
        agent_container_PUT(
            agent["agent"],
            f"/anoncreds/registry/{context.rev_reg_id}/tails-file",
            data={},
            params={},
        )


@given(
    '"{agent_name}" has written the revocation registry entry transaction to the ledger'
)
@when(
    '"{agent_name}" has written the revocation registry entry transaction to the ledger'
)
@then(
    '"{agent_name}" has written the revocation registry entry transaction to the ledger'
)
def step_impl(context, agent_name):
    agent = context.active_agents[agent_name]

    if not is_anoncreds(agent):
        endpoint = "/revocation/registry/"
    else:
        endpoint = "/anoncreds/revocation/registry/"

    # a registry is promoted to active when its initial entry is sent
    i = 5

    async_sleep(2.0)

    while i > 0:
        async_sleep(1.0)
        if context.rev_reg_id is not None:
            reg_info = agent_container_GET(
                agent["agent"],
                f"{endpoint}{context.rev_reg_id}",
            )
            state = reg_info["result"]["state"]
            if state in ["active", "finished"]:
                return
            i = i - 1

    assert False


@when(
    '"{agent_name}" authors a revocation registry entry transaction for the credential definition matching {schema_name}'
)
@then(
    '"{agent_name}" authors a revocation registry entry transaction for the credential definition matching {schema_name}'
)
def step_impl(context, agent_name, schema_name):
    agent = context.active_agents[agent_name]

    connection_id = agent["agent"].agent.connection_id

    # generate revocation registry entry transaction
    # create rev_reg transaction
    if not is_anoncreds(agent):
        created_txn = agent_container_POST(
            agent["agent"],
            f"/revocation/registry/{context.rev_reg_id}/entry",
            data={},
            params={
                "conn_id": connection_id,
                "create_transaction_for_endorser": "true",
            },
        )
    else:
        anoncreds_result = agent_container_POST(
            agent["agent"],
            "/anoncreds/revocation-list",
            data={
                "rev_reg_def_id": context.rev_reg_id,
                "options": {
                    "create_transaction_for_endorser": "true",
                    "endorser_connection_id": connection_id,
                },
            },
            params={},
        )
        created_txn = anoncreds_result["registration_metadata"]

    assert created_txn["txn"]["state"] == "transaction_created"
    if "txn_ids" not in context:
        context.txn_ids = {}
    context.txn_ids["AUTHOR"] = created_txn["txn"]["transaction_id"]


@when(
    '"{holder}" has an issued {schema_name} credential {credential_data} from "{issuer}"'
)
@then(
    '"{holder}" has an issued {schema_name} credential {credential_data} from "{issuer}"'
)
def step_impl(context, holder, schema_name, credential_data, issuer):
    context.execute_steps(
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


@given('"{agent_name}" revokes the credential without publishing the entry')
@when('"{agent_name}" revokes the credential without publishing the entry')
@then('"{agent_name}" revokes the credential without publishing the entry')
def step_impl(context, agent_name):
    agent = context.active_agents[agent_name]

    if not is_anoncreds(agent):
        endpoint = "/revocation/revoke"
    else:
        endpoint = "/anoncreds/revocation/revoke"

    # get the required revocation info from the last credential exchange
    cred_exchange = context.cred_exchange

    cred_exchange = agent_container_GET(
        agent["agent"], "/issue-credential-2.0/records/" + cred_exchange["cred_ex_id"]
    )
    context.cred_exchange = cred_exchange

    agent_container_POST(
        agent["agent"],
        endpoint,
        data={
            "cred_rev_id": cred_exchange["indy"]["cred_rev_id"],
            "publish": False,
            "rev_reg_id": cred_exchange["indy"]["rev_reg_id"],
            "connection_id": cred_exchange["cred_ex_record"]["connection_id"],
        },
    )

    # pause for a few seconds
    async_sleep(3.0)


@when(
    '"{agent_name}" revokes the credential without publishing the entry with txn endorsement'
)
@then(
    '"{agent_name}" revokes the credential without publishing the entry with txn endorsement'
)
def step_impl(context, agent_name):
    agent = context.active_agents[agent_name]

    # get the required revocation info from the last credential exchange
    cred_exchange = context.cred_exchange

    cred_exchange = agent_container_GET(
        agent["agent"], "/issue-credential-2.0/records/" + cred_exchange["cred_ex_id"]
    )
    context.cred_exchange = cred_exchange
    connection_id = agent["agent"].agent.connection_id

    # revoke the credential
    if not is_anoncreds(agent):
        data = {
            "rev_reg_id": cred_exchange["indy"]["rev_reg_id"],
            "cred_rev_id": cred_exchange["indy"]["cred_rev_id"],
            "publish": False,
            "connection_id": cred_exchange["cred_ex_record"]["connection_id"],
        }
        params = {
            "conn_id": connection_id,
            "create_transaction_for_endorser": "true",
        }
        endpoint = "/revocation/revoke"
    else:
        data = {
            "cred_rev_id": cred_exchange["indy"]["cred_rev_id"],
            "publish": False,
            "rev_reg_id": cred_exchange["indy"]["rev_reg_id"],
            "connection_id": cred_exchange["cred_ex_record"]["connection_id"],
            "options": {
                "endorser_connection_id": connection_id,
                "create_transaction_for_endorser": "true",
            },
        }
        params = {}
        endpoint = "/anoncreds/revocation/revoke"

    agent_container_POST(
        agent["agent"],
        endpoint,
        data=data,
        params=params,
    )

    # pause for a few seconds
    async_sleep(3.0)


@given('"{agent_name}" authors a revocation registry entry publishing transaction')
@when('"{agent_name}" authors a revocation registry entry publishing transaction')
@then('"{agent_name}" authors a revocation registry entry publishing transaction')
def step_impl(context, agent_name):
    agent = context.active_agents[agent_name]

    if not is_anoncreds(agent):
        endpoint = "/revocation/publish-revocations"
    else:
        endpoint = "/anoncreds/revocation/publish-revocations"

    # create rev_reg entry transaction
    created_rev_reg = agent_container_POST(
        agent["agent"],
        endpoint,
        data={
            "rrid2crid": {
                context.cred_exchange["indy"]["rev_reg_id"]: [
                    context.cred_exchange["indy"]["cred_rev_id"]
                ]
            }
        },
        params={},
    )
    # check that rev reg entry was written
    assert "rrid2crid" in created_rev_reg


@when(
    '"{agent_name}" authors a revocation registry entry publishing transaction with txn endorsement'
)
@then(
    '"{agent_name}" authors a revocation registry entry publishing transaction with txn endorsement'
)
def step_impl(context, agent_name):
    agent = context.active_agents[agent_name]

    connection_id = agent["agent"].agent.connection_id

    # create rev_reg entry transaction
    if not is_anoncreds(agent):
        data = {
            "rrid2crid": {
                context.cred_exchange["indy"]["rev_reg_id"]: [
                    context.cred_exchange["indy"]["cred_rev_id"]
                ]
            }
        }
        params = {
            "conn_id": connection_id,
            "create_transaction_for_endorser": "true",
        }
        endpoint = "/revocation/publish-revocations"
    else:
        data = {
            "rrid2crid": {
                context.cred_exchange["indy"]["rev_reg_id"]: [
                    context.cred_exchange["indy"]["cred_rev_id"]
                ]
            },
            "options": {
                "endorser_connection_id": connection_id,
                "create_transaction_for_endorser": "true",
            },
        }
        params = {}
        endpoint = "/anoncreds/revocation/publish-revocations"

    agent_container_POST(
        agent["agent"],
        endpoint,
        data=data,
        params=params,
    )

    # pause for a few seconds
    async_sleep(3.0)


@then('"{holder_name}" can verify the credential from "{issuer_name}" was revoked')
def step_impl(context, holder_name, issuer_name):
    agent = context.active_agents[holder_name]

    # sleep here to allow the auto-endorser process to complete
    async_sleep(2.0)

    # fetch the credential - there only is one in the wallet
    cred_list = agent_container_GET(
        agent["agent"],
        "/credentials",
        params={},
    )
    cred_id = cred_list["results"][0]["referent"]

    revoc_status_bool = False
    counter = 0
    while not revoc_status_bool and counter < 3:
        # check revocation status for the credential
        revocation_status = agent_container_GET(
            agent["agent"],
            f"/credential/revoked/{cred_id}",
            params={"to": int(time.time())},
        )
        revoc_status_bool = revocation_status["revoked"]
        counter = counter + 1
        async_sleep(1.0)
    assert revoc_status_bool is True


@given(
    'Without endorser, "{agent_name}" authors a schema transaction with {schema_name}'
)
def step_impl(context, agent_name, schema_name):
    agent = context.active_agents[agent_name]

    schema_info = read_schema_data(schema_name)
    connection_id = agent["agent"].agent.connection_id

    if not is_anoncreds(agent):
        schema_id = agent_container_POST(
            agent["agent"],
            "/schemas",
            data=schema_info["schema"],
            params={
                "conn_id": connection_id,
                "create_transaction_for_endorser": "false",
            },
        )["schema_id"]
    else:
        schema_id = agent_container_POST(
            agent["agent"],
            "/anoncreds/schema",
            data={
                "schema": {
                    "name": schema_info["schema"]["schema_name"],
                    "version": schema_info["schema"]["schema_version"],
                    "attrNames": schema_info["schema"]["attributes"],
                    "issuerId": agent["agent"].agent.did,
                },
                "options": {},
            },
        )["schema_state"]["schema_id"]

    # assert goodness
    assert schema_id
    context.schema_id = schema_id


@given(
    'Without endorser, "{agent_name}" authors a credential definition transaction with {schema_name}'
)
def step_impl(context, agent_name, schema_name):
    agent = context.active_agents[agent_name]

    connection_id = agent["agent"].agent.connection_id

    if not is_anoncreds(agent):
        # TODO for now assume there is a single schema; should find the schema based on the supplied name
        schemas = agent_container_GET(agent["agent"], "/schemas/created")
        assert len(schemas["schema_ids"]) == 1

        credential_definition_id = agent_container_POST(
            agent["agent"],
            "/credential-definitions",
            data={
                "schema_id": schemas["schema_ids"][0],
                "tag": "test_cred_def_with_endorsement",
                "support_revocation": True,
                "revocation_registry_size": 1000,
            },
            params={
                "conn_id": connection_id,
                "create_transaction_for_endorser": "false",
            },
        )
    else:
        schemas = agent_container_GET(agent["agent"], "/anoncreds/schemas")
        assert len(schemas["schema_ids"]) == 1

        credential_definition_id = agent_container_POST(
            agent["agent"],
            "/anoncreds/credential-definition",
            data={
                "credential_definition": {
                    "schemaId": schemas["schema_ids"][0],
                    "issuerId": agent["agent"].agent.did,
                    "tag": "test_cred_def_with_endorsement",
                },
                "options": {
                    "support_revocation": True,
                    "revocation_registry_size": 1000,
                },
            },
        )["credential_definition_state"]["credential_definition_id"]

    # assert goodness
    assert credential_definition_id
    context.cred_def_id = credential_definition_id


@given(
    'Without endorser, "{agent_name}" authors a revocation registry definition transaction for the credential definition matching {schema_name}'
)
def step_impl(context, agent_name, schema_name):
    agent = context.active_agents[agent_name]

    connection_id = agent["agent"].agent.connection_id

    if not is_anoncreds(agent):
        # generate revocation registry transaction
        rev_reg = agent_container_POST(
            agent["agent"],
            "/revocation/create-registry",
            data={
                "credential_definition_id": context.cred_def_id,
                "max_cred_num": 1000,
            },
            params={},
        )
        rev_reg_id = rev_reg["result"]["revoc_reg_id"]
        assert rev_reg_id is not None

        # update revocation registry
        agent_container_PATCH(
            agent["agent"],
            f"/revocation/registry/{rev_reg_id}",
            data={
                "tails_public_uri": f"http://host.docker.internal:6543/revocation/registry/{rev_reg_id}/tails-file"
            },
            params={},
        )

        # create rev_reg def
        created_txn = agent_container_POST(
            agent["agent"],
            f"/revocation/registry/{rev_reg_id}/definition",
            data={},
            params={
                "conn_id": connection_id,
                "create_transaction_for_endorser": "false",
            },
        )
        assert created_txn

    else:
        # generate revocation registry transaction
        rev_reg_id = agent_container_POST(
            agent["agent"],
            "/anoncreds/revocation-registry-definition",
            data={
                "revocation_registry_definition": {
                    "credDefId": context.cred_def_id,
                    "issuerId": agent["agent"].agent.did,
                    "maxCredNum": 1000,
                    "tag": "default",
                },
                "options": {},
            },
            params={},
        )["revocation_registry_definition_state"]["revocation_registry_definition_id"]
        assert rev_reg_id is not None

    context.rev_reg_id = rev_reg_id


@given(
    'Without endorser, "{agent_name}" has written the revocation registry definition to the ledger'
)
def step_impl(context, agent_name):
    agent = context.active_agents[agent_name]

    if not is_anoncreds(agent):
        endpoint = "/revocation/registries/created"
    else:
        endpoint = "/anoncreds/revocation/registries"

    rev_regs = {"rev_reg_ids": []}
    i = 5
    while 0 == len(rev_regs["rev_reg_ids"]) and i > 0:
        async_sleep(1.0)
        rev_regs = agent_container_GET(
            agent["agent"],
            endpoint,
            params={
                "cred_def_id": context.cred_def_id,
            },
        )
        i = i - 1

    assert context.rev_reg_id in rev_regs["rev_reg_ids"]


@given(
    'Without endorser, "{agent_name}" authors a revocation registry entry transaction for the credential definition matching {schema_name}'
)
def step_impl(context, agent_name, schema_name):
    agent = context.active_agents[agent_name]

    connection_id = agent["agent"].agent.connection_id

    # generate revocation registry entry transaction
    # create rev_reg transaction
    created_txn = agent_container_POST(
        agent["agent"],
        f"/revocation/registry/{context.rev_reg_id}/entry",
        data={},
        params={
            "conn_id": connection_id,
            "create_transaction_for_endorser": "false",
        },
    )
    assert created_txn
