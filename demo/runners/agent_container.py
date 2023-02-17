import argparse
import asyncio
import json
import logging
import os
import random
import sys
import time
import yaml

from qrcode import QRCode

from aiohttp import ClientError

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runners.support.agent import (  # noqa:E402
    DemoAgent,
    default_genesis_txns,
    start_mediator_agent,
    connect_wallet_to_mediator,
    start_endorser_agent,
    connect_wallet_to_endorser,
    CRED_FORMAT_INDY,
    CRED_FORMAT_JSON_LD,
    DID_METHOD_KEY,
    KEY_TYPE_BLS,
)
from runners.support.utils import (  # noqa:E402
    check_requires,
    log_json,
    log_msg,
    log_status,
    log_timer,
)


CRED_PREVIEW_TYPE = "https://didcomm.org/issue-credential/2.0/credential-preview"
SELF_ATTESTED = os.getenv("SELF_ATTESTED")
TAILS_FILE_COUNT = int(os.getenv("TAILS_FILE_COUNT", 100))

logging.basicConfig(level=logging.WARNING)
LOGGER = logging.getLogger(__name__)


class AriesAgent(DemoAgent):
    def __init__(
        self,
        ident: str,
        http_port: int,
        admin_port: int,
        prefix: str = "Aries",
        no_auto: bool = False,
        seed: str = None,
        aip: int = 20,
        endorser_role: str = None,
        revocation: bool = False,
        **kwargs,
    ):
        super().__init__(
            ident,
            http_port,
            admin_port,
            prefix=prefix,
            seed=seed,
            aip=aip,
            endorser_role=endorser_role,
            revocation=revocation,
            extra_args=(
                []
                if no_auto
                else [
                    "--auto-accept-invites",
                    "--auto-accept-requests",
                    "--auto-store-credential",
                ]
            ),
            **kwargs,
        )
        self.connection_id = None
        self._connection_ready = None
        self.cred_state = {}
        # define a dict to hold credential attributes
        self.last_credential_received = None
        self.last_proof_received = None

    async def detect_connection(self):
        await self._connection_ready
        self._connection_ready = None

    @property
    def connection_ready(self):
        return self._connection_ready.done() and self._connection_ready.result()

    async def handle_oob_invitation(self, message):
        print("handle_oob_invitation()")
        pass

    async def handle_out_of_band(self, message):
        print("handle_out_of_band()")
        pass

    async def handle_connection_reuse(self, message):
        # we are reusing an existing connection, set our status to the existing connection
        if not self._connection_ready.done():
            self.connection_id = message["connection_id"]
            self.log("Connected")
            self._connection_ready.set_result(True)

    async def handle_connection_reuse_accepted(self, message):
        # we are reusing an existing connection, set our status to the existing connection
        if not self._connection_ready.done():
            self.connection_id = message["connection_id"]
            self.log("Connected")
            self._connection_ready.set_result(True)

    async def handle_connections(self, message):
        # a bit of a hack, but for the mediator connection self._connection_ready
        # will be None
        if not self._connection_ready:
            return
        conn_id = message["connection_id"]

        # inviter:
        if message.get("state") == "invitation":
            self.connection_id = conn_id

        # invitee:
        if (not self.connection_id) and message["rfc23_state"] == "invitation-received":
            self.connection_id = conn_id

        if conn_id == self.connection_id:
            # inviter or invitee:
            if message["rfc23_state"] in ["completed", "response-sent"]:
                if not self._connection_ready.done():
                    self.log("Connected")
                    self._connection_ready.set_result(True)

                # setup endorser properties
                self.log("Check for endorser role ...")
                if self.endorser_role:
                    if self.endorser_role == "author":
                        connection_job_role = "TRANSACTION_AUTHOR"
                        # short pause here to avoid race condition (both agents updating the connection role)
                        await asyncio.sleep(2.0)
                    elif self.endorser_role == "endorser":
                        connection_job_role = "TRANSACTION_ENDORSER"
                        # short pause here to avoid race condition (both agents updating the connection role)
                        await asyncio.sleep(1.0)
                    else:
                        connection_job_role = "None"

                    self.log(
                        f"Updating endorser role for connection: {self.connection_id}, {connection_job_role}"
                    )
                    await self.admin_POST(
                        "/transactions/" + self.connection_id + "/set-endorser-role",
                        params={"transaction_my_job": connection_job_role},
                    )

    async def handle_issue_credential(self, message):
        state = message.get("state")
        credential_exchange_id = message["credential_exchange_id"]
        prev_state = self.cred_state.get(credential_exchange_id)
        if prev_state == state:
            return  # ignore
        self.cred_state[credential_exchange_id] = state

        self.log(
            "Credential: state = {}, credential_exchange_id = {}".format(
                state,
                credential_exchange_id,
            )
        )

        if state == "offer_received":
            log_status("#15 After receiving credential offer, send credential request")
            await self.admin_POST(
                f"/issue-credential/records/{credential_exchange_id}/send-request"
            )

        elif state == "credential_acked":
            cred_id = message["credential_id"]
            self.log(f"Stored credential {cred_id} in wallet")
            log_status(f"#18.1 Stored credential {cred_id} in wallet")
            resp = await self.admin_GET(f"/credential/{cred_id}")
            log_json(resp, label="Credential details:")
            log_json(
                message["credential_request_metadata"],
                label="Credential request metadata:",
            )
            self.log("credential_id", message["credential_id"])
            self.log("credential_definition_id", message["credential_definition_id"])
            self.log("schema_id", message["schema_id"])

        elif state == "request_received":
            log_status("#17 Issue credential to X")
            # issue credentials based on the credential_definition_id
            cred_attrs = self.cred_attrs[message["credential_definition_id"]]
            cred_preview = {
                "@type": CRED_PREVIEW_TYPE,
                "attributes": [
                    {"name": n, "value": v} for (n, v) in cred_attrs.items()
                ],
            }
            try:
                cred_ex_rec = await self.admin_POST(
                    f"/issue-credential/records/{credential_exchange_id}/issue",
                    {
                        "comment": (
                            f"Issuing credential, exchange {credential_exchange_id}"
                        ),
                        "credential_preview": cred_preview,
                    },
                )
                rev_reg_id = cred_ex_rec.get("revoc_reg_id")
                cred_rev_id = cred_ex_rec.get("revocation_id")
                if rev_reg_id:
                    self.log(f"Revocation registry ID: {rev_reg_id}")
                if cred_rev_id:
                    self.log(f"Credential revocation ID: {cred_rev_id}")
            except ClientError:
                pass

        elif state == "abandoned":
            log_status("Credential exchange abandoned")
            self.log("Problem report message:", message.get("error_msg"))

    async def handle_issue_credential_v2_0(self, message):
        state = message.get("state")
        cred_ex_id = message["cred_ex_id"]
        prev_state = self.cred_state.get(cred_ex_id)
        if prev_state == state:
            return  # ignore
        self.cred_state[cred_ex_id] = state

        self.log(f"Credential: state = {state}, cred_ex_id = {cred_ex_id}")

        if state == "request-received":
            log_status("#17 Issue credential to X")
            # issue credential based on offer preview in cred ex record
            await self.admin_POST(
                f"/issue-credential-2.0/records/{cred_ex_id}/issue",
                {"comment": f"Issuing credential, exchange {cred_ex_id}"},
            )

        elif state == "offer-received":
            log_status("#15 After receiving credential offer, send credential request")
            if message["by_format"]["cred_offer"].get("indy"):
                await self.admin_POST(
                    f"/issue-credential-2.0/records/{cred_ex_id}/send-request"
                )
            elif message["by_format"]["cred_offer"].get("ld_proof"):
                holder_did = await self.admin_POST(
                    "/wallet/did/create",
                    {"method": "key", "options": {"key_type": "bls12381g2"}},
                )
                data = {"holder_did": holder_did["result"]["did"]}
                await self.admin_POST(
                    f"/issue-credential-2.0/records/{cred_ex_id}/send-request", data
                )

        elif state == "done":
            pass
            # Logic moved to detail record specific handler

        elif state == "abandoned":
            log_status("Credential exchange abandoned")
            self.log("Problem report message:", message.get("error_msg"))

    async def handle_issue_credential_v2_0_indy(self, message):
        rev_reg_id = message.get("rev_reg_id")
        cred_rev_id = message.get("cred_rev_id")
        cred_id_stored = message.get("cred_id_stored")

        if cred_id_stored:
            cred_id = message["cred_id_stored"]
            log_status(f"#18.1 Stored credential {cred_id} in wallet")
            cred = await self.admin_GET(f"/credential/{cred_id}")
            log_json(cred, label="Credential details:")
            self.log("credential_id", cred_id)
            self.log("cred_def_id", cred["cred_def_id"])
            self.log("schema_id", cred["schema_id"])
            # track last successfully received credential
            self.last_credential_received = cred

        if rev_reg_id and cred_rev_id:
            self.log(f"Revocation registry ID: {rev_reg_id}")
            self.log(f"Credential revocation ID: {cred_rev_id}")

    async def handle_issue_credential_v2_0_ld_proof(self, message):
        self.log(f"LD Credential: message = {message}")

    async def handle_issuer_cred_rev(self, message):
        pass

    async def handle_present_proof(self, message):
        state = message.get("state")

        presentation_exchange_id = message["presentation_exchange_id"]
        presentation_request = message["presentation_request"]
        self.log(
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
            credentials_by_reft = {}
            revealed = {}
            self_attested = {}
            predicates = {}

            try:
                # select credentials to provide for the proof
                credentials = await self.admin_GET(
                    f"/present-proof/records/{presentation_exchange_id}/credentials"
                )
                if credentials:
                    for row in sorted(
                        credentials,
                        key=lambda c: int(c["cred_info"]["attrs"]["timestamp"]),
                        reverse=True,
                    ):
                        for referent in row["presentation_referents"]:
                            if referent not in credentials_by_reft:
                                credentials_by_reft[referent] = row

                # submit the proof wit one unrevealed revealed attribute
                revealed_flag = False
                for referent in presentation_request["requested_attributes"]:
                    if referent in credentials_by_reft:
                        revealed[referent] = {
                            "cred_id": credentials_by_reft[referent]["cred_info"][
                                "referent"
                            ],
                            "revealed": revealed_flag,
                        }
                        revealed_flag = True
                    else:
                        self_attested[referent] = "my self-attested value"

                for referent in presentation_request["requested_predicates"]:
                    if referent in credentials_by_reft:
                        predicates[referent] = {
                            "cred_id": credentials_by_reft[referent]["cred_info"][
                                "referent"
                            ]
                        }

                log_status("#25 Generate the proof")
                request = {
                    "requested_predicates": predicates,
                    "requested_attributes": revealed,
                    "self_attested_attributes": self_attested,
                }

                log_status("#26 Send the proof to X")
                await self.admin_POST(
                    (
                        "/present-proof/records/"
                        f"{presentation_exchange_id}/send-presentation"
                    ),
                    request,
                )
            except ClientError:
                pass

        elif state == "presentation_received":
            log_status("#27 Process the proof provided by X")
            log_status("#28 Check if proof is valid")
            proof = await self.admin_POST(
                f"/present-proof/records/{presentation_exchange_id}/verify-presentation"
            )
            self.log("Proof =", proof["verified"])

        elif state == "abandoned":
            log_status("Presentation exchange abandoned")
            self.log("Problem report message:", message.get("error_msg"))

    async def handle_present_proof_v2_0(self, message):
        state = message.get("state")
        pres_ex_id = message["pres_ex_id"]
        self.log(f"Presentation: state = {state}, pres_ex_id = {pres_ex_id}")

        if state == "request-received":
            # prover role
            log_status(
                "#24 Query for credentials in the wallet that satisfy the proof request"
            )
            pres_request_indy = message["by_format"].get("pres_request", {}).get("indy")
            pres_request_dif = message["by_format"].get("pres_request", {}).get("dif")
            request = {}

            if not pres_request_dif and not pres_request_indy:
                raise Exception("Invalid presentation request received")

            if pres_request_indy:
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
                        # select only indy credentials
                        creds = [x for x in creds if "cred_info" in x]
                        if "timestamp" in creds[0]["cred_info"]["attrs"]:
                            sorted_creds = sorted(
                                creds,
                                key=lambda c: int(c["cred_info"]["attrs"]["timestamp"]),
                                reverse=True,
                            )
                        else:
                            sorted_creds = creds
                        for row in sorted_creds:
                            for referent in row["presentation_referents"]:
                                if referent not in creds_by_reft:
                                    creds_by_reft[referent] = row

                    # submit the proof wit one unrevealed revealed attribute
                    revealed_flag = False
                    for referent in pres_request_indy["requested_attributes"]:
                        if referent in creds_by_reft:
                            revealed[referent] = {
                                "cred_id": creds_by_reft[referent]["cred_info"][
                                    "referent"
                                ],
                                "revealed": revealed_flag,
                            }
                            revealed_flag = True
                        else:
                            self_attested[referent] = "my self-attested value"

                    for referent in pres_request_indy["requested_predicates"]:
                        if referent in creds_by_reft:
                            predicates[referent] = {
                                "cred_id": creds_by_reft[referent]["cred_info"][
                                    "referent"
                                ]
                            }

                    log_status("#25 Generate the indy proof")
                    indy_request = {
                        "indy": {
                            "requested_predicates": predicates,
                            "requested_attributes": revealed,
                            "self_attested_attributes": self_attested,
                        }
                    }
                    request.update(indy_request)
                except ClientError:
                    pass

            if pres_request_dif:
                try:
                    # select credentials to provide for the proof
                    creds = await self.admin_GET(
                        f"/present-proof-2.0/records/{pres_ex_id}/credentials"
                    )
                    if creds and 0 < len(creds):
                        # select only dif credentials
                        creds = [x for x in creds if "issuanceDate" in x]
                        creds = sorted(
                            creds,
                            key=lambda c: c["issuanceDate"],
                            reverse=True,
                        )
                        records = creds
                    else:
                        records = []

                    log_status("#25 Generate the dif proof")
                    dif_request = {
                        "dif": {},
                    }
                    # specify the record id for each input_descriptor id:
                    dif_request["dif"]["record_ids"] = {}
                    for input_descriptor in pres_request_dif["presentation_definition"][
                        "input_descriptors"
                    ]:
                        input_descriptor_schema_uri = []
                        for element in input_descriptor["schema"]:
                            input_descriptor_schema_uri.append(element["uri"])

                        for record in records:
                            if self.check_input_descriptor_record_id(
                                input_descriptor_schema_uri, record
                            ):
                                record_id = record["record_id"]
                                dif_request["dif"]["record_ids"][
                                    input_descriptor["id"]
                                ] = [
                                    record_id,
                                ]
                                break
                    log_msg("presenting ld-presentation:", dif_request)
                    request.update(dif_request)

                    # NOTE that the holder/prover can also/or specify constraints by including the whole proof request
                    # and constraining the presented credentials by adding filters, for example:
                    #
                    # request = {
                    #     "dif": pres_request_dif,
                    # }
                    # request["dif"]["presentation_definition"]["input_descriptors"]["constraints"]["fields"].append(
                    #      {
                    #          "path": [
                    #              "$.id"
                    #          ],
                    #          "purpose": "Specify the id of the credential to present",
                    #          "filter": {
                    #              "const": "https://credential.example.com/residents/1234567890"
                    #          }
                    #      }
                    # )
                    #
                    # (NOTE the above assumes the credential contains an "id", which is an optional field)

                except ClientError:
                    pass

            log_status("#26 Send the proof to X: " + json.dumps(request))
            await self.admin_POST(
                f"/present-proof-2.0/records/{pres_ex_id}/send-presentation",
                request,
            )

        elif state == "presentation-received":
            # verifier role
            log_status("#27 Process the proof provided by X")
            log_status("#28 Check if proof is valid")
            proof = await self.admin_POST(
                f"/present-proof-2.0/records/{pres_ex_id}/verify-presentation"
            )
            self.log("Proof =", proof["verified"])
            self.last_proof_received = proof

        elif state == "abandoned":
            log_status("Presentation exchange abandoned")
            self.log("Problem report message:", message.get("error_msg"))

    async def handle_basicmessages(self, message):
        self.log("Received message:", message["content"])

    async def handle_endorse_transaction(self, message):
        self.log("Received transaction message:", message.get("state"))

    async def handle_revocation_notification(self, message):
        self.log("Received revocation notification message:", message)

    async def generate_invitation(
        self,
        use_did_exchange: bool,
        auto_accept: bool = True,
        display_qr: bool = False,
        reuse_connections: bool = False,
        wait: bool = False,
    ):
        self._connection_ready = asyncio.Future()
        with log_timer("Generate invitation duration:"):
            # Generate an invitation
            log_status(
                "#7 Create a connection to alice and print out the invite details"
            )
            invi_rec = await self.get_invite(
                use_did_exchange,
                auto_accept=auto_accept,
                reuse_connections=reuse_connections,
            )

        if display_qr:
            qr = QRCode(border=1)
            qr.add_data(invi_rec["invitation_url"])
            log_msg(
                "Use the following JSON to accept the invite from another demo agent."
                " Or use the QR code to connect from a mobile agent."
            )
            log_msg(
                json.dumps(invi_rec["invitation"]), label="Invitation Data:", color=None
            )
            qr.print_ascii(invert=True)

        if wait:
            log_msg("Waiting for connection...")
            await self.detect_connection()

        return invi_rec

    async def input_invitation(self, invite_details: dict, wait: bool = False):
        self._connection_ready = asyncio.Future()
        with log_timer("Connect duration:"):
            connection = await self.receive_invite(invite_details)
            log_json(connection, label="Invitation response:")

        if wait:
            log_msg("Waiting for connection...")
            await self.detect_connection()

    async def create_schema_and_cred_def(
        self, schema_name, schema_attrs, revocation, version=None
    ):
        with log_timer("Publish schema/cred def duration:"):
            log_status("#3/4 Create a new schema/cred def on the ledger")
            if not version:
                version = format(
                    "%d.%d.%d"
                    % (
                        random.randint(1, 101),
                        random.randint(1, 101),
                        random.randint(1, 101),
                    )
                )
            (
                _,
                cred_def_id,
            ) = await self.register_schema_and_creddef(  # schema id
                schema_name,
                version,
                schema_attrs,
                support_revocation=revocation,
                revocation_registry_size=TAILS_FILE_COUNT if revocation else None,
            )
            return cred_def_id

    def check_input_descriptor_record_id(
        self, input_descriptor_schema_uri, record
    ) -> bool:
        result = False
        for uri in input_descriptor_schema_uri:
            for record_type in record["type"]:
                if record_type in uri:
                    result = True
                    break
                result = False

        return result


class AgentContainer:
    def __init__(
        self,
        ident: str,
        start_port: int,
        prefix: str = None,
        no_auto: bool = False,
        revocation: bool = False,
        genesis_txns: str = None,
        genesis_txn_list: str = None,
        tails_server_base_url: str = None,
        cred_type: str = CRED_FORMAT_INDY,
        show_timing: bool = False,
        multitenant: bool = False,
        mediation: bool = False,
        use_did_exchange: bool = False,
        wallet_type: str = None,
        public_did: bool = True,
        seed: str = "random",
        aip: int = 20,
        arg_file: str = None,
        endorser_role: str = None,
        reuse_connections: bool = False,
        taa_accept: bool = False,
    ):
        # configuration parameters
        self.genesis_txns = genesis_txns
        self.genesis_txn_list = genesis_txn_list
        self.ident = ident
        self.start_port = start_port
        self.prefix = prefix or ident
        self.no_auto = no_auto
        self.revocation = revocation
        self.tails_server_base_url = tails_server_base_url
        self.cred_type = cred_type
        self.show_timing = show_timing
        self.multitenant = multitenant
        self.mediation = mediation
        self.use_did_exchange = use_did_exchange
        self.wallet_type = wallet_type
        self.public_did = public_did
        self.seed = seed
        self.aip = aip
        self.arg_file = arg_file
        self.endorser_agent = None
        self.endorser_role = endorser_role
        if endorser_role:
            # endorsers and authors need public DIDs (assume cred_type is Indy)
            if endorser_role == "author" or endorser_role == "endorser":
                self.public_did = True
                self.cred_type = CRED_FORMAT_INDY

        self.reuse_connections = reuse_connections
        self.exchange_tracing = False

        # local agent(s)
        self.agent = None
        self.mediator_agent = None
        self.taa_accept = taa_accept

    async def initialize(
        self,
        the_agent: DemoAgent = None,
        schema_name: str = None,
        schema_attrs: list = None,
        create_endorser_agent: bool = False,
    ):
        """Startup agent(s), register DID, schema, cred def as appropriate."""

        if not the_agent:
            log_status(
                "#1 Provision an agent and wallet, get back configuration details"
                + (f" (Wallet type: {self.wallet_type})" if self.wallet_type else "")
            )
            self.agent = AriesAgent(
                self.ident,
                self.start_port,
                self.start_port + 1,
                prefix=self.prefix,
                genesis_data=self.genesis_txns,
                genesis_txn_list=self.genesis_txn_list,
                no_auto=self.no_auto,
                tails_server_base_url=self.tails_server_base_url,
                timing=self.show_timing,
                revocation=self.revocation,
                multitenant=self.multitenant,
                mediation=self.mediation,
                wallet_type=self.wallet_type,
                seed=self.seed,
                aip=self.aip,
                arg_file=self.arg_file,
                endorser_role=self.endorser_role,
            )
        else:
            self.agent = the_agent

        await self.agent.listen_webhooks(self.start_port + 2)

        # create public DID ... UNLESS we are an author ...
        if (not self.endorser_role) or (self.endorser_role == "endorser"):
            if self.public_did and self.cred_type != CRED_FORMAT_JSON_LD:
                await self.agent.register_did(cred_type=CRED_FORMAT_INDY)
                log_msg("Created public DID")

        # if we are endorsing, create the endorser agent first, then we can use the
        # multi-use invitation to auto-connect the agent on startup
        if create_endorser_agent:
            self.endorser_agent = await start_endorser_agent(
                self.start_port + 7,
                self.genesis_txns,
                self.genesis_txn_list,
                use_did_exchange=self.use_did_exchange,
            )
            if not self.endorser_agent:
                raise Exception("Endorser agent returns None :-(")

            # set the endorser invite so the agent can auto-connect
            self.agent.endorser_invite = (
                self.endorser_agent.endorser_multi_invitation_url
            )
            self.agent.endorser_did = self.endorser_agent.endorser_public_did
        else:
            self.endorser_agent = None

        with log_timer("Startup duration:"):
            await self.agent.start_process()

        log_msg("Admin URL is at:", self.agent.admin_url)
        log_msg("Endpoint URL is at:", self.agent.endpoint)

        if self.mediation:
            self.mediator_agent = await start_mediator_agent(
                self.start_port + 4, self.genesis_txns, self.genesis_txn_list
            )
            if not self.mediator_agent:
                raise Exception("Mediator agent returns None :-(")
        else:
            self.mediator_agent = None

        if self.multitenant:
            # create an initial managed sub-wallet (also mediated)
            rand_name = str(random.randint(100_000, 999_999))
            await self.agent.register_or_switch_wallet(
                self.ident + ".initial." + rand_name,
                public_did=self.public_did
                and ((not self.endorser_role) or (not self.endorser_role == "author")),
                webhook_port=None,
                mediator_agent=self.mediator_agent,
                endorser_agent=self.endorser_agent,
                taa_accept=self.taa_accept,
            )
        else:
            if self.mediation:
                # we need to pre-connect the agent to its mediator
                self.agent.log("Connect wallet to mediator ...")
                if not await connect_wallet_to_mediator(
                    self.agent, self.mediator_agent
                ):
                    raise Exception("Mediation setup FAILED :-(")
            if self.endorser_agent:
                self.agent.log("Connect wallet to endorser ...")
                if not await connect_wallet_to_endorser(
                    self.agent, self.endorser_agent
                ):
                    raise Exception("Endorser setup FAILED :-(")
        if self.taa_accept:
            await self.agent.taa_accept()

        # if we are an author, create our public DID here ...
        if (
            self.endorser_role
            and self.endorser_role == "author"
            and self.endorser_agent
        ):
            if self.public_did and self.cred_type != CRED_FORMAT_JSON_LD:
                new_did = await self.agent.admin_POST("/wallet/did/create")
                self.agent.did = new_did["result"]["did"]
                await self.agent.register_did(
                    did=new_did["result"]["did"],
                    verkey=new_did["result"]["verkey"],
                )
                await self.agent.admin_POST("/wallet/did/public?did=" + self.agent.did)
                await asyncio.sleep(3.0)
                log_msg("Created public DID")

        if self.public_did and self.cred_type == CRED_FORMAT_JSON_LD:
            # create did of appropriate type
            data = {"method": DID_METHOD_KEY, "options": {"key_type": KEY_TYPE_BLS}}
            new_did = await self.agent.admin_POST("/wallet/did/create", data=data)
            self.agent.did = new_did["result"]["did"]
            log_msg("Created DID key")

        if schema_name and schema_attrs:
            # Create a schema/cred def
            self.cred_def_id = await self.create_schema_and_cred_def(
                schema_name, schema_attrs
            )

    async def create_schema_and_cred_def(
        self,
        schema_name: str,
        schema_attrs: list,
        version: str = None,
    ):
        if not self.public_did:
            raise Exception("Can't create a schema/cred def without a public DID :-(")
        if self.cred_type == CRED_FORMAT_INDY:
            # need to redister schema and cred def on the ledger
            self.cred_def_id = await self.agent.create_schema_and_cred_def(
                schema_name, schema_attrs, self.revocation, version=version
            )
            return self.cred_def_id
        elif self.cred_type == CRED_FORMAT_JSON_LD:
            # TODO no schema/cred def required
            pass
            return None
        else:
            raise Exception("Invalid credential type:" + self.cred_type)

    async def issue_credential(
        self,
        cred_def_id: str,
        cred_attrs: list,
    ):
        log_status("#13 Issue credential offer to X")

        if self.cred_type == CRED_FORMAT_INDY:
            cred_preview = {
                "@type": CRED_PREVIEW_TYPE,
                "attributes": cred_attrs,
            }
            offer_request = {
                "connection_id": self.agent.connection_id,
                "comment": f"Offer on cred def id {cred_def_id}",
                "auto_remove": False,
                "credential_preview": cred_preview,
                "filter": {"indy": {"cred_def_id": cred_def_id}},
                "trace": self.exchange_tracing,
            }
            cred_exchange = await self.agent.admin_POST(
                "/issue-credential-2.0/send-offer", offer_request
            )

            return cred_exchange

        elif self.cred_type == CRED_FORMAT_JSON_LD:
            # TODO create and send the json-ld credential offer
            pass
            return None

        else:
            raise Exception("Invalid credential type:" + self.cred_type)

    async def receive_credential(
        self,
        cred_def_id: str,
        cred_attrs: list,
    ):
        await asyncio.sleep(1.0)

        # check if the requested credential matches out last received
        if not self.agent.last_credential_received:
            # no credential received
            print("No credential received")
            return False

        if cred_def_id != self.agent.last_credential_received["cred_def_id"]:
            # wrong credential definition
            print("Wrong credential definition id")
            return False

        # check if attribute values match those of issued credential
        wallet_attrs = self.agent.last_credential_received["attrs"]
        matched = True
        for cred_attr in cred_attrs:
            if cred_attr["name"] in wallet_attrs:
                if wallet_attrs[cred_attr["name"]] != cred_attr["value"]:
                    matched = False
            else:
                matched = False

        return matched

    async def request_proof(self, proof_request, explicit_revoc_required: bool = False):
        log_status("#20 Request proof of degree from alice")

        if self.cred_type == CRED_FORMAT_INDY:
            indy_proof_request = {
                "name": proof_request["name"]
                if "name" in proof_request
                else "Proof of stuff",
                "version": proof_request["version"]
                if "version" in proof_request
                else "1.0",
                "requested_attributes": proof_request["requested_attributes"],
                "requested_predicates": proof_request["requested_predicates"],
            }

            if self.revocation:
                non_revoked_supplied = False
                # plug in revocation where requested in the supplied proof request
                non_revoked = {"to": int(time.time())}
                if "non_revoked" in proof_request:
                    indy_proof_request["non_revoked"] = non_revoked
                    non_revoked_supplied = True
                for attr in proof_request["requested_attributes"]:
                    if "non_revoked" in proof_request["requested_attributes"][attr]:
                        indy_proof_request["requested_attributes"][attr][
                            "non_revoked"
                        ] = non_revoked
                        non_revoked_supplied = True
                for pred in proof_request["requested_predicates"]:
                    if "non_revoked" in proof_request["requested_predicates"][pred]:
                        indy_proof_request["requested_predicates"][pred][
                            "non_revoked"
                        ] = non_revoked
                        non_revoked_supplied = True

                if not non_revoked_supplied and not explicit_revoc_required:
                    # else just make it global
                    indy_proof_request["non_revoked"] = non_revoked

            else:
                # make sure we are not leaking non-revoc requests
                if "non_revoked" in proof_request:
                    del proof_request["non_revoked"]
                for attr in proof_request["requested_attributes"]:
                    if "non_revoked" in proof_request["requested_attributes"][attr]:
                        del proof_request["requested_attributes"][attr]["non_revoked"]
                for pred in proof_request["requested_predicates"]:
                    if "non_revoked" in proof_request["requested_predicates"][pred]:
                        del proof_request["requested_predicates"][pred]["non_revoked"]

            log_status(f"  >>> asking for proof for request: {indy_proof_request}")

            proof_request_web_request = {
                "connection_id": self.agent.connection_id,
                "presentation_request": {
                    "indy": indy_proof_request,
                },
                "trace": self.exchange_tracing,
            }
            proof_exchange = await self.agent.admin_POST(
                "/present-proof-2.0/send-request", proof_request_web_request
            )

            return proof_exchange

        elif self.cred_type == CRED_FORMAT_JSON_LD:
            # TODO create and send the json-ld proof request
            pass
            return None

        else:
            raise Exception("Invalid credential type:" + self.cred_type)

    async def verify_proof(self, proof_request):
        await asyncio.sleep(1.0)

        # check if the requested credential matches out last received
        if not self.agent.last_proof_received:
            # no proof received
            print("No proof received")
            return None

        # log_status(f">>> last proof received: {self.agent.last_proof_received}")

        if self.cred_type == CRED_FORMAT_INDY:
            # return verified status
            return self.agent.last_proof_received["verified"]

        elif self.cred_type == CRED_FORMAT_JSON_LD:
            # return verified status
            return self.agent.last_proof_received["verified"]

        else:
            raise Exception("Invalid credential type:" + self.cred_type)

    async def terminate(self):
        """Shut down any running agents."""

        terminated = True
        try:
            if self.endorser_agent:
                log_msg("Shutting down endorser agent ...")
                await self.endorser_agent.terminate()
            if self.mediator_agent:
                log_msg("Shutting down mediator agent ...")
                await self.mediator_agent.terminate()
            if self.agent:
                log_msg("Shutting down agent ...")
                await self.agent.terminate()
        except Exception:
            LOGGER.exception("Error terminating agent:")
            terminated = False

        await asyncio.sleep(3.0)

        return terminated

    async def generate_invitation(
        self,
        auto_accept: bool = True,
        display_qr: bool = False,
        reuse_connections: bool = False,
        wait: bool = False,
    ):
        return await self.agent.generate_invitation(
            self.use_did_exchange,
            auto_accept=auto_accept,
            display_qr=display_qr,
            reuse_connections=reuse_connections,
            wait=wait,
        )

    async def input_invitation(self, invite_details: dict, wait: bool = False):
        return await self.agent.input_invitation(invite_details, wait)

    async def detect_connection(self):
        # no return value, throws an exception if the connection times out
        await self.agent.detect_connection()

    async def register_did(self, did, verkey, role):
        return await self.agent.register_did(
            did=did,
            verkey=verkey,
            role=role,
            cred_type=self.cred_type,
        )

    async def admin_GET(self, path, text=False, params=None) -> dict:
        """
        Execute an admin GET request in the context of the current wallet.

        path = /path/of/request
        text = True if the expected response is text, False if json data
        params = any additional parameters to pass with the request
        """
        return await self.agent.admin_GET(path, text=text, params=params)

    async def admin_POST(self, path, data=None, text=False, params=None) -> dict:
        """
        Execute an admin POST request in the context of the current wallet.

        path = /path/of/request
        data = payload to post with the request
        text = True if the expected response is text, False if json data
        params = any additional parameters to pass with the request
        """
        return await self.agent.admin_POST(path, data=data, text=text, params=params)

    async def admin_PATCH(self, path, data=None, text=False, params=None) -> dict:
        """
        Execute an admin PATCH request in the context of the current wallet.

        path = /path/of/request
        data = payload to post with the request
        text = True if the expected response is text, False if json data
        params = any additional parameters to pass with the request
        """
        return await self.agent.admin_PATCH(path, data=data, text=text, params=params)

    async def admin_PUT(self, path, data=None, text=False, params=None) -> dict:
        """
        Execute an admin PUT request in the context of the current wallet.

        path = /path/of/request
        data = payload to post with the request
        text = True if the expected response is text, False if json data
        params = any additional parameters to pass with the request
        """
        return await self.agent.admin_PUT(path, data=data, text=text, params=params)

    async def agency_admin_GET(self, path, text=False, params=None) -> dict:
        """
        Execute an agency GET request in the context of the base wallet (multitenant only).

        path = /path/of/request
        text = True if the expected response is text, False if json data
        params = any additional parameters to pass with the request
        """
        return await self.agent.agency_admin_GET(path, text=text, params=params)

    async def agency_admin_POST(self, path, data=None, text=False, params=None) -> dict:
        """
        Execute an agency POST request in the context of the base wallet (multitenant only).

        path = /path/of/request
        data = payload to post with the request
        text = True if the expected response is text, False if json data
        params = any additional parameters to pass with the request
        """
        return await self.agent.agency_admin_POST(
            path, data=data, text=text, params=params
        )


def arg_parser(ident: str = None, port: int = 8020):
    """
    Standard command-line arguements.

    "ident", if specified, refers to one of the standard demo personas - alice, faber, acme or performance.
    """
    parser = argparse.ArgumentParser(
        description="Runs a " + (ident or "aries") + " demo agent."
    )
    if not ident:
        parser.add_argument(
            "--ident",
            type=str,
            metavar="<ident>",
            help="Agent identity (label)",
        )
        parser.add_argument(
            "--public-did",
            action="store_true",
            help="Create a public DID for the agent",
        )
    parser.add_argument(
        "--no-auto",
        action="store_true",
        help="Disable auto issuance",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=port,
        metavar=("<port>"),
        help="Choose the starting port number to listen on",
    )
    if (not ident) or (ident != "alice"):
        parser.add_argument(
            "--did-exchange",
            action="store_true",
            help="Use DID-Exchange protocol for connections",
        )
    parser.add_argument(
        "--revocation", action="store_true", help="Enable credential revocation"
    )
    parser.add_argument(
        "--tails-server-base-url",
        type=str,
        metavar=("<tails-server-base-url>"),
        help="Tails server base url",
    )
    if (not ident) or (ident != "alice"):
        parser.add_argument(
            "--cred-type",
            type=str,
            default=CRED_FORMAT_INDY,
            metavar=("<cred-type>"),
            help="Credential type (indy, json-ld)",
        )
    parser.add_argument(
        "--aip",
        type=str,
        default=20,
        metavar=("<api>"),
        help="API level (10 or 20 (default))",
    )
    parser.add_argument(
        "--timing", action="store_true", help="Enable timing information"
    )
    parser.add_argument(
        "--multitenant", action="store_true", help="Enable multitenancy options"
    )
    parser.add_argument(
        "--mediation", action="store_true", help="Enable mediation functionality"
    )
    parser.add_argument(
        "--multi-ledger",
        action="store_true",
        help=(
            "Enable multiple ledger mode, config file can be found "
            "here: ./demo/multi_ledger_config.yml"
        ),
    )
    parser.add_argument(
        "--wallet-type",
        type=str,
        metavar="<wallet-type>",
        help="Set the agent wallet type",
    )
    parser.add_argument(
        "--endorser-role",
        type=str.lower,
        choices=["author", "endorser", "none"],
        metavar="<endorser-role>",
        help=(
            "Specify the role ('author' or 'endorser') which this agent will "
            "participate. Authors will request transaction endorement from an "
            "Endorser. Endorsers will endorse transactions from Authors, and "
            "may write their own  transactions to the ledger. If no role "
            "(or 'none') is specified then the endorsement protocol will not "
            " be used and this agent will write transactions to the ledger "
            "directly."
        ),
    )
    if (not ident) or (ident != "alice"):
        parser.add_argument(
            "--reuse-connections",
            action="store_true",
            help=(
                "Reuse connections by using Faber public key in the invite. "
                "Only applicable for AIP 2.0 (OOB) connections."
            ),
        )
    parser.add_argument(
        "--arg-file",
        type=str,
        metavar="<arg-file>",
        help="Specify a file containing additional aca-py parameters",
    )
    parser.add_argument(
        "--taa-accept",
        action="store_true",
        help="Accept the ledger's TAA, if required",
    )
    return parser


async def create_agent_with_args_list(in_args: list):
    parser = arg_parser()
    args = parser.parse_args(in_args)

    return await create_agent_with_args(args)


async def create_agent_with_args(args, ident: str = None):
    if ("did_exchange" in args and args.did_exchange) and args.mediation:
        raise Exception(
            "DID-Exchange connection protocol is not (yet) compatible with mediation"
        )

    check_requires(args)

    if "revocation" in args and args.revocation:
        tails_server_base_url = args.tails_server_base_url or os.getenv(
            "PUBLIC_TAILS_URL"
        )
    else:
        tails_server_base_url = None

    arg_file = args.arg_file or os.getenv("ACAPY_ARG_FILE")
    arg_file_dict = {}
    if arg_file:
        with open(arg_file) as f:
            arg_file_dict = yaml.safe_load(f)

    # if we don't have a tails server url then guess it
    if ("revocation" in args and args.revocation) and not tails_server_base_url:
        # assume we're running in docker
        tails_server_base_url = (
            "http://" + (os.getenv("DOCKERHOST") or "host.docker.internal") + ":6543"
        )

    if ("revocation" in args and args.revocation) and not tails_server_base_url:
        raise Exception(
            "If revocation is enabled, --tails-server-base-url must be provided"
        )

    multi_ledger_config_path = None
    genesis = None
    if "multi_ledger" in args and args.multi_ledger:
        multi_ledger_config_path = "./demo/multi_ledger_config.yml"
    else:
        genesis = await default_genesis_txns()
    if not genesis and not multi_ledger_config_path:
        print("Error retrieving ledger genesis transactions")
        sys.exit(1)

    agent_ident = ident if ident else (args.ident if "ident" in args else "Aries")

    if "aip" in args:
        aip = int(args.aip)
        if aip not in [
            10,
            20,
        ]:
            raise Exception("Invalid value for aip, should be 10 or 20")
    else:
        aip = 20

    if "cred_type" in args and args.cred_type != CRED_FORMAT_INDY:
        public_did = None
        aip = 20
    elif "cred_type" in args and args.cred_type == CRED_FORMAT_INDY:
        public_did = True
    else:
        public_did = args.public_did if "public_did" in args else None

    cred_type = args.cred_type if "cred_type" in args else None
    log_msg(
        f"Initializing demo agent {agent_ident} with AIP {aip} and credential type {cred_type}"
    )

    reuse_connections = "reuse_connections" in args and args.reuse_connections
    if reuse_connections and aip != 20:
        raise Exception("Can only specify `--reuse-connections` with AIP 2.0")

    agent = AgentContainer(
        genesis_txns=genesis,
        genesis_txn_list=multi_ledger_config_path,
        ident=agent_ident + ".agent",
        start_port=args.port,
        no_auto=args.no_auto,
        revocation=args.revocation if "revocation" in args else False,
        tails_server_base_url=tails_server_base_url,
        show_timing=args.timing,
        multitenant=args.multitenant,
        mediation=args.mediation,
        cred_type=cred_type,
        use_did_exchange=(aip == 20) if ("aip" in args) else args.did_exchange,
        wallet_type=arg_file_dict.get("wallet-type") or args.wallet_type,
        public_did=public_did,
        seed="random" if public_did else None,
        arg_file=arg_file,
        aip=aip,
        endorser_role=args.endorser_role,
        reuse_connections=reuse_connections,
        taa_accept=args.taa_accept,
    )

    return agent


async def test_main(
    start_port: int,
    no_auto: bool = False,
    revocation: bool = False,
    tails_server_base_url: str = None,
    show_timing: bool = False,
    multitenant: bool = False,
    mediation: bool = False,
    use_did_exchange: bool = False,
    wallet_type: str = None,
    cred_type: str = None,
    aip: str = 20,
):
    """Test to startup a couple of agents."""

    faber_container = None
    alice_container = None
    try:
        # initialize the containers
        faber_container = AgentContainer(
            genesis_txns=genesis,
            ident="Faber.agent",
            start_port=start_port,
            no_auto=no_auto,
            revocation=revocation,
            tails_server_base_url=tails_server_base_url,
            show_timing=show_timing,
            multitenant=multitenant,
            mediation=mediation,
            use_did_exchange=use_did_exchange,
            wallet_type=wallet_type,
            public_did=True,
            seed="random",
            cred_type=cred_type,
            aip=aip,
        )
        alice_container = AgentContainer(
            genesis_txns=genesis,
            ident="Alice.agent",
            start_port=start_port + 10,
            no_auto=no_auto,
            revocation=False,
            show_timing=show_timing,
            multitenant=multitenant,
            mediation=mediation,
            use_did_exchange=use_did_exchange,
            wallet_type=wallet_type,
            public_did=False,
            seed=None,
            aip=aip,
        )

        # start the agents - faber gets a public DID and schema/cred def
        await faber_container.initialize(
            schema_name="degree schema",
            schema_attrs=[
                "name",
                "date",
                "degree",
                "grade",
            ],
        )
        await alice_container.initialize()

        # faber create invitation
        invite = await faber_container.generate_invitation()

        # alice accept invitation
        invite_details = invite["invitation"]
        connection = await alice_container.input_invitation(invite_details)

        # wait for faber connection to activate
        await faber_container.detect_connection()
        await alice_container.detect_connection()

        # TODO faber issue credential to alice
        # TODO alice check for received credential

        log_msg("Sleeping ...")
        await asyncio.sleep(3.0)

    except Exception as e:
        LOGGER.exception("Error initializing agent:", e)
        raise (e)

    finally:
        terminated = True
        try:
            # shut down containers at the end of the test
            if alice_container:
                log_msg("Shutting down alice agent ...")
                await alice_container.terminate()
            if faber_container:
                log_msg("Shutting down faber agent ...")
                await faber_container.terminate()
        except Exception as e:
            LOGGER.exception("Error terminating agent:", e)
            terminated = False

    await asyncio.sleep(0.1)

    if not terminated:
        os._exit(1)

    await asyncio.sleep(2.0)
    os._exit(1)


if __name__ == "__main__":
    parser = arg_parser()
    args = parser.parse_args()

    if args.did_exchange and args.mediation:
        raise Exception(
            "DID-Exchange connection protocol is not (yet) compatible with mediation"
        )

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
                "Aries aca-py remote debugging to "
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

    tails_server_base_url = args.tails_server_base_url or os.getenv("PUBLIC_TAILS_URL")

    if args.revocation and not tails_server_base_url:
        raise Exception(
            "If revocation is enabled, --tails-server-base-url must be provided"
        )

    try:
        asyncio.get_event_loop().run_until_complete(
            test_main(
                args.port,
                args.no_auto,
                args.revocation,
                tails_server_base_url,
                args.timing,
                args.multitenant,
                args.mediation,
                args.did_exchange,
                args.wallet_type,
                args.cred_type,
                args.aip,
            )
        )
    except KeyboardInterrupt:
        os._exit(1)
