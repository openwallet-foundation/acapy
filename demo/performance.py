import asyncio
import logging
import os
import random
import sys

from .agent import DemoAgent, default_genesis_txns
from .utils import log_timer

LOGGER = logging.getLogger(__name__)

AGENT_PORT = int(sys.argv[1])

TIMING = True


class BaseAgent(DemoAgent):
    def __init__(
        self, ident: str, port: int, timing: bool = TIMING, prefix: str = None, **kwargs
    ):
        if prefix is None:
            prefix = ident
        super().__init__(ident, port, port + 1, timing=timing, prefix=prefix, **kwargs)
        self.connection_id = None
        self.connection_active = asyncio.Future()

    async def detect_connection(self):
        await self.connection_active

    async def handle_connections(self, payload):
        if payload["connection_id"] == self.connection_id:
            if payload["state"] == "active" and not self.connection_active.done():
                self.log("Connected")
                self.connection_active.set_result(True)


class AliceAgent(BaseAgent):
    def __init__(self, port: int, **kwargs):
        super().__init__("Alice", port, **kwargs)
        self.credential_state = {}
        self.credential_event = asyncio.Event()

    async def get_invite(self):
        result = await self.admin_POST("/connections/create-invitation")
        self.connection_id = result["connection_id"]
        return result["invitation"]

    async def handle_credentials(self, payload):
        cred_id = payload["credential_exchange_id"]
        self.credential_state[cred_id] = payload["state"]
        self.credential_event.set()

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
    def __init__(self, port: int, **kwargs):
        super().__init__("Faber", port, **kwargs)
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


async def main():

    genesis = await default_genesis_txns()
    if not genesis:
        print("Error retrieving ledger genesis transactions")
        sys.exit(1)

    alice = None
    faber = None
    run_timer = log_timer("Total runtime:")
    run_timer.start()

    try:
        start_port = AGENT_PORT

        alice = AliceAgent(start_port, genesis_data=genesis)
        await alice.listen_webhooks(start_port + 2)
        await alice.register_did()

        faber = FaberAgent(start_port + 4, genesis_data=genesis)
        await faber.listen_webhooks(start_port + 6)
        await faber.register_did()

        with log_timer("Startup duration:"):
            await alice.start_process()
            alice.log("Started up")

            await faber.start_process()
            faber.log("Started up")

        with log_timer("Publish duration:"):
            await faber.publish_defs()

        with log_timer("Connect duration:"):
            invite = await alice.get_invite()
            await faber.receive_invite(invite)
            await asyncio.wait_for(faber.detect_connection(), 30)

        if TIMING:
            await alice.reset_timing()
            await faber.reset_timing()

        issue_count = 300
        batch_size = 100

        semaphore = asyncio.Semaphore(10)

        async def send():
            await semaphore.acquire()
            asyncio.ensure_future(faber.send_credential()).add_done_callback(
                lambda fut: semaphore.release()
            )

        recv_timer = alice.log_timer(f"Received {issue_count} credentials in ")
        recv_timer.start()

        with faber.log_timer(f"Done starting {issue_count} credential exchanges in "):
            batch_timer = faber.log_timer(
                f"Started {batch_size} credential exchanges in "
            )
            batch_timer.start()

            for idx in range(issue_count):
                await send()
                if not (idx + 1) % batch_size and idx < issue_count - 1:
                    batch_timer.reset()

        while True:
            pending, total = alice.check_received_creds()
            if total == issue_count and not pending:
                break
            await asyncio.wait_for(alice.update_creds(), 30)

        recv_timer.stop()
        avg = recv_timer.duration / issue_count
        alice.log(f"Average time per credential: {avg:.2f}s ({1/avg:.2f}/s)")

        if TIMING:
            timing = await alice.fetch_timing()
            if timing:
                for line in alice.format_timing(timing):
                    alice.log(line)

            timing = await faber.fetch_timing()
            if timing:
                for line in faber.format_timing(timing):
                    faber.log(line)

    finally:
        terminated = True
        try:
            if alice:
                await alice.terminate()
        except Exception:
            LOGGER.exception("Error terminating agent:")
            terminated = False
        try:
            if faber:
                await faber.terminate()
        except Exception:
            LOGGER.exception("Error terminating agent:")
            terminated = False

    run_timer.stop()
    await asyncio.sleep(0.1)

    if not terminated:
        os._exit(1)


if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        os._exit(1)
