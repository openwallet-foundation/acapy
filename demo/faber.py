import asyncio
import json
import logging
import os
import random
import sys

from .agent import DemoAgent, default_genesis_txns
from .utils import log_msg, log_timer, prompt, prompt_loop

LOGGER = logging.getLogger(__name__)

AGENT_PORT = int(sys.argv[1])

TIMING = False


class FaberAgent(DemoAgent):
    def __init__(self, http_port: int, admin_port: int, **kwargs):
        super().__init__("Faber Agent", http_port, admin_port, **kwargs)
        self.connection_id = None
        self._connection_active = asyncio.Future()
        self.cred_state = {}

    async def detect_connection(self):
        await self._connection_active

    @property
    def connection_active(self):
        return self._connection_active.done() and self._connection_active.result()

    async def handle_connections(self, message):
        if message["connection_id"] == self.connection_id:
            if message["state"] == "active" and not self._connection_active.done():
                self.log("Connected")
                self._connection_active.set_result(True)

    async def handle_credentials(self, message):
        state = message["state"]
        credential_exchange_id = message["credential_exchange_id"]
        prev_state = self.cred_state.get(credential_exchange_id)
        if prev_state == state:
            return  # ignore
        self.cred_state[credential_exchange_id] = state

        self.log(
            "Credential: state=",
            state,
            ", credential_exchange_id=",
            credential_exchange_id,
        )

        if state == "request_received":
            log_msg("#17 Issue credential to X")
            cred_attrs = {
                "name": "Alice Smith",
                "date": "2018-05-28",
                "degree": "Maths",
                "age": "24",
            }
            await self.admin_POST(
                f"/credential_exchange/{credential_exchange_id}/issue",
                {"credential_values": cred_attrs},
            )

    async def handle_presentations(self, message):
        state = message["state"]

        presentation_exchange_id = message["presentation_exchange_id"]
        self.log(
            "Presentation: state=",
            state,
            ", presentation_exchange_id=",
            presentation_exchange_id,
        )

        if state == "presentation_received":
            log_msg("#27 Process the proof provided by X")
            log_msg("#28 Check if proof is valid")
            proof = await self.admin_POST(
                f"/presentation_exchange/{presentation_exchange_id}/verify_presentation"
            )
            self.log("Proof =", proof["verified"])

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
        log_msg("#1 Provision an agent and wallet, get back configuration details")
        agent = FaberAgent(start_port, start_port + 1, genesis_data=genesis)
        await agent.listen_webhooks(start_port + 2)
        await agent.register_did()

        with log_timer("Startup duration:"):
            await agent.start_process()

        log_msg("Started up")
        log_msg("Admin url is at:", agent.admin_url)
        log_msg("Endpoint url is at:", agent.endpoint)

        # Create a schema
        log_msg("#3 Create a new schema on the ledger")
        with log_timer("Publish schema duration:"):
            version = format(
                "%d.%d.%d"
                % (
                    random.randint(1, 101),
                    random.randint(1, 101),
                    random.randint(1, 101),
                )
            )
            schema_body = {
                "schema_name": "degree schema",
                "schema_version": version,
                "attributes": ["name", "date", "degree", "age"],
            }
            schema_response = await agent.admin_POST("/schemas", schema_body)
        # log_msg("Schema:", json.dumps(schema_response))
        schema_id = schema_response["schema_id"]
        log_msg("Schema ID:", schema_id)

        # Create a cred def for the schema
        log_msg("#4 Create a new credential definition on the ledger")
        with log_timer("Publish credential definition duration:"):
            credential_definition_body = {"schema_id": schema_id}
            credential_definition_response = await agent.admin_POST(
                "/credential-definitions", credential_definition_body
            )
        credential_definition_id = credential_definition_response[
            "credential_definition_id"
        ]
        log_msg("Cred def ID:", credential_definition_id)

        with log_timer("Generate invitation duration:"):
            # Generate an invitation
            log_msg("#5 Create a connection to alice and print out the invite details")
            connection = await agent.admin_POST("/connections/create-invitation")

        agent.connection_id = connection["connection_id"]
        log_msg("Invitation response:", connection)
        log_msg("*****************")
        log_msg("Invitation:")
        log_msg(json.dumps(connection["invitation"]), color=None)
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
                log_msg("#13 Issue credential offer to X")
                offer = {
                    "credential_definition_id": credential_definition_id,
                    "connection_id": agent.connection_id,
                }
                await agent.admin_POST("/credential_exchange/send-offer", offer)

            elif option == "2":
                log_msg("#20 Request proof of degree from alice")
                proof_attrs = [
                    {"name": "name", "restrictions": [{"issuer_did": agent.did}]},
                    {"name": "date", "restrictions": [{"issuer_did": agent.did}]},
                    {"name": "degree", "restrictions": [{"issuer_did": agent.did}]},
                    {"name": "self_attested_thing"},
                ]
                proof_predicates = [{"name": "age", "p_type": ">=", "p_value": 18}]
                proof_request = {
                    "name": "Proof of Education",
                    "version": "1.0",
                    "connection_id": agent.connection_id,
                    "requested_attributes": proof_attrs,
                    "requested_predicates": proof_predicates,
                }
                await agent.admin_POST(
                    "/presentation_exchange/send_request", proof_request
                )

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
