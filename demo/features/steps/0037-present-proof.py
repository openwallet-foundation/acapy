from behave import given, when, then
import json
from time import sleep
import time

from bdd_support.agent_backchannel_client import (
    read_proof_req_data,
    read_presentation_data,
    aries_container_request_proof,
    aries_container_verify_proof,
    agent_container_GET,
    agent_container_POST,
)
from runners.agent_container import AgentContainer


# This step is defined in another feature file
# Given "Acme" and "Bob" have an existing connection
# And "Bob" has an issued <Schema_name> credential <Credential_data> from <issuer>


@when(
    '"{verifier}" sends a request for proof presentation {request_for_proof} to "{prover}"'
)
def step_impl(context, verifier, request_for_proof, prover):
    agent = context.active_agents[verifier]

    proof_request_info = read_proof_req_data(request_for_proof)

    proof_exchange = aries_container_request_proof(agent["agent"], proof_request_info)

    context.proof_request = proof_request_info
    context.proof_exchange = proof_exchange


@then('"{verifier}" has the proof verified')
def step_impl(context, verifier):
    agent = context.active_agents[verifier]

    proof_request = context.proof_request

    # check the received credential status (up to 10 seconds)
    for i in range(10):
        verified = aries_container_verify_proof(agent["agent"], proof_request)
        if verified is not None:
            return verified

    assert False
