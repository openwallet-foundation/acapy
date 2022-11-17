import time
from time import sleep

from bdd_support.agent_backchannel_client import (
    agent_container_GET,
    agent_container_PATCH,
    agent_container_POST,
    agent_container_PUT,
    agent_container_register_did,
    async_sleep,
    read_json_data,
    read_schema_data,
)
from behave import given, then, when
from runners.agent_container import AgentContainer

# This step is defined in another feature file
# Given "Acme" and "Bob" have an existing connection


@when('"{agent_name}" has a DID with role "{did_role}"')
def step_impl(context, agent_name, did_role):
    agent = context.active_agents[agent_name]

    # create a new DID in the current wallet
    created_did = agent_container_POST(agent["agent"], "/wallet/did/create")

    # publish to the ledger with did_role
    registered_did = agent_container_register_did(
        agent["agent"],
        created_did["result"]["did"],
        created_did["result"]["verkey"],
        "ENDORSER" if did_role == "ENDORSER" else "",
    )

    # make the new did the wallet's public did
    published_did = agent_container_POST(
        agent["agent"],
        "/wallet/did/public",
        params={"did": created_did["result"]["did"]},
    )
    if "result" in published_did:
        # published right away!
        pass
    elif "txn" in published_did:
        # we are an author and need to go through the endorser process
        # assume everything works!
        async_sleep(3.0)

    if not "public_dids" in context:
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

    created_txn = agent_container_POST(
        agent["agent"],
        "/schemas",
        data=schema_info["schema"],
        params={"conn_id": connection_id, "create_transaction_for_endorser": "true"},
    )

    # assert goodness
    if agent["agent"].endorser_role and agent["agent"].endorser_role == "author":
        assert created_txn["txn"]["state"] == "request_sent"
    else:
        assert created_txn["txn"]["state"] == "transaction_created"

    if not "txn_ids" in context:
        context.txn_ids = {}
    context.txn_ids["AUTHOR"] = created_txn["txn"]["transaction_id"]


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


@when('"{agent_name}" has written the schema {schema_name} to the ledger')
@then('"{agent_name}" has written the schema {schema_name} to the ledger')
def step_impl(context, agent_name, schema_name):
    agent = context.active_agents[agent_name]

    schema_info = read_schema_data(schema_name)

    schemas = {"schema_ids": []}
    i = 5
    while 0 == len(schemas["schema_ids"]) and i > 0:
        async_sleep(1.0)
        schemas = agent_container_GET(agent["agent"], "/schemas/created")
        i = i - 1
    assert len(schemas["schema_ids"]) == 1

    schema_id = schemas["schema_ids"][0]
    schema = agent_container_GET(agent["agent"], "/schemas/" + schema_id)

    context.schema_name = schema_name

    # TODO assert goodness


