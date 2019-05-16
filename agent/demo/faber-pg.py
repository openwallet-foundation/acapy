import subprocess
import time
import requests
import random
import sys
import json
from demo_utils import *


"""
Docker version:
PORTS="5001:5000 10001:10000" ../scripts/run_docker -it http 0.0.0.0 10000 -ot http --admin 0.0.0.0 5000 -e "http://host.docker.internal:10001" --accept-requests --accept-invites --invite
"""
# detect runmode and set hostnames accordingly
run_mode = os.getenv('RUNMODE')

internal_host = "127.0.0.1"
external_host = "localhost"

if run_mode == 'docker':
    internal_host = "host.docker.internal"
    external_host = "host.docker.internal"

# some globals that are required by the hook code
webhook_port = int(sys.argv[1])
in_port_1  = webhook_port + 1
in_port_2  = webhook_port + 2
in_port_3  = webhook_port + 3
admin_port = webhook_port + 4
admin_url  = 'http://' + internal_host + ':' + str(admin_port)

# url mapping for rest hook callbacks
urls = (
  '/webhooks/topic/(.*)/', 'faber_webhooks'
)

# agent webhook callbacks
class faber_webhooks(webhooks):
    def handle_credentials(self, state, message):
        global admin_url
        credential_exchange_id = message['credential_exchange_id']
        s_print("Credential: state=", state, ", credential_exchange_id=", credential_exchange_id)

        if state == 'request_received':
            print("#17 Issue credential to X")
            cred_attrs = {
                'name': 'Alice Smith',
                'date': '2018-05-28',
                'degree': 'Maths',
                'age': '24'
            }
            resp = requests.post(admin_url + '/credential_exchange/' + credential_exchange_id + '/issue',
                json={"credential_values": cred_attrs})
            assert resp.status_code == 200

            return ""

        return ""

    def handle_presentations(self, state, message):
        global admin_url
        presentation_exchange_id = message['presentation_exchange_id']
        s_print("Presentation: state=", state, ", presentation_exchange_id=", presentation_exchange_id)

        if state == 'presentation_received':
            print("#27 Process the proof provided by X")
            print("#28 Check if proof is valid")
            resp = requests.post(admin_url + '/presentation_exchange/' + presentation_exchange_id + '/verify_presentation')
            assert resp.status_code == 200
            proof = json.loads(resp.text)

            s_print("Proof =", proof['verified'])

            return ""

        return ""


