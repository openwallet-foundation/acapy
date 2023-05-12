import base64
import time

import requests
from random_word import RandomWords

r = RandomWords()

FABER_ADMIN_URL = "http://localhost:9011"
ALICE_ADMIN_URL = "http://localhost:9012"
ACME_ADMIN_URL = "http://localhost:9013"
MULTI_ADMIN_URL = "http://localhost:9014"


MEDIATOR_INVITATION_URL = "<paste your connection invitation here>"


def wait_a_bit(secs: int = 1):
    total = secs
    print(f"... wait {total} seconds ...")
    time.sleep(total)


def initialize_mediation(url, headers=None):
    if headers is None:
        headers = {}
    params = {
        "alias": "mediator",
        "auto_accept": "true",
    }
    response = requests.post(
        f"{url}/connections/receive-invitation",
        headers=headers,
        params=params,
        json=data,
    )
    print(f"response = {response}")
    json = response.json()
    print(f"json = {json}")
    mediator_connection_id = json["connection_id"]
    mediator_connection_state = json["state"]
    mediation_id = None

    # let's wait until active, then ask for mediation
    attempts = 0
    while mediator_connection_state != "active" and attempts < 5:
        wait_a_bit(5)
        response = requests.get(
            f"{url}/connections/{mediator_connection_id}",
            headers=headers,
        )
        print(f"response = {response}")
        json = response.json()
        print(f"json = {json}")
        mediator_connection_state = json["state"]
        print(f"mediator_connection_state = {mediator_connection_state}")
        attempts = attempts + 1

    if mediator_connection_state == "active":
        response = requests.post(
            f"{url}/mediation/request/{mediator_connection_id}",
            headers=headers,
            json={},
        )
        print(f"response = {response}")
        mediation_request_json = response.json()
        print(f"mediation request json = {mediation_request_json}")
        mediation_id = mediation_request_json["mediation_id"]
        print(f"mediation_id = {mediation_id}")
        mediation_granted = False
        attempts = 0
        while not mediation_granted and attempts < 5:
            wait_a_bit(5)
            response = requests.get(
                f"{url}/mediation/requests/{mediation_id}",
                headers=headers,
            )
            print(f"response = {response}")
            granted_json = response.json()
            print(f"json = {granted_json}")
            mediation_granted = granted_json["state"] == "granted"
            print(f"mediation_granted = {mediation_granted}")
            attempts = attempts + 1

    return mediator_connection_id, mediation_id


def create_invitation(my_label, alias, mediation_id, url, headers=None):
    if headers is None:
        headers = {}
    data = {
        "my_label": my_label,
    }
    if mediation_id:
        data["mediation_id"] = mediation_id

    params = {
        "alias": alias,
        "auto_accept": "true",
    }

    response = requests.post(
        f"{url}/connections/create-invitation",
        headers=headers,
        params=params,
        json=data,
    )
    print(f"response = {response}")
    json = response.json()
    print(f"create-invitation json = {json}")
    invitation = json["invitation"]
    connection_id = json["connection_id"]
    recipient_keys = json["invitation"]["recipientKeys"]
    return invitation, connection_id, recipient_keys


def receive_invitation(invitation, alias, mediation_id, url, headers=None):
    if headers is None:
        headers = {}
    data = invitation
    params = {
        "alias": alias,
        "auto_accept": "true",
    }
    if mediation_id:
        params["mediation_id"] = mediation_id

    response = requests.post(
        f"{url}/connections/receive-invitation",
        headers=headers,
        json=data,
        params=params,
    )
    print(f"response = {response}")
    json = response.json()
    print(f"receive_invitation json = {json}")
    connection_id = json["connection_id"]
    return connection_id


def fetch_connection(connection_id, url, headers=None):
    if headers is None:
        headers = {}
    response = requests.get(
        f"{url}/connections/{connection_id}",
        headers=headers,
    )
    print(f"response = {response}")
    json = response.json()
    print(f"fetch_connection json = {json}")
    return json["state"] == "active"


def ping_connection(connection_id, alias, url, headers=None):
    if headers is None:
        headers = {}
    response = requests.post(
        f"{url}/connections/{connection_id}/send-ping",
        headers=headers,
        json={"comment": f"{alias} pinging..."},
    )
    print(f"ping_connection = {response}")


