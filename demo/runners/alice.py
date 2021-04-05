import argparse
import asyncio
import base64
import binascii
import json
import logging
import os
import sys
from urllib.parse import urlparse

from aiohttp import ClientError

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runners.agent_container import (  # noqa:E402
    arg_parser,
    create_agent_with_args,
    AriesAgent,
)
from runners.support.agent import (  # noqa:E402
    DemoAgent,
    default_genesis_txns,
    start_mediator_agent,
    connect_wallet_to_mediator,
)
from runners.support.utils import (  # noqa:E402
    log_json,
    log_msg,
    log_status,
    log_timer,
    prompt,
    prompt_loop,
    require_indy,
)

logging.basicConfig(level=logging.WARNING)
LOGGER = logging.getLogger(__name__)


class AliceAgent(AriesAgent):
    def __init__(
        self,
        ident: str,
        http_port: int,
        admin_port: int,
        no_auto: bool = False,
        **kwargs,
    ):
        super().__init__(
            ident,
            http_port,
            admin_port,
            prefix="Alice",
            no_auto=no_auto,
            seed=None,
            **kwargs,
        )
        self.connection_id = None
        self._connection_ready = None
        self.cred_state = {}

    async def detect_connection(self):
        await self._connection_ready
        self._connection_ready = None

    @property
    def connection_ready(self):
        return self._connection_ready.done() and self._connection_ready.result()

    async def handle_connections(self, message):
        print(
            self.ident, "handle_connections", message["state"], message["rfc23_state"]
        )
        conn_id = message["connection_id"]
        if (not self.connection_id) and message["rfc23_state"] == "invitation-received":
            print(self.ident, "set connection id", conn_id)
            self.connection_id = conn_id
        if (
            message["connection_id"] == self.connection_id
            and message["rfc23_state"] == "completed"
            and not self._connection_ready.done()
        ):
            self.log("Connected")
            self._connection_ready.set_result(True)

    async def handle_issue_credential_v2_0(self, message):
        state = message["state"]
        cred_ex_id = message["cred_ex_id"]
        prev_state = self.cred_state.get(cred_ex_id)
        if prev_state == state:
            return  # ignore
        self.cred_state[cred_ex_id] = state

        self.log(f"Credential: state = {state}, cred_ex_id {cred_ex_id}")

        if state == "offer-received":
            log_status("#15 After receiving credential offer, send credential request")
            await self.admin_POST(
                f"/issue-credential-2.0/records/{cred_ex_id}/send-request"
            )

        elif state == "done":
            cred_id = message["cred_id_stored"]
            self.log(f"Stored credential {cred_id} in wallet")
            log_status(f"#18.1 Stored credential {cred_id} in wallet")
            cred = await self.admin_GET(f"/credential/{cred_id}")
            log_json(cred, label="Credential details:")
            self.log("credential_id", cred_id)
            self.log("cred_def_id", cred["cred_def_id"])
            self.log("schema_id", cred["schema_id"])

    async def handle_issue_credential_v2_0_indy(self, message):
        cred_req_metadata = message.get("cred_request_metadata")
        if cred_req_metadata:
            log_json(cred_req_metadata, label="Credential request metadata:")

    async def handle_present_proof_v2_0(self, message):
        state = message["state"]
        pres_ex_id = message["pres_ex_id"]
        log_msg("Presentation: state =", state, ", pres_ex_id =", pres_ex_id)

        if state == "request-received":
            log_status(
                "#24 Query for credentials in the wallet that satisfy the proof request"
            )
            pres_request = message["by_format"].get("pres_request", {}).get("indy")

            # include self-attested attributes (not included in credentials)
            creds_by_reft = {}
            revealed = {}
            self_attested = {}
            predicates = {}

            try:
                # select credentials to provide for the proof
                creds = await self.admin_GET(
                    f"/present-proof-2.0/records/{pres_ex_id}/credentials"
                )
                if creds:
                    for row in sorted(
                        creds,
                        key=lambda c: int(c["cred_info"]["attrs"]["timestamp"]),
                        reverse=True,
                    ):
                        for referent in row["presentation_referents"]:
                            if referent not in creds_by_reft:
                                creds_by_reft[referent] = row

                for referent in pres_request["requested_attributes"]:
                    if referent in creds_by_reft:
                        revealed[referent] = {
                            "cred_id": creds_by_reft[referent]["cred_info"]["referent"],
                            "revealed": True,
                        }
                    else:
                        self_attested[referent] = "my self-attested value"

                for referent in pres_request["requested_predicates"]:
                    if referent in creds_by_reft:
                        predicates[referent] = {
                            "cred_id": creds_by_reft[referent]["cred_info"]["referent"]
                        }

                log_status("#25 Generate the proof")
                request = {
                    "indy": {
                        "requested_predicates": predicates,
                        "requested_attributes": revealed,
                        "self_attested_attributes": self_attested,
                    }
                }

                log_status("#26 Send the proof to X")
                await self.admin_POST(
                    f"/present-proof-2.0/records/{pres_ex_id}/send-presentation",
                    request,
                )
            except ClientError:
                pass

    async def handle_basicmessages(self, message):
        self.log("Received message:", message["content"])


