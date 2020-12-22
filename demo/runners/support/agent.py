import asyncio
import asyncpg
import functools
import json
import logging
import os
import random
import subprocess
import sys
from timeit import default_timer

from aiohttp import (
    web,
    ClientSession,
    ClientRequest,
    ClientResponse,
    ClientError,
    ClientTimeout,
)

from .utils import flatten, log_json, log_msg, log_timer, output_reader

LOGGER = logging.getLogger(__name__)

event_stream_handler = logging.StreamHandler()
event_stream_handler.setFormatter(logging.Formatter("\nEVENT: %(message)s"))

DEBUG_EVENTS = os.getenv("EVENTS")
EVENT_LOGGER = logging.getLogger("event")
EVENT_LOGGER.setLevel(logging.DEBUG if DEBUG_EVENTS else logging.NOTSET)
EVENT_LOGGER.addHandler(event_stream_handler)
EVENT_LOGGER.propagate = False

TRACE_TARGET = os.getenv("TRACE_TARGET")
TRACE_TAG = os.getenv("TRACE_TAG")
TRACE_ENABLED = os.getenv("TRACE_ENABLED")

WEBHOOK_TARGET = os.getenv("WEBHOOK_TARGET")

AGENT_ENDPOINT = os.getenv("AGENT_ENDPOINT")

DEFAULT_POSTGRES = bool(os.getenv("POSTGRES"))
DEFAULT_INTERNAL_HOST = "127.0.0.1"
DEFAULT_EXTERNAL_HOST = "localhost"
DEFAULT_PYTHON_PATH = ".."
PYTHON = os.getenv("PYTHON", sys.executable)

START_TIMEOUT = float(os.getenv("START_TIMEOUT", 30.0))

RUN_MODE = os.getenv("RUNMODE")

GENESIS_URL = os.getenv("GENESIS_URL")
LEDGER_URL = os.getenv("LEDGER_URL")
GENESIS_FILE = os.getenv("GENESIS_FILE")

if RUN_MODE == "docker":
    DEFAULT_INTERNAL_HOST = os.getenv("DOCKERHOST") or "host.docker.internal"
    DEFAULT_EXTERNAL_HOST = DEFAULT_INTERNAL_HOST
    DEFAULT_PYTHON_PATH = "."
elif RUN_MODE == "pwd":
    # DEFAULT_INTERNAL_HOST =
    DEFAULT_EXTERNAL_HOST = os.getenv("DOCKERHOST") or "host.docker.internal"
    DEFAULT_PYTHON_PATH = "."


class repr_json:
    def __init__(self, val):
        self.val = val

    def __repr__(self) -> str:
        if isinstance(self.val, str):
            return self.val
        return json.dumps(self.val, indent=4)


async def default_genesis_txns():
    genesis = None
    try:
        if GENESIS_URL:
            async with ClientSession() as session:
                async with session.get(GENESIS_URL) as resp:
                    genesis = await resp.text()
        elif RUN_MODE == "docker":
            async with ClientSession() as session:
                async with session.get(
                    f"http://{DEFAULT_EXTERNAL_HOST}:9000/genesis"
                ) as resp:
                    genesis = await resp.text()
        elif GENESIS_FILE:
            with open(GENESIS_FILE, "r") as genesis_file:
                genesis = genesis_file.read()
        elif LEDGER_URL:
            async with ClientSession() as session:
                async with session.get(LEDGER_URL.rstrip("/") + "/genesis") as resp:
                    genesis = await resp.text()
        else:
            with open("local-genesis.txt", "r") as genesis_file:
                genesis = genesis_file.read()
    except Exception:
        LOGGER.exception("Error loading genesis transactions:")
    return genesis


