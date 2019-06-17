import os
import subprocess
import time
import requests
import random
import sys
import json
from traceback import print_exc

from demo_utils import background_hook_thread, s_print, start_agent_subprocess, webhooks


"""
Docker version:
PORTS="5000:5000 10000:10000" ../scripts/run_docker -it http 0.0.0.0 10000 -ot http --admin 0.0.0.0 5000 -e "http://host.docker.internal:10000" --accept-requests --accept-invites
"""
# detect runmode and set hostnames accordingly
run_mode = os.getenv("RUNMODE")

internal_host = "127.0.0.1"
external_host = "localhost"
scripts_dir = "../scripts/"

if run_mode == "docker":
    internal_host = "host.docker.internal"
    external_host = "host.docker.internal"
    scripts_dir = "scripts/"

# some globals that are required by the hook code
webhook_port = int(sys.argv[1])
in_port_1 = webhook_port + 1
in_port_2 = webhook_port + 2
in_port_3 = webhook_port + 3
admin_port = webhook_port + 4
admin_url = "http://" + internal_host + ":" + str(admin_port)

# url mapping for rest hook callbacks
urls = ("/webhooks/topic/(.*)/", "alice_webhooks")

# agent webhook callbacks
class alice_webhooks(webhooks):
    def handle_credentials(self, state, message):
        global admin_url
        credential_exchange_id = message["credential_exchange_id"]
        s_print(
            "Credential: state=",
            state,
            ", credential_exchange_id=",
            credential_exchange_id,
        )

        if state == "offer_received":
            print("#15 After receiving credential offer, send credential request")
            resp = requests.post(
                admin_url
                + "/credential_exchange/"
                + credential_exchange_id
                + "/send-request"
            )
            assert resp.status_code == 200
            return ""

        elif state == "stored":
            print("Stored credential in wallet")
            resp = requests.get(admin_url + "/credential/" + message["credential_id"])
            assert resp.status_code == 200
            print("Stored credential:")
            print(resp.text)
            print("credential_id", message["credential_id"])
            print("credential_definition_id", message["credential_definition_id"])
            print("schema_id", message["schema_id"])
            print("credential_request_metadata", message["credential_request_metadata"])

            return ""

        return ""

    def handle_presentations(self, state, message):
        global admin_url
        presentation_exchange_id = message["presentation_exchange_id"]
        presentation_request = message["presentation_request"]

        s_print(
            "Presentation: state=",
            state,
            ", presentation_exchange_id=",
            presentation_exchange_id,
        )

        if state == "request_received":
            print(
                "#24 Query for credentials in the wallet that satisfy the proof request"
            )

            # include self-attested attributes (not included in credentials)
            revealed = {}
            self_attested = {}
            predicates = {}

            for referent in presentation_request["requested_attributes"]:

                # select credentials to provide for the proof
                creds = requests.get(
                    admin_url
                    + "/presentation_exchange/"
                    + presentation_exchange_id
                    + "/credentials/"
                    + referent
                )
                assert creds.status_code == 200
                credentials = json.loads(creds.text)

                if credentials:
                    revealed[referent] = {
                        "cred_id": credentials[0]["cred_info"]["referent"],
                        "revealed": True,
                    }
                else:
                    self_attested[referent] = "my self-attested value"

            for referent in presentation_request["requested_predicates"]:

                # select credentials to provide for the proof
                creds = requests.get(
                    admin_url
                    + "/presentation_exchange/"
                    + presentation_exchange_id
                    + "/credentials/"
                    + referent
                )
                assert creds.status_code == 200
                credentials = json.loads(creds.text)

                if credentials:
                    predicates[referent] = {
                        "cred_id": credentials[0]["cred_info"]["referent"],
                        "revealed": True,
                    }

            print("#25 Generate the proof")
            proof = {
                "name": presentation_request["name"],
                "version": presentation_request["version"],
                "requested_predicates": predicates,
                "requested_attributes": revealed,
                "self_attested_attributes": self_attested,
            }
            print("#26 Send the proof to X")
            resp = requests.post(
                admin_url
                + "/presentation_exchange/"
                + presentation_exchange_id
                + "/send_presentation",
                json=proof,
            )
            assert resp.status_code == 200

            return ""

        return ""


def main():
    if run_mode == "docker":
        #genesis = requests.get("http://host.docker.internal:9000/genesis").text
        genesis_url = "http://host.docker.internal:9000/genesis"
    else:
        #with open("local-genesis.txt", "r") as genesis_file:
        #    genesis = genesis_file.read()
        genesis_url = "http://localhost:9000/genesis"

    # TODO seed from input parameter; optionally register the DID
    rand_name = str(random.randint(100000, 999999))
    seed = ("my_seed_000000000000000000000000" + rand_name)[-32:]
    alias = "Alice Agent"
    register_did = False  # Alice doesn't need to register her did
    if register_did:
        print("Registering", alias, "with seed", seed)
        ledger_url = "http://" + external_host + ":9000"
        headers = {"accept": "application/json"}
        data = {"alias": alias, "seed": seed, "role": "TRUST_ANCHOR"}
        resp = requests.post(ledger_url + "/register", json=data)
        assert resp.status_code == 200
        nym_info = resp.text
        print(nym_info)

    # run app and respond to agent webhook callbacks (run in background)
    g_vars = globals()
    webhook_thread = background_hook_thread(urls, g_vars)
    time.sleep(3.0)
    print("Web hooks is running!")

    print("#7 Provision an agent and wallet, get back configuration details")
    # start agent sub-process
    endpoint_url = "http://" + internal_host + ":" + str(in_port_1)
    wallet_name = "alice" + rand_name
    wallet_key = "alice" + rand_name
    python_path = ".."
    webhook_url = "http://" + external_host + ":" + str(webhook_port) + "/webhooks"
    (agent_proc, t1, t2) = start_agent_subprocess(
        "alice",
        genesis_url,
        seed,
        endpoint_url,
        in_port_1,
        in_port_2,
        in_port_3,
        admin_port,
        "indy",
        wallet_name,
        wallet_key,
        python_path,
        webhook_url,
        scripts_dir,
        run_subprocess=True,
        use_postgres=False,
    )
    time.sleep(5.0)
    print("Admin url is at:", admin_url)
    print("Endpoint url is at:", endpoint_url)

    try:
        # check swagger content
        resp = requests.get(admin_url + "/api/docs/swagger.json")
        assert resp.status_code == 200
        p = resp.text
        assert "Indy Catalyst Agent" in p

        # respond to an invitation
        print("#9 Input faber.py invitation details")
        details = input("invite details: ")
        resp = requests.post(
            admin_url + "/connections/receive-invitation", json=details
        )
        assert resp.status_code == 200
        connection = json.loads(resp.text)
        print("invitation response:", connection)
        conn_id = connection["connection_id"]

        time.sleep(3.0)
        option = input("(3) Send Message (X) Exit? [3/X]")
        while option != "X" and option != "x":
            if option == "3":
                msg = input("Enter message:")
                resp = requests.post(
                    admin_url + "/connections/" + conn_id + "/send-message",
                    json={"content": msg},
                )
                assert resp.status_code == 200

            option = input("(3) Send Message (X) Exit? [3/X]")

    except Exception:
        print_exc()
    finally:
        if agent_proc:
            time.sleep(2.0)
            agent_proc.terminate()
            try:
                agent_proc.wait(timeout=0.5)
                print("== subprocess exited with rc =", agent_proc.returncode)
            except subprocess.TimeoutExpired:
                print("subprocess did not terminate in time")
        sys.exit()


if __name__ == "__main__":
    main()
