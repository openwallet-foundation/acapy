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
from bdd_support.agent_backchannel_client import agent_backchannel_GET, agent_backchannel_POST, expected_agent_state

@given('{n} agents')
@given(u'we have {n} agents')
def step_impl(context, n):
    """Startup 'n' agents based on the options provided in the context table parameters."""
    
    context.active_agents = {}
    for row in context.table:
        agent_name = row['name']
        agent_role = row['role']
        agent_params = row['capabilities']

        context.active_agents[agent_name] = {
            'name': agent_name,
            'role': agent_role,
            'agent': None,
        }

        # startup an agent with the provided params
        agent = None
        # TODO

        # keep reference to the agent so we can shut it down later
        context.active_agents[agent_name]['agent'] = agent


@when('"{inviter}" generates a connection invitation')
def step_impl(context, inviter):
    inviter_url = context.config.userdata.get(inviter)

    (resp_status, resp_text) = agent_backchannel_POST(inviter_url + "/agent/command/", "connection", operation="create-invitation")
    assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'

    resp_json = json.loads(resp_text)
    context.inviter_invitation = resp_json["invitation"]

    # check and see if the connection_id_dict exists
    # if it does, it was probably used to create another connection in a 3+ agent scenario
    # so that means we need to keep the connection ids around for use in the scenario
    # so we will not create a new dict which will reset the dict
    if hasattr(context, 'temp_connection_id_dict'):
        context.temp_connection_id_dict[inviter] = resp_json["connection_id"]
    else:
        context.temp_connection_id_dict = {inviter: resp_json["connection_id"]}

    # Check to see if the inviter_name exists in context. If not, antother suite is using it so set the inviter name and url
    if not hasattr(context, 'inviter_name') or context.inviter_name != inviter:
        context.inviter_url = inviter_url
        context.inviter_name = inviter

    # get connection and verify status
    assert expected_agent_state(inviter_url, "connection", context.temp_connection_id_dict[inviter], "invited")

@given('"{invitee}" receives the connection invitation')
@when('"{invitee}" receives the connection invitation')
def step_impl(context, invitee):
    invitee_url = context.config.userdata.get(invitee)

    data = context.inviter_invitation
    (resp_status, resp_text) = agent_backchannel_POST(invitee_url + "/agent/command/", "connection", operation="receive-invitation", data=data)
    assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'

    resp_json = json.loads(resp_text)

    if not hasattr(context, 'connection_id_dict'):
        context.connection_id_dict = {}
        context.connection_id_dict[invitee] = {}
    
    context.connection_id_dict[invitee][context.inviter_name] = resp_json["connection_id"]

    # Also add the inviter into the main connection_id_dict. if the len is 0 that means its already been cleared and this may be Mallory.
    if len(context.temp_connection_id_dict) != 0:
        context.connection_id_dict[context.inviter_name] = {invitee: context.temp_connection_id_dict[context.inviter_name]}
        #clear the temp connection id dict used in the initial step. We don't need it anymore.
        context.temp_connection_id_dict.clear()

    # Check to see if the invitee_name exists in context. If not, antother suite is using it so set the invitee name and url
    if not hasattr(context, 'invitee_name'):
        context.invitee_url = invitee_url
        context.invitee_name = invitee

    # get connection and verify status
    assert expected_agent_state(invitee_url, "connection", context.connection_id_dict[invitee][context.inviter_name], "invited")

@when('"{inviter}" sends a connection response to "{invitee}"')
@given('"{inviter}" sends a connection response to "{invitee}"')
@then('"{inviter}" sends a connection response to "{invitee}"')
def step_impl(context, inviter, invitee):
    inviter_url = context.config.userdata.get(inviter)
    #inviter_connection_id = context.connection_id_dict[inviter]
    inviter_connection_id = context.connection_id_dict[inviter][invitee]
    invitee_url = context.config.userdata.get(invitee)
    invitee_connection_id = context.connection_id_dict[invitee][inviter]

    # get connection and verify status
    assert expected_agent_state(inviter_url, "connection", inviter_connection_id, "requested")
    assert expected_agent_state(invitee_url, "connection", invitee_connection_id, "requested")

    (resp_status, resp_text) = agent_backchannel_POST(inviter_url + "/agent/command/", "connection", operation="accept-request", id=inviter_connection_id)
    assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'

    # get connection and verify status
    assert expected_agent_state(inviter_url, "connection", inviter_connection_id, "responded")

@when('"{invitee}" receives the connection response')
@given('"{invitee}" receives the connection response')
def step_impl(context, invitee):
    invitee_url = context.config.userdata.get(invitee)
    invitee_connection_id = context.connection_id_dict[invitee][context.inviter_name]

    # invitee already recieved the connection response in the accept-request call so get connection and verify status=responded.
    assert expected_agent_state(invitee_url, "connection", invitee_connection_id, "responded")

