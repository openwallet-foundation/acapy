import asyncio
import json
import logging
import os
import random
import sys

from .agent import DemoAgent, default_genesis_txns
from .utils import log_json, log_msg, log_status, log_timer, prompt, prompt_loop

LOGGER = logging.getLogger(__name__)

AGENT_PORT = int(sys.argv[1])

TIMING = False


class AcmeAgent(DemoAgent):
    def __init__(self, http_port: int, admin_port: int, **kwargs):
        super().__init__("Acme Agent", http_port, admin_port, prefix="Acme", **kwargs)
        self.connection_id = None
        self._connection_ready = asyncio.Future()
        self.cred_state = {}
        # TODO define a dict to hold credential attributes based on credential_definition_id
        self.cred_attrs = {}

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

        if state == "request_received":
            # TODO issue credentials based on the credential_definition_id
            pass

    async def handle_presentations(self, message):
        state = message["state"]

        presentation_exchange_id = message["presentation_exchange_id"]
        self.log(
            "Presentation: state =",
            state,
            ", presentation_exchange_id =",
            presentation_exchange_id,
        )

        if state == "presentation_received":
            # TODO handle received presentations
            pass

    async def handle_basicmessages(self, message):
        self.log("Received message:", message["content"])


async def main():

    genesis = await default_genesis_txns()
    if not genesis:
        print("Error retrieving ledger genesis transactions")
        sys.exit(1)

    agent = None
    start_port = AGENT_PORT

    try:
        log_status("#1 Provision an agent and wallet, get back configuration details")
        agent = AcmeAgent(start_port, start_port + 1, genesis_data=genesis)
        await agent.listen_webhooks(start_port + 2)
        await agent.register_did()

        with log_timer("Startup duration:"):
            await agent.start_process()
        log_msg("Admin url is at:", agent.admin_url)
        log_msg("Endpoint url is at:", agent.endpoint)

        # Create a schema
        log_status("#3 Create a new schema on the ledger")
        with log_timer("Publish schema duration:"):
            version = format(
                "%d.%d.%d"
                % (
                    random.randint(1, 101),
                    random.randint(1, 101),
                    random.randint(1, 101),
                )
            )
            # TODO define schema
            #(schema_id, credential_definition_id) = await agent.register_schema_and_creddef(
            #    "employee id schema", version, ["employee_id", "name", "date", "position"]
            #    )

        with log_timer("Generate invitation duration:"):
            # Generate an invitation
            log_status(
                "#5 Create a connection to alice and print out the invite details"
            )
            connection = await agent.admin_POST("/connections/create-invitation")

        agent.connection_id = connection["connection_id"]
        log_json(connection, label="Invitation response:")
        log_msg("*****************")
        log_msg(json.dumps(connection["invitation"]), label="Invitation:", color=None)
        log_msg("*****************")

        log_msg("Waiting for connection...")
        await agent.detect_connection()

        async for option in prompt_loop(
            "(1) Issue Credential, (2) Send Proof Request, "
            + "(3) Send Message (X) Exit? [1/2/3/X] "
        ):
            if option in "xX":
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
