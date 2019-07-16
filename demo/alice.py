import asyncio
import json
import logging
import os
import sys

from .agent import DemoAgent, default_genesis_txns
from .utils import log_json, log_msg, log_status, log_timer, prompt, prompt_loop

LOGGER = logging.getLogger(__name__)

AGENT_PORT = int(sys.argv[1])

TIMING = False


class AliceAgent(DemoAgent):
    def __init__(self, http_port: int, admin_port: int, **kwargs):
        super().__init__("Alice Agent", http_port, admin_port, prefix="Alice", **kwargs)
        self.connection_id = None
        self._connection_ready = asyncio.Future()
        self.cred_state = {}

    async def detect_connection(self):
        await self._connection_ready

    @property
    def connection_ready(self):
        return self._connection_ready.done() and self._connection_ready.result()

    async def handle_connections(self, message):
        if message["connection_id"] == self.connection_id:
            if message["state"] == "active" and not self._connection_ready.done():
                self.log("Connected")
                self._connection_ready.set_result(True)

    async def handle_credentials(self, message):
        state = message["state"]
        credential_exchange_id = message["credential_exchange_id"]
        prev_state = self.cred_state.get(credential_exchange_id)
        if prev_state == state:
            return  # ignore
        self.cred_state[credential_exchange_id] = state

        self.log(
            "Credential: state =",
            state,
            ", credential_exchange_id =",
            credential_exchange_id,
        )

        if state == "offer_received":
            log_status("#15 After receiving credential offer, send credential request")
            await self.admin_POST(
                f"/credential_exchange/{credential_exchange_id}/send-request"
            )

        elif state == "stored":
            self.log("Stored credential in wallet")
            cred_id = message["credential_id"]
            resp = await self.admin_GET(f"/credential/{cred_id}")
            log_json(resp, label="Credential details:")
            log_json(
                message["credential_request_metadata"],
                label="Credential request metadata:",
            )
            self.log("credential_id", message["credential_id"])
            self.log("credential_definition_id", message["credential_definition_id"])
            self.log("schema_id", message["schema_id"])

    async def handle_presentations(self, message):
        state = message["state"]
        presentation_exchange_id = message["presentation_exchange_id"]
        presentation_request = message["presentation_request"]

        log_msg(
            "Presentation: state =",
            state,
            ", presentation_exchange_id =",
            presentation_exchange_id,
        )

        if state == "request_received":
            log_status(
                "#24 Query for credentials in the wallet that satisfy the proof request"
            )

            # include self-attested attributes (not included in credentials)
            revealed = {}
            self_attested = {}
            predicates = {}

            for referent in presentation_request["requested_attributes"]:

                # select credentials to provide for the proof
                credentials = await self.admin_GET(
                    f"/presentation_exchange/{presentation_exchange_id}"
                    + f"/credentials/{referent}"
                )
                if credentials:
                    revealed[referent] = {
                        "cred_id": credentials[0]["cred_info"]["referent"],
                        "revealed": True,
                    }
                else:
                    self_attested[referent] = "my self-attested value"

            for referent in presentation_request["requested_predicates"]:

                # select credentials to provide for the proof
                credentials = await self.admin_GET(
                    f"/presentation_exchange/{presentation_exchange_id}"
                    f"/credentials/{referent}"
                )
                if credentials:
                    predicates[referent] = {
                        "cred_id": credentials[0]["cred_info"]["referent"],
                        "revealed": True,
                    }

            log_status("#25 Generate the proof")
            proof = {
                "name": presentation_request["name"],
                "version": presentation_request["version"],
                "requested_predicates": predicates,
                "requested_attributes": revealed,
                "self_attested_attributes": self_attested,
            }

            log_status("#26 Send the proof to X")
            await self.admin_POST(
                f"/presentation_exchange/{presentation_exchange_id}/send_presentation",
                proof,
            )

    async def handle_basicmessages(self, message):
        self.log("Received message:", message["content"])


async def input_invitation(agent):
    async for details in prompt_loop("Invite details: "):
        if details:
            try:
                json.loads(details)
                break
            except json.JSONDecodeError as e:
                log_msg("Invalid JSON:", str(e))
                pass

    with log_timer("Connect duration:"):
        connection = await agent.admin_POST(
            "/connections/receive-invitation", details, params={"accept": "auto"}
        )
        agent.connection_id = connection["connection_id"]
        log_json(connection, label="Invitation response:")

        await agent.detect_connection()


async def main():

    genesis = await default_genesis_txns()
    if not genesis:
        print("Error retrieving ledger genesis transactions")
        sys.exit(1)

    agent = None
    start_port = AGENT_PORT

    try:
        log_status("#7 Provision an agent and wallet, get back configuration details")
        agent = AliceAgent(start_port, start_port + 1, genesis_data=genesis)
        await agent.listen_webhooks(start_port + 2)

        with log_timer("Startup duration:"):
            await agent.start_process()
        log_msg("Admin url is at:", agent.admin_url)
        log_msg("Endpoint url is at:", agent.endpoint)

        log_status("#9 Input faber.py invitation details")
        await input_invitation(agent)

        async for option in prompt_loop(
            "(3) Send Message (4) Input New Invitation (X) Exit? [3/4/X]: "
        ):
            if option is None or option in "xX":
                break
            elif option == "3":
                msg = await prompt("Enter message: ")
                if msg:
                    await agent.admin_POST(
                        f"/connections/{agent.connection_id}/send-message",
                        {"content": msg},
                    )
            elif option == "4":
                # handle new invitation
                log_status("Input new invitation details")
                await input_invitation(agent)

        if TIMING:
            timing = await agent.fetch_timing()
            if timing:
                for line in agent.format_timing(timing):
                    log_msg(line)

    finally:
        terminated = True
        try:
            if agent:
                await agent.terminate()
        except Exception:
            LOGGER.exception("Error terminating agent:")
            terminated = False

    await asyncio.sleep(0.1)

    if not terminated:
        os._exit(1)


if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        os._exit(1)