@given('"{invitee}" sends a connection request to "{inviter}"')
@when('"{invitee}" sends a connection request to "{inviter}"')
def step_impl(context, invitee, inviter):
    invitee_url = context.config.userdata.get(invitee)
    invitee_connection_id = context.connection_id_dict[invitee][inviter]
    inviter_url = context.config.userdata.get(inviter)
    inviter_connection_id = context.connection_id_dict[inviter][invitee]

    # get connection and verify status
    assert expected_agent_state(invitee_url, "connection", invitee_connection_id, "invited")
    assert expected_agent_state(inviter_url, "connection", inviter_connection_id, "invited")

    (resp_status, resp_text) = agent_backchannel_POST(invitee_url + "/agent/command/", "connection", operation="accept-invitation", id=invitee_connection_id)
    assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'

    # get connection and verify status
    assert expected_agent_state(invitee_url, "connection", invitee_connection_id, "requested")


@when('"{inviter}" receives the connection request')
@given('"{inviter}" receives the connection request')
def step_impl(context, inviter):
    inviter_url = context.config.userdata.get(inviter)
    inviter_connection_id = context.connection_id_dict[inviter][context.invitee_name]

    # inviter already recieved the connection request in the accept-invitation call so get connection and verify status=requested.
    assert expected_agent_state(inviter_url, "connection", inviter_connection_id, "requested")


@when('"{inviter}" accepts the connection response to "{invitee}"')
def step_impl(context, inviter, invitee):
    inviter_url = context.config.userdata.get(inviter)
    inviter_connection_id = context.connection_id_dict[inviter][invitee]
    invitee_url = context.config.userdata.get(invitee)
    invitee_connection_id = context.connection_id_dict[invitee][inviter]

    # get connection and verify status
    assert expected_agent_state(inviter_url, "connection", inviter_connection_id, "requested")
    assert expected_agent_state(invitee_url, "connection", invitee_connection_id, "requested")

    (resp_status, resp_text) = agent_backchannel_POST(inviter_url + "/agent/command/", "connection", operation="accept-request", id=inviter_connection_id)
    assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'

    # get connection and verify status
    assert expected_agent_state(inviter_url, "connection", inviter_connection_id, "responded")
    assert expected_agent_state(invitee_url, "connection", invitee_connection_id, "complete")

@when('"{invitee}" sends a response ping')
def step_impl(context, invitee):
    invitee_url = context.config.userdata.get(invitee)
    invitee_connection_id = context.connection_id_dict[invitee][context.inviter_name]

    # get connection and verify status
    assert expected_agent_state(invitee_url, "connection", invitee_connection_id, "responded")

    data = {"comment": "Hello from " + invitee}
    (resp_status, resp_text) = agent_backchannel_POST(invitee_url + "/agent/command/", "connection", operation="send-ping", id=invitee_connection_id, data=data)
    assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'

    # get connection and verify status
    assert expected_agent_state(invitee_url, "connection", invitee_connection_id, "complete")

@when('"{inviter}" receives the response ping')
def step_impl(context, inviter):
    # extra step to force status to 'active' for VCX
    inviter_url = context.config.userdata.get(inviter)
    inviter_connection_id = context.connection_id_dict[inviter][context.invitee_name]

    data = {"comment": "Hello from " + inviter}
    (resp_status, resp_text) = agent_backchannel_POST(inviter_url + "/agent/command/", "connection", operation="send-ping", id=inviter_connection_id, data=data)
    assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'

    # get connection and verify status
    assert expected_agent_state(inviter_url, "connection", inviter_connection_id, "complete")

@then('"{inviter}" and "{invitee}" still have a completed connection')
@then('"{inviter}" and "{invitee}" have a connection')
def step_impl(context, inviter, invitee):
    inviter_url = context.config.userdata.get(inviter)
    inviter_connection_id = context.connection_id_dict[inviter][invitee]
    invitee_url = context.config.userdata.get(invitee)
    invitee_connection_id = context.connection_id_dict[invitee][inviter]

    # Check to see if this is a DID Exchange connection to set the state to check appropriatly for that protocol.
    if "responder_url" in context:
        state_to_assert = "completed"
    else:
        state_to_assert = "complete"

    # get connection and verify status for inviter
    assert expected_agent_state(inviter_url, "connection", inviter_connection_id, state_to_assert)

    # get connection and verify status for invitee
    assert expected_agent_state(invitee_url, "connection", invitee_connection_id, state_to_assert)