class DemoAgent:
    def __init__(
        self,
        ident: str,
        http_port: int,
        admin_port: int,
        internal_host: str = None,
        external_host: str = None,
        genesis_data: str = None,
        seed: str = "random",
        label: str = None,
        color: str = None,
        prefix: str = None,
        tails_server_base_url: str = None,
        timing: bool = False,
        timing_log: str = None,
        postgres: bool = None,
        revocation: bool = False,
        multitenant: bool = False,
        extra_args=None,
        **params,
    ):
        self.ident = ident
        self.http_port = http_port
        self.admin_port = admin_port
        self.internal_host = internal_host or DEFAULT_INTERNAL_HOST
        self.external_host = external_host or DEFAULT_EXTERNAL_HOST
        self.genesis_data = genesis_data
        self.label = label or ident
        self.color = color
        self.prefix = prefix
        self.timing = timing
        self.timing_log = timing_log
        self.postgres = DEFAULT_POSTGRES if postgres is None else postgres
        self.tails_server_base_url = tails_server_base_url
        self.extra_args = extra_args
        self.trace_enabled = TRACE_ENABLED
        self.trace_target = TRACE_TARGET
        self.trace_tag = TRACE_TAG
        self.multitenant = multitenant
        self.external_webhook_target = WEBHOOK_TARGET

        self.admin_url = f"http://{self.internal_host}:{admin_port}"
        if AGENT_ENDPOINT:
            self.endpoint = AGENT_ENDPOINT
        elif RUN_MODE == "pwd":
            self.endpoint = f"http://{self.external_host}".replace(
                "{PORT}", str(http_port)
            )
        else:
            self.endpoint = f"http://{self.external_host}:{http_port}"

        self.webhook_port = None
        self.webhook_url = None
        self.webhook_site = None
        self.params = params
        self.proc = None
        self.client_session: ClientSession = ClientSession()

        rand_name = str(random.randint(100_000, 999_999))
        self.seed = (
            ("my_seed_000000000000000000000000" + rand_name)[-32:]
            if seed == "random"
            else seed
        )
        self.storage_type = params.get("storage_type")
        self.wallet_type = params.get("wallet_type") or "indy"
        self.wallet_name = (
            params.get("wallet_name") or self.ident.lower().replace(" ", "") + rand_name
        )
        self.wallet_key = params.get("wallet_key") or self.ident + rand_name
        self.did = None
        self.wallet_stats = []

        # for multitenancy, storage_type and wallet_type are the same for all wallets
        if self.multitenant:
            self.agency_ident = self.ident
            self.agency_wallet_name = self.wallet_name
            self.agency_wallet_seed = self.seed
            self.agency_wallet_did = self.did
            self.agency_wallet_key = self.wallet_key

    async def get_wallets(self):
        """Get registered wallets of agent (this is an agency call)."""
        wallets = await self.admin_GET("/multitenancy/wallets")
        return wallets

    async def get_public_did(self):
        """Get public did of wallet (called for a sub-wallet)."""
        did = await self.admin_GET("/wallet/did/public")
        return did

    async def register_schema_and_creddef(
        self,
        schema_name,
        version,
        schema_attrs,
        support_revocation: bool = False,
        revocation_registry_size: int = None,
        tag=None,
    ):
        # Create a schema
        schema_body = {
            "schema_name": schema_name,
            "schema_version": version,
            "attributes": schema_attrs,
        }
        schema_response = await self.admin_POST("/schemas", schema_body)
        # log_json(json.dumps(schema_response), label="Schema:")
        schema_id = schema_response["schema_id"]
        log_msg("Schema ID:", schema_id)

        # Create a cred def for the schema
        cred_def_tag = (
            tag if tag else (self.ident + "." + schema_name).replace(" ", "_")
        )
        credential_definition_body = {
            "schema_id": schema_id,
            "support_revocation": support_revocation,
            **{
                "revocation_registry_size": revocation_registry_size
                for _ in [""]
                if support_revocation
            },
            "tag": cred_def_tag,
        }
        credential_definition_response = await self.admin_POST(
            "/credential-definitions", credential_definition_body
        )
        credential_definition_id = credential_definition_response[
            "credential_definition_id"
        ]
        log_msg("Cred def ID:", credential_definition_id)
        return schema_id, credential_definition_id

    def get_agent_args(self):
        result = [
            ("--endpoint", self.endpoint),
            ("--label", self.label),
            "--auto-ping-connection",
            "--auto-respond-messages",
            ("--inbound-transport", "http", "0.0.0.0", str(self.http_port)),
            ("--outbound-transport", "http"),
            ("--admin", "0.0.0.0", str(self.admin_port)),
            "--admin-insecure-mode",
            ("--wallet-type", self.wallet_type),
            ("--wallet-name", self.wallet_name),
            ("--wallet-key", self.wallet_key),
            "--preserve-exchange-records",
            "--auto-provision",
        ]
        if self.multitenant:
            result.extend(
                [
                    "--multitenant",
                    "--multitenant-admin",
                    ("--jwt-secret", "very_secret_secret"),
                ]
            )
        if self.genesis_data:
            result.append(("--genesis-transactions", self.genesis_data))
        if self.seed:
            result.append(("--seed", self.seed))
        if self.storage_type:
            result.append(("--storage-type", self.storage_type))
        if self.timing:
            result.append("--timing")
        if self.timing_log:
            result.append(("--timing-log", self.timing_log))
        if self.postgres:
            result.extend(
                [
                    ("--wallet-storage-type", "postgres_storage"),
                    ("--wallet-storage-config", json.dumps(self.postgres_config)),
                    ("--wallet-storage-creds", json.dumps(self.postgres_creds)),
                ]
            )
        if self.webhook_url:
            result.append(("--webhook-url", self.webhook_url))
        if self.external_webhook_target:
            result.append(("--webhook-url", self.external_webhook_target))
        if self.trace_enabled:
            result.extend(
                [
                    ("--trace",),
                    ("--trace-target", self.trace_target),
                    ("--trace-tag", self.trace_tag),
                    ("--trace-label", self.label + ".trace"),
                ]
            )

        if self.tails_server_base_url:
            result.append(("--tails-server-base-url", self.tails_server_base_url))
        else:
            # set the tracing parameters but don't enable tracing
            result.extend(
                [
                    (
                        "--trace-target",
                        self.trace_target if self.trace_target else "log",
                    ),
                    (
                        "--trace-tag",
                        self.trace_tag if self.trace_tag else "acapy.events",
                    ),
                    ("--trace-label", self.label + ".trace"),
                ]
            )
        if self.extra_args:
            result.extend(self.extra_args)

        return result

    @property
    def prefix_str(self):
        if self.prefix:
            return f"{self.prefix:10s} |"

    async def register_did(
        self,
        ledger_url: str = None,
        alias: str = None,
        did: str = None,
        verkey: str = None,
    ):
        self.log(f"Registering {self.ident} ...")
        if not ledger_url:
            ledger_url = LEDGER_URL
        if not ledger_url:
            ledger_url = f"http://{self.external_host}:9000"
        data = {"alias": alias or self.ident, "role": "TRUST_ANCHOR"}
        if did and verkey:
            data["did"] = did
            data["verkey"] = verkey
        else:
            data["seed"] = self.seed
        async with self.client_session.post(
            ledger_url + "/register", json=data
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Error registering DID, response code {resp.status}")
            nym_info = await resp.json()
            self.did = nym_info["did"]
            if self.multitenant:
                if not self.agency_wallet_did:
                    self.agency_wallet_did = self.did
        self.log(f"Registered DID: {self.did}")

    async def register_or_switch_wallet(self, target_wallet_name, public_did=False):
        self.log(f"Register or switch to wallet {target_wallet_name}")
        if target_wallet_name == self.agency_wallet_name:
            self.ident = self.agency_ident
            self.wallet_name = self.agency_wallet_name
            self.seed = self.agency_wallet_seed
            self.did = self.agency_wallet_did
            self.wallet_key = self.agency_wallet_key
            self.log(f"Switching to AGENCY wallet {target_wallet_name}")
            return False

        # check if wallet exists already
        wallets = await self.agency_admin_GET("/multitenancy/wallets")
        for wallet in wallets["results"]:
            if wallet["settings"]["wallet.name"] == target_wallet_name:
                # if so set local agent attributes
                self.wallet_name = target_wallet_name
                # assume wallet key is wallet name
                self.wallet_key = target_wallet_name
                self.ident = target_wallet_name
                # we can't recover the seed so let's set it to None and see what happens ...
                self.seed = None
                self.log(f"Switching to EXISTING wallet {target_wallet_name}")
                return False

        # if not then create it
        wallet_params = {
            "wallet_key": target_wallet_name,
            "wallet_name": target_wallet_name,
            "wallet_type": self.wallet_type,
            "label": target_wallet_name,
        }
        self.wallet_name = target_wallet_name
        self.wallet_key = target_wallet_name
        self.ident = target_wallet_name
        new_wallet = await self.agency_admin_POST("/multitenancy/wallet", wallet_params)
        self.log("New wallet params:", new_wallet)
        self.managed_wallet_params = new_wallet
        if public_did:
            # assign public did
            new_did = await self.admin_POST("/wallet/did/create")
            self.did = new_did["result"]["did"]
            await self.register_did(
                did=new_did["result"]["did"], verkey=new_did["result"]["verkey"]
            )
            await self.admin_POST("/wallet/did/public?did=" + self.did)
        self.log(f"Created NEW wallet {target_wallet_name}")
        return True

    def handle_output(self, *output, source: str = None, **kwargs):
        end = "" if source else "\n"
        if source == "stderr":
            color = "fg:ansired"
        elif not source:
            color = self.color or "fg:ansiblue"
        else:
            color = None
        log_msg(*output, color=color, prefix=self.prefix_str, end=end, **kwargs)

    def log(self, *msg, **kwargs):
        self.handle_output(*msg, **kwargs)

    def log_json(self, data, label: str = None, **kwargs):
        log_json(data, label=label, prefix=self.prefix_str, **kwargs)

    def log_timer(self, label: str, show: bool = True, **kwargs):
        return log_timer(label, show, logger=self.log, **kwargs)

    def _process(self, args, env, loop):
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            encoding="utf-8",
        )
        loop.run_in_executor(
            None,
            output_reader,
            proc.stdout,
            functools.partial(self.handle_output, source="stdout"),
        )
        loop.run_in_executor(
            None,
            output_reader,
            proc.stderr,
            functools.partial(self.handle_output, source="stderr"),
        )
        return proc

    def get_process_args(self):
        return list(
            flatten(
                ([PYTHON, "-m", "aries_cloudagent", "start"], self.get_agent_args())
            )
        )

    async def start_process(self, python_path: str = None, wait: bool = True):
        my_env = os.environ.copy()
        python_path = DEFAULT_PYTHON_PATH if python_path is None else python_path
        if python_path:
            my_env["PYTHONPATH"] = python_path

        agent_args = self.get_process_args()
        self.log(agent_args)

        # start agent sub-process
        loop = asyncio.get_event_loop()
        self.proc = await loop.run_in_executor(
            None, self._process, agent_args, my_env, loop
        )
        if wait:
            await asyncio.sleep(1.0)
            await self.detect_process()

    def _terminate(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=0.5)
                self.log(f"Exited with return code {self.proc.returncode}")
            except subprocess.TimeoutExpired:
                msg = "Process did not terminate in time"
                self.log(msg)
                raise Exception(msg)

    async def terminate(self):
        loop = asyncio.get_event_loop()
        if self.proc:
            await loop.run_in_executor(None, self._terminate)
        await self.client_session.close()
        if self.webhook_site:
            await self.webhook_site.stop()

    async def listen_webhooks(self, webhook_port):
        self.webhook_port = webhook_port
        if RUN_MODE == "pwd":
            self.webhook_url = f"http://localhost:{str(webhook_port)}/webhooks"
        else:
            self.webhook_url = (
                f"http://{self.external_host}:{str(webhook_port)}/webhooks"
            )
        app = web.Application()
        app.add_routes([web.post("/webhooks/topic/{topic}/", self._receive_webhook)])
        runner = web.AppRunner(app)
        await runner.setup()
        self.webhook_site = web.TCPSite(runner, "0.0.0.0", webhook_port)
        await self.webhook_site.start()

    async def _receive_webhook(self, request: ClientRequest):
        topic = request.match_info["topic"].replace("-", "_")
        payload = await request.json()
        await self.handle_webhook(topic, payload, request.headers)
        return web.Response(status=200)

    async def handle_webhook(self, topic: str, payload, headers: dict):
        if topic != "webhook":  # would recurse
            handler = f"handle_{topic}"
            wallet_id = headers.get("x-wallet-id")
            method = getattr(self, handler, None)
            if method:
                EVENT_LOGGER.debug(
                    "Agent called controller webhook: %s%s%s",
                    handler,
                    (f" for wallet: {wallet_id}" if wallet_id else ""),
                    (f" with payload: \n{repr_json(payload)}\n" if payload else ""),
                )
                asyncio.get_event_loop().create_task(method(payload))
            else:
                log_msg(
                    f"Error: agent {self.ident} "
                    f"has no method {handler} "
                    f"to handle webhook on topic {topic}"
                )

    async def handle_problem_report(self, message):
        self.log(
            f"Received problem report: {message['explain-ltxt']}\n", source="stderr"
        )

    async def handle_revocation_registry(self, message):
        reg_id = message.get("revoc_reg_id", "(undetermined)")
        self.log(f"Revocation registry: {reg_id} state: {message['state']}")

    async def admin_request(
        self, method, path, data=None, text=False, params=None, headers=None
    ) -> ClientResponse:
        params = {k: v for (k, v) in (params or {}).items() if v is not None}
        async with self.client_session.request(
            method, self.admin_url + path, json=data, params=params, headers=headers
        ) as resp:
            resp_text = await resp.text()
            try:
                resp.raise_for_status()
            except Exception as e:
                # try to retrieve and print text on error
                raise Exception(f"Error: {resp_text}") from e
            if not resp_text and not text:
                return None
            if not text:
                try:
                    return json.loads(resp_text)
                except json.JSONDecodeError as e:
                    raise Exception(f"Error decoding JSON: {resp_text}") from e
            return resp_text

    async def agency_admin_GET(
        self, path, text=False, params=None, headers=None
    ) -> ClientResponse:
        if not self.multitenant:
            raise Exception("Error can't call agency admin unless in multitenant mode")
        try:
            EVENT_LOGGER.debug("Controller GET %s request to Agent", path)
            if not headers:
                headers = {}
            response = await self.admin_request(
                "GET", path, None, text, params, headers=headers
            )
            EVENT_LOGGER.debug(
                "Response from GET %s received: \n%s",
                path,
                repr_json(response),
            )
            return response
        except ClientError as e:
            self.log(f"Error during GET {path}: {str(e)}")
            raise

    async def admin_GET(
        self, path, text=False, params=None, headers=None
    ) -> ClientResponse:
        try:
            EVENT_LOGGER.debug("Controller GET %s request to Agent", path)
            if self.multitenant:
                if not headers:
                    headers = {}
                headers["Authorization"] = (
                    "Bearer " + self.managed_wallet_params["token"]
                )
                self.log("GET:", path)
                self.log("Headers:", headers)
            response = await self.admin_request(
                "GET", path, None, text, params, headers=headers
            )
            EVENT_LOGGER.debug(
                "Response from GET %s received: \n%s",
                path,
                repr_json(response),
            )
            return response
        except ClientError as e:
            self.log(f"Error during GET {path}: {str(e)}")
            raise

    async def agency_admin_POST(
        self, path, data=None, text=False, params=None, headers=None
    ) -> ClientResponse:
        if not self.multitenant:
            raise Exception("Error can't call agency admin unless in multitenant mode")
        try:
            EVENT_LOGGER.debug(
                "Controller POST %s request to Agent%s",
                path,
                (" with data: \n{}".format(repr_json(data)) if data else ""),
            )
            if not headers:
                headers = {}
            response = await self.admin_request(
                "POST", path, data, text, params, headers=headers
            )
            EVENT_LOGGER.debug(
                "Response from POST %s received: \n%s",
                path,
                repr_json(response),
            )
            return response
        except ClientError as e:
            self.log(f"Error during POST {path}: {str(e)}")
            raise

    async def admin_POST(
        self, path, data=None, text=False, params=None, headers=None
    ) -> ClientResponse:
        try:
            EVENT_LOGGER.debug(
                "Controller POST %s request to Agent%s",
                path,
                (" with data: \n{}".format(repr_json(data)) if data else ""),
            )
            if self.multitenant:
                if not headers:
                    headers = {}
                headers["Authorization"] = (
                    "Bearer " + self.managed_wallet_params["token"]
                )
                self.log("POST:", path)
                self.log("Headers:", headers)
            response = await self.admin_request(
                "POST", path, data, text, params, headers=headers
            )
            EVENT_LOGGER.debug(
                "Response from POST %s received: \n%s",
                path,
                repr_json(response),
            )
            return response
        except ClientError as e:
            self.log(f"Error during POST {path}: {str(e)}")
            raise

    async def admin_PATCH(
        self, path, data=None, text=False, params=None
    ) -> ClientResponse:
        try:
            return await self.admin_request("PATCH", path, data, text, params)
        except ClientError as e:
            self.log(f"Error during PATCH {path}: {str(e)}")
            raise

    async def admin_GET_FILE(self, path, params=None) -> bytes:
        try:
            params = {k: v for (k, v) in (params or {}).items() if v is not None}
            resp = await self.client_session.request(
                "GET", self.admin_url + path, params=params
            )
            resp.raise_for_status()
            return await resp.read()
        except ClientError as e:
            self.log(f"Error during GET FILE {path}: {str(e)}")
            raise

    async def admin_PUT_FILE(self, files, url, params=None, headers=None) -> bytes:
        try:
            params = {k: v for (k, v) in (params or {}).items() if v is not None}
            resp = await self.client_session.request(
                "PUT", url, params=params, data=files, headers=headers
            )
            resp.raise_for_status()
            return await resp.read()
        except ClientError as e:
            self.log(f"Error during PUT FILE {url}: {str(e)}")
            raise

    async def detect_process(self, headers=None):
        async def fetch_status(url: str, timeout: float, headers=None):
            code = None
            text = None
            start = default_timer()
            async with ClientSession(timeout=ClientTimeout(total=3.0)) as session:
                while default_timer() - start < timeout:
                    try:
                        async with session.get(url, headers=headers) as resp:
                            code = resp.status
                            if code == 200:
                                text = await resp.text()
                                break
                    except (ClientError, asyncio.TimeoutError):
                        pass
                    await asyncio.sleep(0.5)
            return code, text

        status_url = self.admin_url + "/status"
        status_code, status_text = await fetch_status(
            status_url, START_TIMEOUT, headers=headers
        )

        if not status_text:
            raise Exception(
                f"Timed out waiting for agent process to start (status={status_code}). "
                + f"Admin URL: {status_url}"
            )
        ok = False
        try:
            status = json.loads(status_text)
            ok = isinstance(status, dict) and "version" in status
        except json.JSONDecodeError:
            pass
        if not ok:
            raise Exception(
                f"Unexpected response from agent process. Admin URL: {status_url}"
            )

    async def fetch_timing(self):
        status = await self.admin_GET("/status")
        return status.get("timing")

    def format_timing(self, timing: dict) -> dict:
        result = []
        for name, count in timing["count"].items():
            result.append(
                (
                    name[:35],
                    count,
                    timing["total"][name],
                    timing["avg"][name],
                    timing["min"][name],
                    timing["max"][name],
                )
            )
        result.sort(key=lambda row: row[2], reverse=True)
        yield "{:35} | {:>12} {:>12} {:>10} {:>10} {:>10}".format(
            "", "count", "total", "avg", "min", "max"
        )
        yield "=" * 96
        yield from (
            "{:35} | {:12d} {:12.3f} {:10.3f} {:10.3f} {:10.3f}".format(*row)
            for row in result
        )
        yield ""

    async def reset_timing(self):
        await self.admin_POST("/status/reset", text=True)

    @property
    def postgres_config(self):
        return {
            "url": f"{self.internal_host}:5432",
            "tls": "None",
            "max_connections": 5,
            "min_idle_time": 0,
            "connection_timeout": 10,
        }

    @property
    def postgres_creds(self):
        return {
            "account": "postgres",
            "password": "mysecretpassword",
            "admin_account": "postgres",
            "admin_password": "mysecretpassword",
        }

    async def collect_postgres_stats(self, ident: str, vacuum_full: bool = True):
        creds = self.postgres_creds

        conn = await asyncpg.connect(
            host=self.internal_host,
            port="5432",
            user=creds["admin_account"],
            password=creds["admin_password"],
            database=self.wallet_name,
        )

        tables = ("items", "tags_encrypted", "tags_plaintext")
        for t in tables:
            await conn.execute(f"VACUUM FULL {t}" if vacuum_full else f"VACUUM {t}")

        sizes = await conn.fetch(
            """
            SELECT relname AS "relation",
                pg_size_pretty(pg_total_relation_size(C.oid)) AS "total_size"
            FROM pg_class C
            LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
            WHERE nspname = 'public'
            ORDER BY pg_total_relation_size(C.oid) DESC;
            """
        )
        results = {k: [0, "0B"] for k in tables}
        for row in sizes:
            if row["relation"] in results:
                results[row["relation"]][1] = row["total_size"].replace(" ", "")
        for t in tables:
            row = await conn.fetchrow(f"""SELECT COUNT(*) AS "count" FROM {t}""")
            results[t][0] = row["count"]
        self.wallet_stats.append((ident, results))

        await conn.close()

    def format_postgres_stats(self):
        if not self.wallet_stats:
            return
        yield "{:30} | {:>17} | {:>17} | {:>17}".format(
            f"{self.wallet_name} DB", "items", "tags_encrypted", "tags_plaintext"
        )
        yield "=" * 90
        for ident, stats in self.wallet_stats:
            yield "{:30} | {:8d} {:>8} | {:8d} {:>8} | {:8d} {:>8}".format(
                ident,
                stats["items"][0],
                stats["items"][1],
                stats["tags_encrypted"][0],
                stats["tags_encrypted"][1],
                stats["tags_plaintext"][0],
                stats["tags_plaintext"][1],
            )
        yield ""

    def reset_postgres_stats(self):
        self.wallet_stats.clear()
