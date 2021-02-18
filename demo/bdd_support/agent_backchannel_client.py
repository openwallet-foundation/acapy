import asyncio
from aiohttp import (
    web,
    ClientSession,
    ClientRequest,
    ClientResponse,
    ClientError,
    ClientTimeout,
)
import json
from time import sleep
import uuid

from runners.agent_container import AgentContainer, create_agent_with_args
from runners.support.agent import DemoAgent


######################################################################
# coroutine utilities
######################################################################

def run_coroutine(coroutine):
    loop = asyncio.get_event_loop()
    if not loop:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coroutine())
    finally:
        pass
        #loop.close()

def run_coroutine_with_args(coroutine, *args):
    loop = asyncio.get_event_loop()
    if not loop:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coroutine(*args))
    finally:
        pass
        #loop.close()

def run_coroutine_with_kwargs(coroutine, *args, **kwargs):
    loop = asyncio.get_event_loop()
    if not loop:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coroutine(*args, **kwargs))
    finally:
        pass
        #loop.close()


######################################################################
# high level aries agent interface
######################################################################
def create_agent_container_with_args(in_args: list):
    return run_coroutine_with_args(
        create_agent_with_args,
        in_args
    )

def aries_container_initialize(
    the_container: AgentContainer,
    schema_name: str = None,
    schema_attrs: list = None,
):
    run_coroutine_with_kwargs(
        the_container.initialize,
        schema_name = schema_name,
        schema_attrs = schema_attrs,
    )

def aries_container_terminate(
    the_container: AgentContainer,
):
    return run_coroutine(the_container.terminate)

def aries_container_generate_invitation(
    the_container: AgentContainer,
):
    return run_coroutine_with_kwargs(
        the_container.generate_invitation,
    )

def aries_container_receive_invitation(
    the_container: AgentContainer,
    invite_details: dict,
):
    return run_coroutine_with_kwargs(
        the_container.input_invitation,
        invite_details,
    )

def aries_container_detect_connection(
    the_container: AgentContainer,
):
    run_coroutine(the_container.detect_connection)

def aries_container_create_schema_cred_def(
    the_container: AgentContainer,
        schema_name: str,
        schema_attrs: list,
):
    return run_coroutine_with_args(
        the_container.create_schema_and_cred_def,
        schema_name,
        schema_attrs,
    )

def aries_container_issue_credential(
    the_container: AgentContainer,
    cred_def_id: str,
    cred_attrs: list,
):
    return run_coroutine_with_args(
        the_container.issue_credential,
        cred_def_id,
        cred_attrs,
    )

def aries_container_receive_credential(
    the_container: AgentContainer,
    cred_def_id: str,
    cred_attrs: list,
):
    return run_coroutine_with_args(
        the_container.receive_credential,
        cred_def_id,
        cred_attrs,
    )


######################################################################
# aries agent admin api interface
######################################################################


######################################################################
# general utilities
######################################################################
def read_json_data(file_name: str):
    with open("features/data/" + file_name) as data_file:
        return json.load(data_file)

def read_schema_data(schema_name: str):
    return read_json_data("schema_" + schema_name + ".json")

def read_credential_data(schema_name: str, cred_scenario_name: str):
    schema_cred_data = read_json_data("cred_data_schema_" + schema_name + ".json")
    cred_data = schema_cred_data[cred_scenario_name]
    for attr in cred_data["attributes"]:
        if attr["value"] == "@uuid":
            attr["value"] = str(uuid.uuid4())
    return cred_data["attributes"]

def read_proof_req_data(proof_req_name: str):
    return read_json_data("proof_request_" + proof_req_name + ".json")

def read_presentation_data(presentation_name: str):
    return read_json_data("presentation_" + presentation_name + ".json")


######################################################################
# probably obsolete ...
######################################################################

async def make_agent_backchannel_request(
    method, path, data=None, text=False, params=None
) -> (int, str):
    params = {k: v for (k, v) in (params or {}).items() if v is not None}
    client_session: ClientSession = ClientSession()
    async with client_session.request(
        method, path, json=data, params=params
    ) as resp:
        resp_status = resp.status
        resp_text = await resp.text()
        await client_session.close()
        return (resp_status, resp_text)


def agent_backchannel_GET(url, topic, operation=None, id=None) -> (int, str):
    agent_url = url + topic + "/"
    if operation:
        agent_url = agent_url + operation + "/"
    if id:
        agent_url = agent_url + id
    (resp_status, resp_text) = run_coroutine_with_kwargs(make_agent_backchannel_request, "GET", agent_url)
    return (resp_status, resp_text)


def agent_backchannel_POST(url, topic, operation=None, id=None, data=None) -> (int, str):
    agent_url = url + topic + "/"
    payload = {}
    if data:
        payload["data"] = data
    if operation:
        agent_url = agent_url + operation + "/"
    if id:
        if topic == 'credential':
            payload["cred_ex_id"] = id
        else:
            payload["id"] = id
    (resp_status, resp_text) = run_coroutine_with_kwargs(make_agent_backchannel_request, "POST", agent_url, data=payload)
    return (resp_status, resp_text)

def agent_backchannel_DELETE(url, topic, id=None, data=None) -> (int, str):
    agent_url = url + topic + "/"
    if id:
        agent_url = agent_url + id
    (resp_status, resp_text) = run_coroutine_with_kwargs(make_agent_backchannel_request, "DELETE", agent_url)
    return (resp_status, resp_text)

def expected_agent_state(agent_url, protocol_txt, thread_id, status_txt):
    sleep(0.2)
    state = "None"
    if type(status_txt) != list:
        status_txt = [status_txt]
    for i in range(5):
        (resp_status, resp_text) = agent_backchannel_GET(agent_url + "/agent/command/", protocol_txt, id=thread_id)
        if resp_status == 200:
            resp_json = json.loads(resp_text)
            state = resp_json["state"]
            if state in status_txt:
                return True
        sleep(0.2)

    print("From", agent_url, "Expected state", status_txt, "but received", state, ", with a response status of", resp_status)
    return False