def create_tenant(wallet_name, wallet_key, url, headers=None):
    if headers is None:
        headers = {}
    # need to create the tenant and get the token
    data = {
        "key_management_mode": "managed",
        "wallet_dispatch_type": "default",
        "wallet_name": wallet_name,
        "wallet_key": wallet_key,
        "label": wallet_name,
        "wallet_type": "askar",
        "wallet_webhook_urls": [],
    }
    # multi-agent has no security for base wallet, just call multitenancy/wallet
    # to create a new tenant
    response = requests.post(f"{url}/multitenancy/wallet", headers=headers, json=data)
    print(f"response = {response}")
    json = response.json()
    print(f"json = {json}")
    wallet_id = json["wallet_id"]
    token = json["token"]
    _headers = {"Authorization": f"Bearer {token}"}

    return wallet_id, token, _headers


if __name__ == "__main__":
    _url = MEDIATOR_INVITATION_URL
    base64_message = _url.split("=", maxsplit=1)[1]
    base64_bytes = base64_message.encode("ascii")
    message_bytes = base64.b64decode(base64_bytes)
    data = message_bytes.decode("ascii")
    print(f"invitation_block = {data}")

    print("\n... single tenants, initiate mediation ...\n")

    faber_mediation_connection_id, faber_mediation_id = initialize_mediation(
        FABER_ADMIN_URL
    )
    print("faber")
    print(f"  mediation_connection_id={faber_mediation_connection_id}")
    print(f"  mediation_id={faber_mediation_id}")

    alice_mediation_connection_id, alice_mediation_id = initialize_mediation(
        ALICE_ADMIN_URL
    )
    print("alice")
    print(f"  mediation_connection_id={alice_mediation_connection_id}")
    print(f"  mediation_id={alice_mediation_id}")

    print("\n... single tenants, connect ...\n")

    # faber create invitation for alice
    (
        faber_invitation,
        faber_alice_connection_id,
        faber_recipient_keys,
    ) = create_invitation("faber", "alice", faber_mediation_id, FABER_ADMIN_URL)
    alice_faber_connection_id = receive_invitation(
        faber_invitation, "faber", alice_mediation_id, ALICE_ADMIN_URL
    )

    connection_active = False
    while not connection_active:
        wait_a_bit(1)
        connection_active = fetch_connection(faber_alice_connection_id, FABER_ADMIN_URL)

    print("\n... connections active, ping each other ...\n")

    pings = 0
    while connection_active and pings < 10:
        ping_connection(faber_alice_connection_id, "faber", FABER_ADMIN_URL)
        wait_a_bit(1)
        ping_connection(alice_faber_connection_id, "alice", ALICE_ADMIN_URL)
        wait_a_bit(1)
        pings = pings + 1

    print("\n... multitenant create tenant...\n")
    # ok, now let's try with multitenant
    multi_wallet_name = r.get_random_word()
    multi_wallet_id, multi_token, multi_headers = create_tenant(
        multi_wallet_name, "changeme", MULTI_ADMIN_URL
    )

    print("\n... multitenant, initiate mediation ...\n")

    multi_mediation_connection_id, multi_mediation_id = initialize_mediation(
        MULTI_ADMIN_URL, multi_headers
    )
    print("multi")
    print(f"  mediation_connection_id={multi_mediation_connection_id}")
    print(f"  mediation_id={multi_mediation_id}")

    print("\n... multitenant, connect ...\n")
    multi_mediation_id = None
    (
        multi_invitation,
        multi_alice_connection_id,
        multi_recipient_keys,
    ) = create_invitation(
        multi_wallet_name, "alice", multi_mediation_id, MULTI_ADMIN_URL, multi_headers
    )

    alice_multi_connection_id = receive_invitation(
        multi_invitation, multi_wallet_name, alice_mediation_id, ALICE_ADMIN_URL
    )

    connection_active = False
    while not connection_active:
        wait_a_bit(1)
        connection_active = fetch_connection(alice_multi_connection_id, ALICE_ADMIN_URL)

    pings = 0
    while connection_active and pings < 10:
        ping_connection(
            multi_alice_connection_id, "multi", MULTI_ADMIN_URL, multi_headers
        )
        wait_a_bit(1)
        ping_connection(alice_multi_connection_id, "alice", ALICE_ADMIN_URL)
        wait_a_bit(1)
        pings = pings + 1
