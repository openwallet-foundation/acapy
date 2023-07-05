import time

import requests
from random_word import RandomWords

r = RandomWords()

FABER_ADMIN_URL = "http://localhost:9011"
ALICE_ADMIN_URL = "http://localhost:9012"
ACME_ADMIN_URL = "http://localhost:9013"
MULTI_ADMIN_URL = "http://localhost:9014"


def wait_a_bit(secs: int = 1):
    total = secs
    print(f"... wait {total} seconds ...")
    time.sleep(total)


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
    print("\n... single tenants, connect ...\n")

    # faber create invitation for alice
    (
        faber_invitation,
        faber_alice_connection_id,
        faber_recipient_keys,
    ) = create_invitation("faber", "alice", None, FABER_ADMIN_URL)
    alice_faber_connection_id = receive_invitation(
        faber_invitation, "faber", None, ALICE_ADMIN_URL
    )

    connection_active = False
    attempts = 0
    while not connection_active and attempts < 5:
        wait_a_bit(1)
        connection_active = fetch_connection(faber_alice_connection_id, FABER_ADMIN_URL)
        attempts = attempts + 1

    print("\n... connections active, ping each other ...\n")

    pings = 0
    while connection_active and pings < 5:
        ping_connection(faber_alice_connection_id, "faber", FABER_ADMIN_URL)
        wait_a_bit(1)
        ping_connection(alice_faber_connection_id, "alice", ALICE_ADMIN_URL)
        wait_a_bit(1)
        pings = pings + 1

    print("\n... multitenant create tenant(s)...\n")
    # ok, now let's try with multitenant
    multi_one_wallet_name = r.get_random_word()
    multi_one_wallet_id, multi_one_token, multi_one_headers = create_tenant(
        multi_one_wallet_name, "changeme", MULTI_ADMIN_URL
    )

    multi_two_wallet_name = r.get_random_word()
    multi_two_wallet_id, multi_two_token, multi_two_headers = create_tenant(
        multi_two_wallet_name, "changeme", MULTI_ADMIN_URL
    )

    print("\n... multitenant, connect ...\n")
    (
        multi_one_invitation,
        multi_one_alice_connection_id,
        multi_one_recipient_keys,
    ) = create_invitation(
        multi_one_wallet_name, "alice", None, MULTI_ADMIN_URL, multi_one_headers
    )

    alice_multi_one_connection_id = receive_invitation(
        multi_one_invitation, multi_one_wallet_name, None, ALICE_ADMIN_URL
    )

    connection_active = False
    attempts = 0
    while not connection_active and attempts < 5:
        wait_a_bit(1)
        connection_active = fetch_connection(
            alice_multi_one_connection_id, ALICE_ADMIN_URL
        )
        attempts = attempts + 1

    pings = 0
    while connection_active and pings < 5:
        ping_connection(
            multi_one_alice_connection_id,
            multi_one_wallet_name,
            MULTI_ADMIN_URL,
            multi_one_headers,
        )
        wait_a_bit(1)
        ping_connection(alice_multi_one_connection_id, "alice", ALICE_ADMIN_URL)
        wait_a_bit(1)
        pings = pings + 1

    (
        multi_two_invitation,
        multi_two_one_connection_id,
        multi_two_recipient_keys,
    ) = create_invitation(
        multi_two_wallet_name,
        multi_one_wallet_name,
        None,
        MULTI_ADMIN_URL,
        multi_two_headers,
    )

    multi_one_two_connection_id = receive_invitation(
        multi_two_invitation,
        multi_two_wallet_name,
        None,
        MULTI_ADMIN_URL,
        multi_one_headers,
    )

    connection_active = False
    attempts = 0
    while not connection_active and attempts < 5:
        wait_a_bit(1)
        connection_active = fetch_connection(
            multi_one_two_connection_id, MULTI_ADMIN_URL, multi_one_headers
        )
        attempts = attempts + 1

    pings = 0
    while connection_active and pings < 5:
        ping_connection(
            multi_two_one_connection_id,
            multi_two_wallet_name,
            MULTI_ADMIN_URL,
            multi_two_headers,
        )
        wait_a_bit(1)
        ping_connection(
            multi_one_two_connection_id,
            multi_one_wallet_name,
            MULTI_ADMIN_URL,
            multi_one_headers,
        )
        wait_a_bit(1)
        pings = pings + 1