async def input_invitation(agent):
    async for details in prompt_loop("Invite details: "):
        b64_invite = None
        try:
            url = urlparse(details)
            query = url.query
            if query and "c_i=" in query:
                pos = query.index("c_i=") + 4
                b64_invite = query[pos:]
            elif query and "oob=" in query:
                pos = query.index("oob=") + 4
                b64_invite = query[pos:]
            else:
                b64_invite = details
        except ValueError:
            b64_invite = details

        if b64_invite:
            try:
                padlen = 4 - len(b64_invite) % 4
                if padlen <= 2:
                    b64_invite += "=" * padlen
                invite_json = base64.urlsafe_b64decode(b64_invite)
                details = invite_json.decode("utf-8")
            except binascii.Error:
                pass
            except UnicodeDecodeError:
                pass

        if details:
            try:
                details = json.loads(details)
                break
            except json.JSONDecodeError as e:
                log_msg("Invalid invitation:", str(e))

    with log_timer("Connect duration:"):
        connection = await agent.input_invitation(details, wait=True)


async def main(args):
    alice_agent = await create_agent_with_args(args, ident="alice")

    try:
        log_status(
            "#7 Provision an agent and wallet, get back configuration details"
            + (
                f" (Wallet type: {alice_agent.wallet_type})"
                if alice_agent.wallet_type
                else ""
            )
        )
        agent = AliceAgent(
            "alice.agent",
            alice_agent.start_port,
            alice_agent.start_port + 1,
            genesis_data=alice_agent.genesis_txns,
            no_auto=alice_agent.no_auto,
            timing=alice_agent.show_timing,
            multitenant=alice_agent.multitenant,
            mediation=alice_agent.mediation,
            wallet_type=alice_agent.wallet_type,
        )

        await alice_agent.initialize(the_agent=agent)

        log_status("#9 Input faber.py invitation details")
        await input_invitation(alice_agent)

        options = "    (3) Send Message\n" "    (4) Input New Invitation\n"
        if alice_agent.multitenant:
            options += "    (W) Create and/or Enable Wallet\n"
        options += "    (X) Exit?\n[3/4/{}X] ".format(
            "W/" if alice_agent.multitenant else "",
        )
        async for option in prompt_loop(options):
            if option is not None:
                option = option.strip()

            if option is None or option in "xX":
                break

            elif option in "wW" and alice_agent.multitenant:
                target_wallet_name = await prompt("Enter wallet name: ")
                include_subwallet_webhook = await prompt(
                    "(Y/N) Create sub-wallet webhook target: "
                )
                if include_subwallet_webhook.lower() == "y":
                    await alice_agent.agent.register_or_switch_wallet(
                        target_wallet_name,
                        webhook_port=alice_agent.agent.get_new_webhook_port(),
                        mediator_agent=alice_agent.mediator_agent,
                    )
                else:
                    await alice_agent.agent.register_or_switch_wallet(
                        target_wallet_name,
                        mediator_agent=alice_agent.mediator_agent,
                    )

            elif option == "3":
                msg = await prompt("Enter message: ")
                if msg:
                    await alice_agent.agent.admin_POST(
                        f"/connections/{agent.connection_id}/send-message",
                        {"content": msg},
                    )

            elif option == "4":
                # handle new invitation
                log_status("Input new invitation details")
                await input_invitation(alice_agent)

        if alice_agent.show_timing:
            timing = await alice_agent.agent.fetch_timing()
            if timing:
                for line in alice_agent.agent.format_timing(timing):
                    log_msg(line)

    finally:
        terminated = await alice_agent.terminate()

    await asyncio.sleep(0.1)

    if not terminated:
        os._exit(1)


if __name__ == "__main__":
    parser = arg_parser(ident="alice", port=8030)
    args = parser.parse_args()

    ENABLE_PYDEVD_PYCHARM = os.getenv("ENABLE_PYDEVD_PYCHARM", "").lower()
    ENABLE_PYDEVD_PYCHARM = ENABLE_PYDEVD_PYCHARM and ENABLE_PYDEVD_PYCHARM not in (
        "false",
        "0",
    )
    PYDEVD_PYCHARM_HOST = os.getenv("PYDEVD_PYCHARM_HOST", "localhost")
    PYDEVD_PYCHARM_CONTROLLER_PORT = int(
        os.getenv("PYDEVD_PYCHARM_CONTROLLER_PORT", 5001)
    )

    if ENABLE_PYDEVD_PYCHARM:
        try:
            import pydevd_pycharm

            print(
                "Alice remote debugging to "
                f"{PYDEVD_PYCHARM_HOST}:{PYDEVD_PYCHARM_CONTROLLER_PORT}"
            )
            pydevd_pycharm.settrace(
                host=PYDEVD_PYCHARM_HOST,
                port=PYDEVD_PYCHARM_CONTROLLER_PORT,
                stdoutToServer=True,
                stderrToServer=True,
                suspend=False,
            )
        except ImportError:
            print("pydevd_pycharm library was not found")

    require_indy()

    try:
        asyncio.get_event_loop().run_until_complete(main(args))
    except KeyboardInterrupt:
        os._exit(1)
