import asyncio
import logging
import os
import random
import sys

import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa

from runners.support.agent import DemoAgent, default_genesis_txns
from runners.support.utils import log_timer, progress, require_indy

LOGGER = logging.getLogger(__name__)


class BaseAgent(DemoAgent):
    def __init__(
        self,
        ident: str,
        port: int,
        prefix: str = None,
        use_routing: bool = False,
        **kwargs,
    ):
        if prefix is None:
            prefix = ident
        super().__init__(ident, port, port + 1, prefix=prefix, **kwargs)
        self._connection_id = None
        self._connection_ready = None
        self.credential_state = {}
        self.credential_event = asyncio.Event()
        self.revocations = []
        self.ping_state = {}
        self.ping_event = asyncio.Event()
        self.sent_pings = set()

    @property
    def connection_id(self) -> str:
        return self._connection_id

    @connection_id.setter
    def connection_id(self, conn_id: str):
        self._connection_id = conn_id
        self._connection_ready = asyncio.Future()

    async def get_invite(self, auto_accept: bool = True):
        result = await self.admin_POST(
            "/connections/create-invitation",
            params={"auto_accept": json.dumps(auto_accept)},
        )
        self.connection_id = result["connection_id"]
        return result["invitation"]

    async def receive_invite(self, invite, auto_accept: bool = True):
        result = await self.admin_POST(
            "/connections/receive-invitation",
            invite,
            params={"auto_accept": json.dumps(auto_accept)},
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

    async def handle_issue_credential(self, payload):
        cred_ex_id = payload["credential_exchange_id"]
        rev_reg_id = payload.get("revoc_reg_id")
        cred_rev_id = payload.get("revocation_id")

        self.credential_state[cred_ex_id] = payload["state"]
        if rev_reg_id and cred_rev_id:
            self.revocations.append((rev_reg_id, cred_rev_id))
        self.credential_event.set()

    async def handle_ping(self, payload):
        thread_id = payload["thread_id"]
        if thread_id in self.sent_pings or (
            payload["state"] == "received"
            and payload["comment"]
            and payload["comment"].startswith("test-ping")
        ):
            self.ping_state[thread_id] = payload["state"]
            self.ping_event.set()

    async def check_received_creds(self) -> (int, int):
        while True:
            self.credential_event.clear()
            pending = 0
            total = len(self.credential_state)
            for result in self.credential_state.values():
                if result != "credential_acked":
                    pending += 1
            if self.credential_event.is_set():
                continue
            return pending, total

    async def update_creds(self):
        await self.credential_event.wait()

    async def check_received_pings(self) -> (int, int):
        while True:
            self.ping_event.clear()
            result = {}
            for thread_id, state in self.ping_state.items():
                if not result.get(state):
                    result[state] = set()
                result[state].add(thread_id)
            if self.ping_event.is_set():
                continue
            return result

    async def update_pings(self):
        await self.ping_event.wait()

    async def send_ping(self, ident: str = None) -> str:
        resp = await self.admin_POST(
            f"/connections/{self.connection_id}/send-ping",
            {"comment": f"test-ping {ident}"},
        )
        self.sent_pings.add(resp["thread_id"])

    def check_task_exception(self, fut: asyncio.Task):
        if fut.done():
            try:
                exc = fut.exception()
            except asyncio.CancelledError as e:
                exc = e
            if exc:
                self.log(f"Task raised exception: {str(exc)}")


class AliceAgent(BaseAgent):
    def __init__(self, port: int, **kwargs):
        super().__init__("Alice", port, seed=None, **kwargs)
        self.extra_args = [
            "--auto-respond-credential-offer",
            "--auto-store-credential",
            "--monitor-ping",
        ]
        self.timing_log = "logs/alice_perf.log"

    async def set_tag_policy(self, cred_def_id, taggables):
        req_body = {"taggables": taggables}
        await self.admin_POST(f"/wallet/tag-policy/{cred_def_id}", req_body)


class FaberAgent(BaseAgent):
    def __init__(self, port: int, **kwargs):
        super().__init__("Faber", port, **kwargs)
        self.schema_id = None
        self.credential_definition_id = None
        self.revocation_registry_id = None

    async def publish_defs(self, support_revocation: bool = False):
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
        credential_definition_body = {
            "schema_id": self.schema_id,
            "support_revocation": support_revocation,
        }
        credential_definition_response = await self.admin_POST(
            "/credential-definitions", credential_definition_body
        )
        self.credential_definition_id = credential_definition_response[
            "credential_definition_id"
        ]
        self.log(f"Credential Definition ID: {self.credential_definition_id}")

        # create revocation registry
        if support_revocation:
            revoc_body = {
                "credential_definition_id": self.credential_definition_id,
            }
            revoc_response = await self.admin_POST(
                "/revocation/create-registry", revoc_body
            )
            self.revocation_registry_id = revoc_response["result"]["revoc_reg_id"]
            self.log(f"Revocation Registry ID: {self.revocation_registry_id}")

    async def send_credential(
        self, cred_attrs: dict, comment: str = None, auto_remove: bool = True
    ):
        cred_preview = {
            "attributes": [{"name": n, "value": v} for (n, v) in cred_attrs.items()]
        }
        await self.admin_POST(
            "/issue-credential/send",
            {
                "connection_id": self.connection_id,
                "cred_def_id": self.credential_definition_id,
                "credential_proposal": cred_preview,
                "comment": comment,
                "auto_remove": auto_remove,
                "revoc_reg_id": self.revocation_registry_id,
            },
        )

    async def revoke_credential(self, cred_ex_id: str):
        await self.admin_POST(
            f"/issue-credential/records/{cred_ex_id}/revoke?publish=true"
        )


class RoutingAgent(BaseAgent):
    def __init__(self, port: int, **kwargs):
        super().__init__("Router", port, **kwargs)


async def main(
    start_port: int,
    threads: int = 20,
    ping_only: bool = False,
    show_timing: bool = False,
    routing: bool = False,
    issue_count: int = 300,
    revoc: bool = False,
):

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
        alice = AliceAgent(start_port, genesis_data=genesis, timing=show_timing)
        await alice.listen_webhooks(start_port + 2)

        faber = FaberAgent(start_port + 3, genesis_data=genesis, timing=show_timing)
        await faber.listen_webhooks(start_port + 5)
        await faber.register_did()

        if routing:
            alice_router = RoutingAgent(
                start_port + 6, genesis_data=genesis, timing=show_timing
            )
            await alice_router.listen_webhooks(start_port + 8)
            await alice_router.register_did()

        with log_timer("Startup duration:"):
            if alice_router:
                await alice_router.start_process()
            await alice.start_process()
            await faber.start_process()

        if not ping_only:
            with log_timer("Publish duration:"):
                await faber.publish_defs(revoc)
                # await alice.set_tag_policy(faber.credential_definition_id, ["name"])

        with log_timer("Connect duration:"):
            if routing:
                router_invite = await alice_router.get_invite()
                alice_router_conn_id = await alice.receive_invite(router_invite)
                await asyncio.wait_for(alice.detect_connection(), 30)

            invite = await faber.get_invite()

            if routing:
                conn_id = await alice.receive_invite(invite, auto_accept=False)
                await alice.establish_inbound(conn_id, alice_router_conn_id)
                await alice.accept_invite(conn_id)
                await asyncio.wait_for(alice.detect_connection(), 30)
            else:
                await alice.receive_invite(invite)

            await asyncio.wait_for(faber.detect_connection(), 30)

        if show_timing:
            await alice.reset_timing()
            await faber.reset_timing()
            if routing:
                await alice_router.reset_timing()

        batch_size = 100

        semaphore = asyncio.Semaphore(threads)

        def done_send(fut: asyncio.Task):
            semaphore.release()
            faber.check_task_exception(fut)

        async def send_credential(index: int):
            await semaphore.acquire()
            comment = f"issue test credential {index}"
            attributes = {
                "name": "Alice Smith",
                "date": "2018-05-28",
                "degree": "Maths",
                "age": "24",
            }
            asyncio.ensure_future(
                faber.send_credential(attributes, comment, not revoc)
            ).add_done_callback(done_send)

        async def check_received_creds(agent, issue_count, pb):
            reported = 0
            iter_pb = iter(pb) if pb else None
            while True:
                pending, total = await agent.check_received_creds()
                complete = total - pending
                if reported == complete:
                    await asyncio.wait_for(agent.update_creds(), 30)
                    continue
                if iter_pb and complete > reported:
                    try:
                        while next(iter_pb) < complete:
                            pass
                    except StopIteration:
                        iter_pb = None
                reported = complete
                if reported == issue_count:
                    break

        async def send_ping(index: int):
            await semaphore.acquire()
            asyncio.ensure_future(faber.send_ping(str(index))).add_done_callback(
                done_send
            )

        async def check_received_pings(agent, issue_count, pb):
            reported = 0
            iter_pb = iter(pb) if pb else None
            while True:
                pings = await agent.check_received_pings()
                complete = sum(len(tids) for tids in pings.values())
                if complete == reported:
                    await asyncio.wait_for(agent.update_pings(), 30)
                    continue
                if iter_pb and complete > reported:
                    try:
                        while next(iter_pb) < complete:
                            pass
                    except StopIteration:
                        iter_pb = None
                reported = complete
                if reported >= issue_count:
                    break

        if ping_only:
            recv_timer = faber.log_timer(f"Completed {issue_count} ping exchanges in")
            batch_timer = faber.log_timer(f"Started {batch_size} ping exchanges in")
        else:
            recv_timer = faber.log_timer(
                f"Completed {issue_count} credential exchanges in"
            )
            batch_timer = faber.log_timer(
                f"Started {batch_size} credential exchanges in"
            )
        recv_timer.start()
        batch_timer.start()

        with progress() as pb:
            receive_task = None
            try:
                if ping_only:
                    issue_pg = pb(range(issue_count), label="Sending pings")
                    receive_pg = pb(range(issue_count), label="Responding pings")
                    check_received = check_received_pings
                    send = send_ping
                    completed = f"Done sending {issue_count} pings in"
                else:
                    issue_pg = pb(range(issue_count), label="Issuing credentials")
                    receive_pg = pb(range(issue_count), label="Receiving credentials")
                    check_received = check_received_creds
                    send = send_credential
                    completed = f"Done starting {issue_count} credential exchanges in"

                issue_task = asyncio.ensure_future(
                    check_received(faber, issue_count, issue_pg)
                )
                issue_task.add_done_callback(faber.check_task_exception)
                receive_task = asyncio.ensure_future(
                    check_received(alice, issue_count, receive_pg)
                )
                receive_task.add_done_callback(alice.check_task_exception)
                with faber.log_timer(completed):
                    for idx in range(0, issue_count):
                        await send(idx + 1)
                        if not (idx + 1) % batch_size and idx < issue_count - 1:
                            batch_timer.reset()

                await issue_task
                await receive_task
            except KeyboardInterrupt:
                if receive_task:
                    receive_task.cancel()
                print("Cancelled")

        recv_timer.stop()
        avg = recv_timer.duration / issue_count
        item_short = "ping" if ping_only else "cred"
        item_long = "ping exchange" if ping_only else "credential"
        faber.log(f"Average time per {item_long}: {avg:.2f}s ({1/avg:.2f}/s)")

        if alice.postgres:
            await alice.collect_postgres_stats(f"{issue_count} {item_short}s")
            for line in alice.format_postgres_stats():
                alice.log(line)
        if faber.postgres:
            await faber.collect_postgres_stats(f"{issue_count} {item_short}s")
            for line in faber.format_postgres_stats():
                faber.log(line)

        if revoc and faber.revocations:
            (rev_reg_id, cred_rev_id) = next(iter(faber.revocations))
            print(
                "Revoking and publishing cred rev id {cred_rev_id} "
                "from rev reg id {rev_reg_id}"
            )

        if show_timing:
            timing = await alice.fetch_timing()
            if timing:
                for line in alice.format_timing(timing):
                    alice.log(line)

            timing = await faber.fetch_timing()
            if timing:
                for line in faber.format_timing(timing):
                    faber.log(line)
            if routing:
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
    import argparse

    parser = argparse.ArgumentParser(
        description="Runs an automated credential issuance performance demo."
    )
    parser.add_argument(
        "-c",
        "--count",
        type=int,
        default=300,
        help="Set the number of credentials to issue",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8030,
        metavar=("<port>"),
        help="Choose the starting port number to listen on",
    )
    parser.add_argument(
        "--ping",
        action="store_true",
        default=False,
        help="Only send ping messages between the agents",
    )
    parser.add_argument(
        "--routing", action="store_true", help="Enable inbound routing demonstration"
    )
    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        default=10,
        help="Set the number of concurrent exchanges to start",
    )
    parser.add_argument(
        "--timing", action="store_true", help="Enable detailed timing report"
    )
    args = parser.parse_args()

    require_indy()

    try:
        asyncio.get_event_loop().run_until_complete(
            main(
                args.port,
                args.threads,
                args.ping,
                args.timing,
                args.routing,
                args.count,
            )
        )
    except KeyboardInterrupt:
        os._exit(1)
