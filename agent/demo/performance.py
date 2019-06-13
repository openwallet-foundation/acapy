import asyncio
import os
import random
import sys
from timeit import default_timer

import aiohttp

from agent import DemoAgent

# detect runmode and set hostnames accordingly
run_mode = os.getenv("RUNMODE")

AGENT_PORT = int(sys.argv[1])

internal_host = "127.0.0.1"
external_host = "localhost"
scripts_dir = "../scripts/"

if run_mode == "docker":
    internal_host = "host.docker.internal"
    external_host = "host.docker.internal"
    scripts_dir = "scripts/"


class BaseAgent(DemoAgent):
    def __init__(self, ident: str, port: int, genesis: str = None):
        super().__init__(
            ident, port, port + 1, internal_host, external_host, genesis=genesis
        )
        self.connection_id = None
        self.connection_active = asyncio.Future()

    async def detect_connection(self):
        await self.connection_active

    async def handle_webhook(self, topic, payload):
        if topic == "connections" and payload["connection_id"] == self.connection_id:
            if payload["state"] == "active" and not self.connection_active.done():
                self.log("Promoted to active")
                self.connection_active.set_result(True)


class AliceAgent(BaseAgent):
    def __init__(self, port: int, genesis: str):
        super().__init__("Alice", port, genesis)
        self.credential_state = {}
        self.credential_event = asyncio.Event()

    async def get_invite(self):
        result = await self.admin_POST("/connections/create-invitation")
        self.connection_id = result["connection_id"]
        return result["invitation"]

    async def handle_webhook(self, topic, payload):
        if topic == "credentials":
            cred_id = payload["credential_exchange_id"]
            self.credential_state[cred_id] = payload["state"]
            self.credential_event.set()
        await super().handle_webhook(topic, payload)

    def check_received_creds(self) -> (int, int):
        self.credential_event.clear()
        pending = 0
        total = len(self.credential_state)
        for result in self.credential_state.values():
            if result != "stored":
                pending += 1
        return pending, total

    async def update_creds(self):
        await self.credential_event.wait()


class FaberAgent(BaseAgent):
    def __init__(self, port: int, genesis):
        super().__init__("Faber", port, genesis)
        self.schema_id = None
        self.credential_definition_id = None

    async def receive_invite(self, invite):
        result = await self.admin_POST("/connections/receive-invitation", invite)
        self.connection_id = result["connection_id"]

    async def publish_defs(self):
        # create a schema
        self.log("Publishing test schema")
        version = format(
            "%d.%d.%d"
            % (random.randint(1, 101), random.randint(1, 101), random.randint(1, 101))
        )
        schema_body = {
            "schema_name": "degree schema",
            "schema_version": version,
            "attributes": ["name", "date", "degree", "age"],
        }
        schema_response = await self.admin_POST("/schemas", schema_body)
        self.schema_id = schema_response["schema_id"]
        self.log(f"Schema ID: {self.schema_id}")

        # create a cred def for the schema
        self.log("Publishing test credential definition")
        credential_definition_body = {"schema_id": self.schema_id}
        credential_definition_response = await self.admin_POST(
            "/credential-definitions", credential_definition_body
        )
        self.credential_definition_id = credential_definition_response[
            "credential_definition_id"
        ]
        self.log(f"Credential Definition ID: {self.credential_definition_id}")

    async def send_credential(self):
        cred_attrs = {
            "name": "Alice Smith",
            "date": "2018-05-28",
            "degree": "Maths",
            "age": "24",
        }
        await self.admin_POST(
            "/credential_exchange/send",
            {
                "credential_values": cred_attrs,
                "connection_id": self.connection_id,
                "credential_definition_id": self.credential_definition_id,
            },
        )


async def test():

    genesis = None

    try:
        if run_mode == "docker":
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://{external_host}:9000/genesis") as resp:
                    genesis = await resp.text()
        else:
            with open("local-genesis.txt", "r") as genesis_file:
                genesis = genesis_file.read()
    finally:
        if not genesis:
            print("Error retrieving ledger genesis transactions")
            return

    alice = None
    faber = None
    init_time = default_timer()

    try:
        start_port = AGENT_PORT

        alice = AliceAgent(start_port, genesis)
        await alice.listen_webhooks(start_port + 2)
        await alice.register_did()

        faber = FaberAgent(start_port + 4, genesis)
        await faber.listen_webhooks(start_port + 6)
        await faber.register_did()

        start_time = default_timer()
        await alice.start_process(scripts_dir=scripts_dir)
        alice.log("Started up")

        await faber.start_process(scripts_dir=scripts_dir)
        faber.log("Started up")

        init_done_time = default_timer()

        print(f"INIT DONE {init_done_time - start_time:.2f}s")

        await faber.publish_defs()

        publish_done_time = default_timer()

        print(f"PUBLISH DONE {publish_done_time - init_done_time:.2f}s")

        invite = await alice.get_invite()
        await faber.receive_invite(invite)

        await asyncio.wait_for(faber.detect_connection(), 5)

        connect_time = default_timer()

        print(f"CONNECTED {connect_time - init_done_time:.2f}s")

        issue_count = 100

        for idx in range(issue_count):
            await faber.send_credential()

        while True:
            pending, total = alice.check_received_creds()
            if total == issue_count and not pending:
                break
            await asyncio.wait_for(alice.update_creds(), 30)

        issued_time = default_timer()

        alice.log(
            f"Received all {total} credentials in {issued_time - connect_time:.2f}s"
        )
        avg = (issued_time - connect_time) / issue_count
        alice.log(f"Average time per credential: {avg:.2f}s")

    finally:
        if alice:
            await alice.terminate()
        if faber:
            await faber.terminate()

    done_time = default_timer()
    print(f"Total runtime: {done_time - init_time:.2f}s")


asyncio.get_event_loop().run_until_complete(test())
print("Done")