@then('"{invitee}" is connected to "{inviter}"')
def step_impl(context, inviter, invitee):
    inviter_url = context.config.userdata.get(inviter)
    inviter_connection_id = context.connection_id_dict[inviter][invitee]
    invitee_url = context.config.userdata.get(invitee)
    invitee_connection_id = context.connection_id_dict[invitee][inviter]

    # get connection and verify status for inviter
    assert expected_agent_state(inviter_url, "connection", inviter_connection_id, "responded")

    # get connection and verify status for invitee
    assert expected_agent_state(invitee_url, "connection", invitee_connection_id, "complete")

@given('"{sender}" and "{receiver}" have an existing connection')
def step_impl(context, sender, receiver):
    if "DIDExchangeConnection" in context.tags:
        context.execute_steps(u'''
            When "''' + sender + '''" sends an explicit invitation
            And "''' + receiver + '''" receives the invitation
            And "''' + receiver + '''" sends the request to "''' + sender + '''"
            And "''' + sender + '''" receives the request
            And "''' + sender + '''" sends a response to "''' + receiver + '''"
            And "''' + receiver + '''" receives the response
            And "''' + receiver + '''" sends complete to "''' + sender + '''"
            Then "''' + sender + '''" and "''' + receiver + '''" have a connection
        ''')

    else:
        context.execute_steps(u'''
            When "''' + sender + '''" generates a connection invitation
            And "''' + receiver + '''" receives the connection invitation
            And "''' + receiver + '''" sends a connection request to "''' + sender + '''"
            And "''' + sender + '''" receives the connection request
            And "''' + sender + '''" sends a connection response to "''' + receiver + '''"
            And "''' + receiver + '''" receives the connection response
            And "''' + receiver + '''" sends trustping to "''' + sender + '''"
            Then "''' + sender + '''" and "''' + receiver + '''" have a connection
        ''')

@when(u'"{sender}" sends a trust ping')
def step_impl(context, sender):
    sender_url = context.config.userdata.get(sender)
    sender_connection_id = context.connection_id_dict[sender][context.inviter_name]

    # get connection and verify status
    assert expected_agent_state(sender_url, "connection", sender_connection_id, "active")

    data = {"comment": "Hello from " + sender}
    (resp_status, resp_text) = agent_backchannel_POST(sender_url + "/agent/command/", "connection", operation="send-ping", id=sender_connection_id, data=data)
    assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'

    # get connection and verify status
    assert expected_agent_state(sender_url, "connection", sender_connection_id, "complete")

@then('"{receiver}" receives the trust ping')
def step_impl(context, receiver):
    # TODO
    pass


@given('"{invitee}" has sent a connection request to "{inviter}"')
def step_impl(context, invitee, inviter):
    context.execute_steps('''
        When "''' + inviter + '''" generates a connection invitation
         And "''' + invitee + '''" receives the connection invitation
         And "''' + invitee + '''" sends a connection request
    ''')

@given('"{inviter}" has accepted the connection request by sending a connection response')
def step_impl(context, inviter):
    context.execute_steps('''When "''' + inviter + '''" accepts the connection response''')


@given(u'"{invitee}" is in the state of complete')
def step_impl(context, invitee):
    invitee_url = context.config.userdata.get(invitee)
    invitee_connection_id = context.connection_id_dict[invitee][context.inviter_name]

    # get connection and verify status
    assert expected_agent_state(invitee_url, "connection", invitee_connection_id, "complete")


@given(u'"{inviter}" is in the state of responded')
def step_impl(context, inviter):
    inviter_url = context.config.userdata.get(inviter)
    inviter_connection_id = context.connection_id_dict[inviter][context.invitee_name]

    # get connection and verify status
    assert expected_agent_state(inviter_url, "connection", inviter_connection_id, "responded")


@when(u'"{sender}" sends acks to "{reciever}"')
def step_impl(context, sender, reciever):
    sender_url = context.config.userdata.get(sender)
    sender_connection_id = context.connection_id_dict[sender][context.inviter_name]

    data = {"comment": "acknowledgement from " + sender}
    # TODO acks not implemented yet, this will fail.
    (resp_status, resp_text) = agent_backchannel_POST(sender_url + "/agent/command/", "connection", operation="acks", id=sender_connection_id, data=data)
    assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'


@when('"{sender}" sends trustping to "{receiver}"')
def step_impl(context, sender, receiver):
    sender_url = context.config.userdata.get(sender)
    sender_connection_id = context.connection_id_dict[sender][receiver]

    data = {"comment": "acknowledgement from " + sender}
    (resp_status, resp_text) = agent_backchannel_POST(sender_url + "/agent/command/", "connection", operation="send-ping", id=sender_connection_id, data=data)
    assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'


@then(u'"{inviter}" is in the state of complete')
def step_impl(context, inviter):
    # get connection and verify status
    assert expected_agent_state(context.config.userdata.get(inviter), "connection", context.connection_id_dict[inviter][context.invitee_name], "complete")


