import asyncio
import json
import logging
import os
import sys
from aiohttp import ClientError

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa

from runners.agent_container import (  # noqa:E402
    arg_parser,
    create_agent_with_args,
    AriesAgent,
)
from runners.support.utils import (  # noqa:E402
    check_requires,
    log_msg,
    log_status,
    log_timer,
    prompt,
    prompt_loop,
)


CRED_PREVIEW_TYPE = "https://didcomm.org/issue-credential/2.0/credential-preview"
SELF_ATTESTED = os.getenv("SELF_ATTESTED")
TAILS_FILE_COUNT = int(os.getenv("TAILS_FILE_COUNT", 100))

logging.basicConfig(level=logging.WARNING)
LOGGER = logging.getLogger(__name__)


class AcmeAgent(AriesAgent):
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
            prefix="Acme",
            no_auto=no_auto,
            **kwargs,
        )
        self.connection_id = None
        self._connection_ready = None
        self.cred_state = {}
        self.cred_attrs = {}

    async def detect_connection(self):
        await self._connection_ready
        self._connection_ready = None

    @property
    def connection_ready(self):
        return self._connection_ready.done() and self._connection_ready.result()

    async def handle_oob_invitation(self, message):
        pass

    async def handle_connections(self, message):
        print(
            self.ident, "handle_connections", message["state"], message["rfc23_state"]
        )
        conn_id = message["connection_id"]
        if (not self.connection_id) and message["rfc23_state"] == "invitation-sent":
            print(self.ident, "set connection id", conn_id)
            self.connection_id = conn_id
        if (
            message["connection_id"] == self.connection_id
            and message["rfc23_state"] == "completed"
            and (self._connection_ready and not self._connection_ready.done())
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

        self.log(f"Credential: state = {state}, cred_ex_id = {cred_ex_id}")

        if state == "request-received":
            # TODO issue credentials based on offer preview in cred ex record
            pass

    async def handle_issue_credential_v2_0_indy(self, message):
        pass  # employee id schema does not support revocation

    async def handle_present_proof_v2_0(self, message):
        state = message["state"]
        pres_ex_id = message["pres_ex_id"]
        self.log(f"Presentation: state = {state}, pres_ex_id = {pres_ex_id}")

        if state == "presentation-received":
            # TODO handle received presentations
            pass

    async def handle_basicmessages(self, message):
        self.log("Received message:", message["content"])


async def main(args):
    acme_agent = await create_agent_with_args(args, ident="acme")

    try:
        log_status(
            "#1 Provision an agent and wallet, get back configuration details"
            + (
                f" (Wallet type: {acme_agent.wallet_type})"
                if acme_agent.wallet_type
                else ""
            )
        )
        agent = AcmeAgent(
            "acme.agent",
            acme_agent.start_port,
            acme_agent.start_port + 1,
            genesis_data=acme_agent.genesis_txns,
            genesis_txn_list=acme_agent.genesis_txn_list,
            no_auto=acme_agent.no_auto,
            tails_server_base_url=acme_agent.tails_server_base_url,
            timing=acme_agent.show_timing,
            multitenant=acme_agent.multitenant,
            mediation=acme_agent.mediation,
            wallet_type=acme_agent.wallet_type,
            seed=acme_agent.seed,
        )

        acme_agent.public_did = True
        # acme_schema_name = "employee id schema"
        # acme_schema_attrs = ["employee_id", "name", "date", "position"]
        await acme_agent.initialize(
            the_agent=agent,
            # schema_name=acme_schema_name,
            # schema_attrs=acme_schema_attrs,
        )

        # TODO publish schema and cred def

        # generate an invitation for Alice
        await acme_agent.generate_invitation(display_qr=True, wait=True)

        options = (
            "    (1) Issue Credential\n"
            "    (2) Send Proof Request\n"
            "    (3) Send Message\n"
            "    (X) Exit?\n"
            "[1/2/3/X]"
        )
        async for option in prompt_loop(options):
            if option is not None:
                option = option.strip()

            if option is None or option in "xX":
                break

            elif option == "1":
                log_status("#13 Issue credential offer to X")
                # TODO credential offers

            elif option == "2":
                log_status("#20 Request proof of degree from alice")
                # TODO presentation requests

            elif option == "3":
                msg = await prompt("Enter message: ")
                await agent.admin_POST(
                    f"/connections/{agent.connection_id}/send-message", {"content": msg}
                )

        if acme_agent.show_timing:
            timing = await acme_agent.agent.fetch_timing()
            if timing:
                for line in acme_agent.agent.format_timing(timing):
                    log_msg(line)

    finally:
        terminated = await acme_agent.terminate()

    await asyncio.sleep(0.1)

    if not terminated:
        os._exit(1)


if __name__ == "__main__":
    parser = arg_parser(ident="acme", port=8040)
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
                "Acme remote debugging to "
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

    check_requires(args)

    try:
        asyncio.get_event_loop().run_until_complete(main(args))
    except KeyboardInterrupt:
        os._exit(1)