@when('"{agent_name}" authors a credential definition transaction with {schema_name}')
@then('"{agent_name}" authors a credential definition transaction with {schema_name}')
def step_impl(context, agent_name, schema_name):
    agent = context.active_agents[agent_name]

    connection_id = agent["agent"].agent.connection_id

    # TODO for now assume there is a single schema; should find the schema based on the supplied name
    schemas = agent_container_GET(agent["agent"], "/schemas/created")
    assert len(schemas["schema_ids"]) == 1

    schema_id = schemas["schema_ids"][0]
    created_txn = agent_container_POST(
        agent["agent"],
        "/credential-definitions",
        data={
            "schema_id": schema_id,
            "tag": "test_cred_def_with_endorsement",
            "support_revocation": True,
            "revocation_registry_size": 1000,
        },
        params={"conn_id": connection_id, "create_transaction_for_endorser": "true"},
    )

    # assert goodness
    if agent["agent"].endorser_role and agent["agent"].endorser_role == "author":
        assert created_txn["txn"]["state"] == "request_sent"
    else:
        assert created_txn["txn"]["state"] == "transaction_created"
    if not "txn_ids" in context:
        context.txn_ids = {}
    context.txn_ids["AUTHOR"] = created_txn["txn"]["transaction_id"]


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
        cred_defs = agent_container_GET(
            agent["agent"], "/credential-definitions/created"
        )
        i = i - 1
    assert len(cred_defs["credential_definition_ids"]) == 1

    cred_def_id = cred_defs["credential_definition_ids"][0]
    cred_def = agent_container_GET(
        agent["agent"], "/credential-definitions/" + cred_def_id
    )

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

    # generate revocation registry transaction
    rev_reg = agent_container_POST(
        agent["agent"],
        "/revocation/create-registry",
        data={"credential_definition_id": context.cred_def_id, "max_cred_num": 1000},
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
    assert created_txn["txn"]["state"] == "transaction_created"
    if not "txn_ids" in context:
        context.txn_ids = {}
    context.txn_ids["AUTHOR"] = created_txn["txn"]["transaction_id"]


@when('"{agent_name}" has written the revocation registry definition to the ledger')
@then('"{agent_name}" has written the revocation registry definition to the ledger')
def step_impl(context, agent_name):
    agent = context.active_agents[agent_name]

    rev_regs = {"rev_reg_ids": []}
    i = 5
    while 0 == len(rev_regs["rev_reg_ids"]) and i > 0:
        async_sleep(1.0)
        rev_regs = agent_container_GET(
            agent["agent"],
            "/revocation/registries/created",
            params={
                "cred_def_id": context.cred_def_id,
            },
        )
        i = i - 1
    assert len(rev_regs["rev_reg_ids"]) == 1

    rev_reg_id = rev_regs["rev_reg_ids"][0]

    context.rev_reg_id = rev_reg_id


@when(
    '"{agent_name}" has activated the tails file, and uploaded it to the tails server'
)
@then(
    '"{agent_name}" has has activated the tails file, and uploaded it to the tails server'
)
def step_impl(context, agent_name):
    agent = context.active_agents[agent_name]

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


@when(
    '"{agent_name}" has written the revocation registry entry transaction to the ledger'
)
@then(
    '"{agent_name}" has written the revocation registry entry transaction to the ledger'
)
def step_impl(context, agent_name):
    agent = context.active_agents[agent_name]

    # a registry is promoted to active when its initial entry is sent
    i = 5
    while i > 0:
        async_sleep(1.0)
        reg_info = agent_container_GET(
            agent["agent"],
            f"/revocation/registry/{context.rev_reg_id}",
        )
        state = reg_info["result"]["state"]
        if state == "active":
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
    created_txn = agent_container_POST(
        agent["agent"],
        f"/revocation/registry/{context.rev_reg_id}/entry",
        data={},
        params={
            "conn_id": connection_id,
            "create_transaction_for_endorser": "true",
        },
    )
    assert created_txn["txn"]["state"] == "transaction_created"
    if not "txn_ids" in context:
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


@when('"{agent_name}" revokes the credential without publishing the entry')
@then('"{agent_name}" revokes the credential without publishing the entry')
def step_impl(context, agent_name):
    agent = context.active_agents[agent_name]

    # get the required revocation info from the last credential exchange
    cred_exchange = context.cred_exchange

    cred_exchange = agent_container_GET(
        agent["agent"], "/issue-credential-2.0/records/" + cred_exchange["cred_ex_id"]
    )
    context.cred_exchange = cred_exchange

    # revoke the credential
    agent_container_POST(
        agent["agent"],
        "/revocation/revoke",
        data={
            "rev_reg_id": cred_exchange["indy"]["rev_reg_id"],
            "cred_rev_id": cred_exchange["indy"]["cred_rev_id"],
            "publish": False,
            "connection_id": cred_exchange["cred_ex_record"]["connection_id"],
        },
    )

    # pause for a few seconds
    async_sleep(3.0)


@when('"{agent_name}" authors a revocation registry entry publishing transaction')
@then('"{agent_name}" authors a revocation registry entry publishing transaction')
def step_impl(context, agent_name):
    agent = context.active_agents[agent_name]

    connection_id = agent["agent"].agent.connection_id

    # create rev_reg entry transaction
    created_rev_reg = agent_container_POST(
        agent["agent"],
        f"/revocation/publish-revocations",
        data={
            "rrid2crid": {
                context.cred_exchange["indy"]["rev_reg_id"]: [
                    context.cred_exchange["indy"]["cred_rev_id"]
                ]
            }
        },
    )

    # check that rev reg entry was written
    assert "rrid2crid" in created_rev_reg


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
    assert len(cred_list["results"]) == 1
    cred_id = cred_list["results"][0]["referent"]

    # check revocation status for the credential
    revocation_status = agent_container_GET(
        agent["agent"],
        f"/credential/revoked/{cred_id}",
        params={"to": int(time.time())},
    )
    assert revocation_status["revoked"] == True
