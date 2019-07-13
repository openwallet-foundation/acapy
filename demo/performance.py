import asyncio
import logging
import os
import random
import sys

from .agent import DemoAgent, default_genesis_txns
from .utils import log_timer, progress

LOGGER = logging.getLogger(__name__)

START_PORT = int(sys.argv[1])

ROUTING = True

TIMING = True


class BaseAgent(DemoAgent):
    def __init__(
        self,
        ident: str,
        port: int,
        timing: bool = TIMING,
        prefix: str = None,
        use_routing: bool = False,
        **kwargs,
    ):
        if prefix is None:
            prefix = ident
        super().__init__(ident, port, port + 1, timing=timing, prefix=prefix, **kwargs)
        self._connection_id = None
        self._connection_ready = None

    @property
    def connection_id(self) -> str:
        return self._connection_id

    @connection_id.setter
    def connection_id(self, conn_id: str):
        self._connection_id = conn_id
        self._connection_ready = asyncio.Future()

    async def get_invite(self, accept: str = "auto"):
        result = await self.admin_POST(
            "/connections/create-invitation", params={"accept": accept}
        )
        self.connection_id = result["connection_id"]
        return result["invitation"]

    async def receive_invite(self, invite, accept: str = "auto"):
        result = await self.admin_POST(
            "/connections/receive-invitation", invite, params={"accept": accept}
        )
        self.connection_id = result["connection_id"]
        return self.connection_id

    async def accept_invite(self, conn_id: str):
        await self.admin_POST(f"/connections/{conn_id}/accept-invitation")

    async def establish_inbound(self, conn_id: str, router_conn_id: str):
        await self.admin_POST(
            f"/connections/{conn_id}/establish-inbound/{router_conn_id}"
        )

    async def detect_connection(self):
        if not self._connection_ready:
            raise Exception("No connection to await")
        await self._connection_ready

    async def handle_connections(self, payload):
        if payload["connection_id"] == self.connection_id:
            if payload["state"] == "active" and not self._connection_ready.done():
                self.log("Connected")
                self._connection_ready.set_result(True)


class AliceAgent(BaseAgent):
    def __init__(self, port: int, **kwargs):
        super().__init__("Alice", port, seed=None, **kwargs)
        self.credential_state = {}
        self.credential_event = asyncio.Event()
        self.extra_args = ["--auto-respond-credential-offer"]

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


class RoutingAgent(BaseAgent):
    def __init__(self, port: int, **kwargs):
        super().__init__("Router", port, **kwargs)


async def main():

    genesis = await default_genesis_txns()
    if not genesis:
        print("Error retrieving ledger genesis transactions")
        sys.exit(1)

    alice = None
    faber = None
    alice_router = None
    run_timer = log_timer("Total runtime:")
    run_timer.start()

    try:
        start_port = START_PORT

        alice = AliceAgent(start_port, genesis_data=genesis)
        await alice.listen_webhooks(start_port + 2)

        faber = FaberAgent(start_port + 3, genesis_data=genesis)
        await faber.listen_webhooks(start_port + 5)
        await faber.register_did()

        if ROUTING:
            alice_router = RoutingAgent(start_port + 6, genesis_data=genesis)
            await alice_router.listen_webhooks(start_port + 8)
            await alice_router.register_did()

        with log_timer("Startup duration:"):
            if alice_router:
                await alice_router.start_process()
            await alice.start_process()
            await faber.start_process()

        with log_timer("Publish duration:"):
            await faber.publish_defs()

        with log_timer("Connect duration:"):
            if ROUTING:
                router_invite = await alice_router.get_invite()
                alice_router_conn_id = await alice.receive_invite(router_invite)
                await asyncio.wait_for(alice.detect_connection(), 30)

            invite = await faber.get_invite()

            if ROUTING:
                conn_id = await alice.receive_invite(invite, accept="manual")
                await alice.establish_inbound(conn_id, alice_router_conn_id)
                await alice.accept_invite(conn_id)
                await asyncio.wait_for(alice.detect_connection(), 30)
            else:
                await alice.receive_invite(invite)

            await asyncio.wait_for(faber.detect_connection(), 30)

        if TIMING:
            await alice.reset_timing()
            await faber.reset_timing()
            if ROUTING:
                await alice_router.reset_timing()

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
        batch_timer = faber.log_timer(f"Started {batch_size} credential exchanges in ")
        batch_timer.start()

        async def check_received(agent, issue_count, pb):
            reported = 0
            iter_pb = iter(pb) if pb else None
            while True:
                pending, total = agent.check_received_creds()
                if iter_pb and total > reported:
                    try:
                        while next(iter_pb) < total:
                            pass
                    except StopIteration:
                        iter_pb = None
                reported = total
                if total == issue_count and not pending:
                    break
                await asyncio.wait_for(agent.update_creds(), 30)

        with progress() as pb:
            receive_task = None
            try:
                issue_pg = pb(range(issue_count), label="Issuing credentials")
                receive_pg = pb(range(issue_count), label="Receiving credentials")
                receive_task = asyncio.ensure_future(
                    check_received(alice, issue_count, receive_pg)
                )
                with faber.log_timer(
                    f"Done starting {issue_count} credential exchanges in "
                ):
                    for idx in issue_pg:
                        await send()
                        if not (idx + 1) % batch_size and idx < issue_count - 1:
                            batch_timer.reset()

                await receive_task
            except KeyboardInterrupt:
                if receive_task:
                    receive_task.cancel()
                print("Canceled")

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
            if ROUTING:
                timing = await alice_router.fetch_timing()
                if timing:
                    for line in alice_router.format_timing(timing):
                        alice_router.log(line)

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
        try:
            if alice_router:
                await alice_router.terminate()
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
