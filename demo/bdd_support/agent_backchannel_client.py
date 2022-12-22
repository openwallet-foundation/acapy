import asyncio
import json
import uuid

from runners.agent_container import AgentContainer, create_agent_with_args_list


######################################################################
# coroutine utilities
######################################################################


def run_coroutine(coroutine, *args, **kwargs):
    loop = asyncio.get_event_loop()
    if not loop:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coroutine(*args, **kwargs))
    finally:
        pass
        # loop.close()


def async_sleep(delay):
    run_coroutine(asyncio.sleep, delay)


######################################################################
# high level aries agent interface
######################################################################
def create_agent_container_with_args(in_args: list):
    return run_coroutine(create_agent_with_args_list, in_args)


def aries_container_initialize(
    the_container: AgentContainer,
    schema_name: str = None,
    schema_attrs: list = None,
):
    run_coroutine(
        the_container.initialize,
        schema_name=schema_name,
        schema_attrs=schema_attrs,
    )


def agent_container_register_did(
    the_container: AgentContainer,
    did: str,
    verkey: str,
    role: str,
):
    run_coroutine(
        the_container.register_did,
        did,
        verkey,
        role,
    )


def aries_container_terminate(
    the_container: AgentContainer,
):
    return run_coroutine(the_container.terminate)


def aries_container_generate_invitation(
    the_container: AgentContainer,
):
    return run_coroutine(
        the_container.generate_invitation,
    )


def aries_container_receive_invitation(
    the_container: AgentContainer,
    invite_details: dict,
):
    return run_coroutine(
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
    version: str = None,
):
    return run_coroutine(
        the_container.create_schema_and_cred_def,
        schema_name,
        schema_attrs,
        version=version,
    )


def aries_container_issue_credential(
    the_container: AgentContainer,
    cred_def_id: str,
    cred_attrs: list,
):
    return run_coroutine(
        the_container.issue_credential,
        cred_def_id,
        cred_attrs,
    )


def aries_container_receive_credential(
    the_container: AgentContainer,
    cred_def_id: str,
    cred_attrs: list,
):
    return run_coroutine(
        the_container.receive_credential,
        cred_def_id,
        cred_attrs,
    )


def aries_container_request_proof(
    the_container: AgentContainer,
    proof_request: dict,
    explicit_revoc_required: bool = False,
):
    return run_coroutine(
        the_container.request_proof,
        proof_request,
        explicit_revoc_required=explicit_revoc_required,
    )


def aries_container_verify_proof(
    the_container: AgentContainer,
    proof_request: dict,
):
    return run_coroutine(
        the_container.verify_proof,
        proof_request,
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
    proof_request_info = read_json_data("proof_request_" + proof_req_name + ".json")
    return proof_request_info["presentation_proposal"]


def read_presentation_data(presentation_name: str):
    return read_json_data("presentation_" + presentation_name + ".json")


######################################################################
# probably obsolete ...
######################################################################


def agent_container_GET(
    the_container: AgentContainer,
    path: str,
    text: bool = False,
    params: dict = None,
) -> dict:
    return run_coroutine(
        the_container.admin_GET,
        path,
        text=text,
        params=params,
    )


def agent_container_POST(
    the_container: AgentContainer,
    path: str,
    data: dict = None,
    text: bool = False,
    params: dict = None,
) -> dict:
    return run_coroutine(
        the_container.admin_POST,
        path,
        data=data,
        text=text,
        params=params,
    )


def agent_container_PATCH(
    the_container: AgentContainer,
    path: str,
    data: dict = None,
    text: bool = False,
    params: dict = None,
) -> dict:
    return run_coroutine(
        the_container.admin_PATCH,
        path,
        data=data,
        text=text,
        params=params,
    )


def agent_container_PUT(
    the_container: AgentContainer,
    path: str,
    data: dict = None,
    text: bool = False,
    params: dict = None,
) -> dict:
    return run_coroutine(
        the_container.admin_PUT,
        path,
        data=data,
        text=text,
        params=params,
    )