def main():
    if run_mode == 'docker':
        genesis = requests.get('http://host.docker.internal:9000/genesis').text
    else:
        with open('local-genesis.txt', 'r') as genesis_file:
            genesis = genesis_file.read()
    #print(genesis)

    # TODO seed from input parameter; optionally register the DID
    rand_name = str(random.randint(100000, 999999))
    seed = ('my_seed_000000000000000000000000' + rand_name)[-32:]
    alias = 'My Test Company'
    register_did = True
    if register_did:
        print("Registering", alias, "with seed", seed)
        ledger_url = 'http://' + external_host + ':9000'
        headers = {"accept": "application/json"}
        data = {"alias": alias, "seed": seed, "role": "TRUST_ANCHOR"}
        resp = requests.post(ledger_url+'/register', json=data)
        assert resp.status_code == 200
        nym_info = json.loads(resp.text)
        my_did = nym_info["did"]
        print(nym_info)

    # run app and respond to agent webhook callbacks (run in background)
    g_vars = globals()
    webhook_thread = background_hook_thread(urls, g_vars)
    time.sleep(3.0)

    # start agent sub-process
    print("#1 Provision an agent and wallet, get back configuration details")
    endpoint_url  = 'http://' + internal_host + ':' + str(in_port_1)
    wallet_name = 'faber'+rand_name
    wallet_key  = 'faber'+rand_name
    python_path = ".."
    webhook_url = "http://" + external_host + ':' + str(webhook_port) + "/webhooks"
    (agent_proc, t1, t2) =  start_agent_subprocess(genesis, seed, endpoint_url, in_port_1, in_port_2, in_port_3, admin_port,
                                            'indy', wallet_name, wallet_key, python_path, webhook_url)
    time.sleep(3.0)
    print("Admin url is at:", admin_url)
    print("Endpoint url is at:", endpoint_url)

    try:
        # check swagger content
        resp = requests.get(admin_url+'/api/docs/swagger.json')
        assert resp.status_code == 200
        p = resp.text
        assert 'Indy Catalyst Agent' in p

        # create a schema
        print("#3 Create a new schema on the ledger")
        version = format("%d.%d.%d" % (random.randint(1, 101), random.randint(1, 101), random.randint(1, 101)))
        schema_body = {
                "schema_name": "degree schema",
                "schema_version": version,
                "attributes": ['name', 'date', 'degree', 'age'],
            }
        schema_response = requests.post(admin_url+"/schemas", json=schema_body)
        assert resp.status_code == 200
        print(schema_response.text)
        schema_response_body = schema_response.json()
        schema_id = schema_response_body["schema_id"]
        print(schema_id)

        # create a cred def for the schema
        print("#4 Create a new credential definition on the ledger")
        credential_definition_body = {"schema_id": schema_id}
        credential_definition_response = requests.post(
            admin_url+"/credential-definitions", json=credential_definition_body
        )
        credential_definition_response_body = credential_definition_response.json()
        credential_definition_id = credential_definition_response_body[
            "credential_definition_id"
        ]
        print(f"cred def id: {credential_definition_id}")

        print("#5 Create a connection to alice and print out the invite details")
        # generate an invitation
        headers = {"accept": "application/json"}
        resp = requests.post(admin_url+'/connections/create-invitation', headers=headers)
        assert resp.status_code == 200
        connection = json.loads(resp.text)
        print('invitation response:', connection)
        print("*****************")
        print("Invitation:", json.dumps(connection['invitation']))
        print("*****************")
        conn_id = connection['connection_id']

        time.sleep(3.0)
        option = input('(1) Issue Credential, (2) Send Proof Request, (3) Send Message (X) Exit? [1/2/3/X]')
        while option != 'X' and option != 'x':
            if option == '1':
                print("#13 Issue credential offer to X")
                offer = {"credential_definition_id": credential_definition_id, "connection_id": conn_id}
                resp = requests.post(admin_url + '/credential_exchange/send-offer', json=offer)
                assert resp.status_code == 200
                credential_exchange = json.loads(resp.text)
                credential_exchange_id = credential_exchange['credential_exchange_id']

            if option == '2':
                print("#20 Request proof of degree from alice")
                proof_attrs = [
                    {'name': 'name', 'restrictions': [{'issuer_did': my_did}]},
                    {'name': 'date', 'restrictions': [{'issuer_did': my_did}]},
                    {'name': 'degree', 'restrictions': [{'issuer_did': my_did}]},
                    {'name': 'self_attested_thing'}
                ]
                proof_predicates = [{'name':'age', 'p_type':'>=', 'p_value':18},]
                proof_request = {"name": "Proof of Education", "version": "1.0", "connection_id": conn_id, "requested_attributes": proof_attrs, "requested_predicates": proof_predicates}
                resp = requests.post(admin_url + '/presentation_exchange/send_request', json=proof_request)
                assert resp.status_code == 200
                presentation_exchange = json.loads(resp.text)
                presentation_exchange_id = presentation_exchange['presentation_exchange_id']

            if option == '3':
                msg = input('Enter message:')
                resp = requests.post(admin_url + '/connections/' + conn_id + '/send-message', json={'content': msg})
                assert resp.status_code == 200

            option = input('(1) Issue Credential, (2) Send Proof Request, (3) Send Message (X) Exit? [1/2/3/X]')

    except Exception as e:
        print(e)
    finally:
        time.sleep(2.0)
        agent_proc.terminate()
        try:
            agent_proc.wait(timeout=0.5)
            print('== subprocess exited with rc =', agent_proc.returncode)
        except subprocess.TimeoutExpired:
            print('subprocess did not terminate in time')
        sys.exit()

if __name__ == "__main__":
    main()
