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


######################################################################
# coroutine utilities
######################################################################

def run_coroutine(coroutine):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coroutine())
    finally:
        loop.close()

def run_coroutine_with_args(coroutine, *args):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coroutine(*args))
    finally:
        loop.close()

def run_coroutine_with_kwargs(coroutine, *args, **kwargs):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coroutine(*args, **kwargs))
    finally:
        loop.close()


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