@given(u'"{inviter}" generated a single-use connection invitation')
def step_impl(context, inviter):
    context.execute_steps('''
        When "''' + inviter + '''" generates a connection invitation
    ''')


@given(u'"{invitee}" received the connection invitation')
def step_impl(context, invitee):
    context.execute_steps('''
        When "''' + invitee + '''" receives the connection invitation
    ''')


@given(u'"{invitee}" sent a connection request to "{inviter}"')
def step_impl(context, invitee, inviter):
    context.execute_steps('''
        When "''' + invitee + '''" sends a connection request to "''' + inviter + '''"
    ''')


@given(u'"{inviter}" and "{invitee}" have a connection')
def step_impl(context, inviter, invitee):
    context.execute_steps('''
        When "''' + invitee + '''" sends trustping to "''' + inviter + '''"
        Then "''' + inviter + '''" and "''' + invitee + '''" have a connection
        ''')


@when(u'"{inviteinterceptor}" sends a connection request to "{inviter}" based on the connection invitation')
def step_impl(context, inviteinterceptor, inviter):
    context.execute_steps('''
        When "''' + inviteinterceptor + '''" receives the connection invitation
    ''')
    inviteinterceptor_url = context.config.userdata.get(inviteinterceptor)
    inviteinterceptor_connection_id = context.connection_id_dict[inviteinterceptor][inviter]

    # get connection and verify status before call
    assert expected_agent_state(inviteinterceptor_url, "connection", inviteinterceptor_connection_id, "invited")

    (resp_status, resp_text) = agent_backchannel_POST(inviteinterceptor_url + "/agent/command/", "connection", operation="accept-invitation", id=inviteinterceptor_connection_id)
    assert resp_status == 200, f'resp_status {resp_status} is not 200; {resp_text}'

    # get connection and verify status
    assert expected_agent_state(inviteinterceptor_url, "connection", inviteinterceptor_connection_id, "requested")

@then(u'"{inviter}" sends a request_not_accepted error')
def step_impl(context, inviter):
    inviter_url = context.config.userdata.get(inviter)
    inviter_connection_id = context.connection_id_dict[inviter][context.invitee_name]

    # TODO It is expected that accept-request should send a request not accepted error, not a 500
    (resp_status, resp_text) = agent_backchannel_POST(inviter_url + "/agent/command/", "connection", operation="accept-request", id=inviter_connection_id)
    # TODO once bug 418 has been fixed change this assert to the proper response code. 
    # bug reference URL: https://app.zenhub.com/workspaces/von---verifiable-organization-network-5adf53987ccbaa70597dbec0/issues/hyperledger/aries-cloudagent-python/418
    assert resp_status == 406, f'resp_status {resp_status} is not 406; {resp_text}'
    #assert resp_status == 500

    # Invitee should still be active based on the inviter connection id.
    #assert connection_status(inviter_url, inviter_connection_id, ["complete"])

@given(u'"{inviter}" generated a multi-use connection invitation')
def step_impl(context, inviter):
    context.execute_steps('''
        When "''' + inviter + '''" generates a connection invitation
    ''')


@when(u'"{sender}" and "{receiver}" complete the connection process')
def step_impl(context, sender, receiver):
    context.execute_steps(u'''
         When "''' + receiver + '''" receives the connection invitation
         And "''' + receiver + '''" sends a connection request to "''' + sender + '''"
         And "''' + sender + '''" receives the connection request
         And "''' + sender + '''" sends a connection response to "''' + receiver + '''"
         And "''' + receiver + '''" receives the connection response
         And "''' + receiver + '''" sends trustping to "''' + sender + '''"
    ''')

@then('"{inviter}" and "{invitee}" are able to complete the connection')
def step_impl(context):
    raise NotImplementedError('STEP: Then "Acme" and "Bob" are able to complete the connection')


@then(u'"{receiver}" and "{sender}" have another connection')
def step_impl(context, receiver, sender):
    context.execute_steps(u'''
        Then "''' + sender + '''" and "''' + receiver + '''" have a connection
    ''')


@given(u'"Bob" has Invalid DID Method')
def step_impl(context):
    raise NotImplementedError(u'STEP: Given "Bob" has Invalid DID Method')


@then(u'"Acme" sends an request not accepted error')
def step_impl(context):
    raise NotImplementedError(u'STEP: Then "Acme" sends an request not accepted error')


@then(u'the state of "Acme" is reset to Null')
def step_impl(context):
    raise NotImplementedError(u'STEP: Then the state of "Acme" is reset to Null')


@then(u'the state of "Bob" is reset to Null')
def step_impl(context):
    raise NotImplementedError(u'STEP: Then the state of "Bob" is reset to Null')


@given(u'"Bob" has unknown endpoint protocols')
def step_impl(context):
    raise NotImplementedError(u'STEP: Given "Bob" has unknown endpoint protocols')
