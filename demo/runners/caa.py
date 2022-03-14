import asyncio
# import json
import logging
import os
import sys
# import time

# from aiohttp import ClientError

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runners.agent_container import (  # noqa:E402
    arg_parser,
    create_agent_with_args,
    AriesAgent,
)
# from runners.support.agent import (  # noqa:E402
#     CRED_FORMAT_INDY,
#     CRED_FORMAT_JSON_LD,
#     SIG_TYPE_BLS,
# )
from runners.support.utils import (  # noqa:E402
    # log_msg,
    log_status,
    # prompt,
    # prompt_loop,
)


CRED_PREVIEW_TYPE = "https://didcomm.org/issue-credential/2.0/credential-preview"
SELF_ATTESTED = os.getenv("SELF_ATTESTED")
TAILS_FILE_COUNT = int(os.getenv("TAILS_FILE_COUNT", 100))

logging.basicConfig(level=logging.WARNING)
LOGGER = logging.getLogger(__name__)


class CaaAgent(AriesAgent):
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
            prefix="Caa",
            no_auto=no_auto,
            **kwargs,
        )
        self.connection_id = None
        self._connection_ready = None
        self.cred_state = {}
        # self.cred_attrs = {}

    async def detect_connection(self):
        await self._connection_ready
        self._connection_ready = None

    @property
    def connection_ready(self):
        return self._connection_ready.done() and self._connection_ready.result()

    async def handle_basicmessages(self, message):
        self.log("Received message:", message["content"])


async def main(args):
    caa_agent = await create_agent_with_args(args, ident="caa")

    try:
        log_status(
            "#1 Provision an agent and wallet, get back configuration details"
            + (
                f" (Wallet type: {caa_agent.wallet_type})"
                if caa_agent.wallet_type
                else ""
            )
        )
        agent = CaaAgent(
            "Caa",
            caa_agent.start_port,
            caa_agent.start_port + 1,
            genesis_data=caa_agent.genesis_txns,
            no_auto=caa_agent.no_auto,
            tails_server_base_url=caa_agent.tails_server_base_url,
            timing=caa_agent.show_timing,
            multitenant=caa_agent.multitenant,
            mediation=caa_agent.mediation,
            wallet_type=caa_agent.wallet_type,
            seed=caa_agent.seed,
        )

        caa_agent.public_did = True

        await caa_agent.initialize(
            the_agent=agent,
            # schema_name=caa_schema_name,
            # schema_attrs=caa_schema_attrs,
        )

        print(10000)

    finally:
        terminated = await caa_agent.terminate()

    await asyncio.sleep(0.1)

    if not terminated:
        os._exit(1)

if __name__ == "__main__":
    parser = arg_parser(ident="caa", port=8050)
    args = parser.parse_args()
    # Namespace(aip=20, arg_file=None, cred_type='indy', did_exchange=False, mediation=False, multitenant=False, no_auto=False, port=8050, revocation=False, tails_server_base_url=None, timing=False, wallet_type=None)
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
                "CAA remote debugging to "
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
    print(200) #
    try:
        asyncio.get_event_loop().run_until_complete(main(args))
    except KeyboardInterrupt:
        os._exit(1)
