"""Indy ledger implementation."""

import asyncio
import json
import logging
import re
import tempfile

from hashlib import sha256
from os import path
from datetime import datetime, date
from time import time
from typing import Sequence, Type

import indy.anoncreds
import indy.ledger
import indy.pool
from indy.error import IndyError, ErrorCode

from ..cache.base import BaseCache
from ..messaging.credential_definitions.util import CRED_DEF_SENT_RECORD_TYPE
from ..messaging.schemas.util import SCHEMA_SENT_RECORD_TYPE
from ..storage.base import StorageRecord
from ..storage.indy import IndyStorage
from ..wallet.base import BaseWallet

from .base import BaseLedger
from .error import (
    BadLedgerRequestError,
    ClosedPoolError,
    LedgerConfigError,
    LedgerError,
    LedgerTransactionError,
)
from .util import TAA_ACCEPTED_RECORD_TYPE


GENESIS_TRANSACTION_PATH = tempfile.gettempdir()
GENESIS_TRANSACTION_PATH = path.join(
    GENESIS_TRANSACTION_PATH, "indy_genesis_transactions.txt"
)


class IndyErrorHandler:
    """Trap IndyError and raise an appropriate LedgerError instead."""

    def __init__(self, message: str = None, error_cls: Type[LedgerError] = LedgerError):
        """Init the context manager."""
        self.error_cls = error_cls
        self.message = message

    def __enter__(self):
        """Enter the context manager."""
        return self

    def __exit__(self, err_type, err_value, err_traceback):
        """Exit the context manager."""
        if err_type is IndyError:
            raise self.wrap_error(
                err_value, self.message, self.error_cls
            ) from err_value

    @classmethod
    def wrap_error(
        cls,
        err_value: IndyError,
        message: str = None,
        error_cls: Type[LedgerError] = LedgerError,
    ) -> LedgerError:
        """Create an instance of LedgerError from an IndyError."""
        err_msg = message or "Exception while performing ledger operation"
        indy_message = hasattr(err_value, "message") and err_value.message
        if indy_message:
            err_msg += f": {indy_message}"
        # TODO: may wish to attach backtrace when available
        return error_cls(err_msg)


class IndyLedger(BaseLedger):
    """Indy ledger class."""

    LEDGER_TYPE = "indy"

    def __init__(
        self,
        pool_name: str,
        wallet: BaseWallet,
        *,
        keepalive: int = 0,
        cache: BaseCache = None,
        cache_duration: int = 600,
    ):
        """
        Initialize an IndyLedger instance.

        Args:
            pool_name: The Indy pool ledger configuration name
            wallet: IndyWallet instance
            keepalive: How many seconds to keep the ledger open
            cache: The cache instance to use
            cache_duration: The TTL for ledger cache entries
        """
        self.logger = logging.getLogger(__name__)

        self.opened = False
        self.ref_count = 0
        self.ref_lock = asyncio.Lock()
        self.keepalive = keepalive
        self.close_task: asyncio.Future = None
        self.cache = cache
        self.cache_duration = cache_duration
        self.wallet = wallet
        self.pool_handle = None
        self.pool_name = pool_name
        self.taa_acceptance = None
        self.taa_cache = None

        if wallet.WALLET_TYPE != "indy":
            raise LedgerConfigError("Wallet type is not 'indy'")

    async def create_pool_config(
        self, genesis_transactions: str, recreate: bool = False
    ):
        """Create the pool ledger configuration."""

        # indy-sdk requires a file but it's only used once to bootstrap
        # the connection so we take a string instead of create a tmp file
        txn_path = GENESIS_TRANSACTION_PATH
        with open(txn_path, "w") as genesis_file:
            genesis_file.write(genesis_transactions)
        pool_config = json.dumps({"genesis_txn": txn_path})

        if await self.check_pool_config():
            if recreate:
                self.logger.debug("Removing existing ledger config")
                await indy.pool.delete_pool_ledger_config(self.pool_name)
            else:
                raise LedgerConfigError(
                    "Ledger pool configuration already exists: %s", self.pool_name
                )

        self.logger.debug("Creating pool ledger config")
        with IndyErrorHandler(
            "Exception when creating pool ledger config", LedgerConfigError
        ):
            await indy.pool.create_pool_ledger_config(self.pool_name, pool_config)

    async def check_pool_config(self) -> bool:
        """Check if a pool config has been created."""
        pool_names = {cfg["pool"] for cfg in await indy.pool.list_pools()}
        return self.pool_name in pool_names

    async def open(self):
        """Open the pool ledger, creating it if necessary."""
        # We only support proto ver 2
        with IndyErrorHandler(
            "Exception when setting ledger protocol version", LedgerConfigError
        ):
            await indy.pool.set_protocol_version(2)

        with IndyErrorHandler("Exception when opening pool ledger", LedgerConfigError):
            self.pool_handle = await indy.pool.open_pool_ledger(self.pool_name, "{}")
        self.opened = True

    async def close(self):
        """Close the pool ledger."""
        if self.opened:
            with IndyErrorHandler("Exception when closing pool ledger"):
                await indy.pool.close_pool_ledger(self.pool_handle)
            self.pool_handle = None
            self.opened = False

    async def _context_open(self):
        """Open the wallet if necessary and increase the number of active references."""
        async with self.ref_lock:
            if self.close_task:
                self.close_task.cancel()
            if not self.opened:
                self.logger.debug("Opening the pool ledger")
                await self.open()
            self.ref_count += 1

    async def _context_close(self):
        """Release the wallet reference and schedule closing of the pool ledger."""

        async def closer(timeout: int):
            """Close the pool ledger after a timeout."""
            await asyncio.sleep(timeout)
            async with self.ref_lock:
                if not self.ref_count:
                    self.logger.debug("Closing pool ledger after timeout")
                    await self.close()

        async with self.ref_lock:
            self.ref_count -= 1
            if not self.ref_count:
                if self.keepalive:
                    self.close_task = asyncio.ensure_future(closer(self.keepalive))
                else:
                    await self.close()

    async def __aenter__(self) -> "IndyLedger":
        """
        Context manager entry.

        Returns:
            The current instance

        """
        await self._context_open()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Context manager exit."""
        await self._context_close()

    async def _submit(
        self,
        request_json: str,
        sign: bool = None,
        taa_accept: bool = False,
        public_did: str = "",
    ) -> str:
        """
        Sign and submit request to ledger.

        Args:
            request_json: The json string to submit
            sign: whether or not to sign the request
            taa_accept: whether to apply TAA acceptance to the (signed, write) request
            public_did: override the public DID used to sign the request

        """

        if not self.pool_handle:
            raise ClosedPoolError(
                "Cannot sign and submit request to closed pool {}".format(
                    self.pool_name
                )
            )

        if (sign is None and public_did == "") or (sign and not public_did):
            did_info = await self.wallet.get_public_did()
            if did_info:
                public_did = did_info.did
        if public_did and sign is None:
            sign = True

        if sign:
            if not public_did:
                raise BadLedgerRequestError("Cannot sign request without a public DID")
            if taa_accept:
                acceptance = await self.get_latest_txn_author_acceptance()
                if acceptance:
                    request_json = await (
                        indy.ledger.append_txn_author_agreement_acceptance_to_request(
                            request_json,
                            acceptance["text"],
                            acceptance["version"],
                            acceptance["digest"],
                            acceptance["mechanism"],
                            acceptance["time"],
                        )
                    )
            submit_op = indy.ledger.sign_and_submit_request(
                self.pool_handle, self.wallet.handle, public_did, request_json
            )
        else:
            submit_op = indy.ledger.submit_request(self.pool_handle, request_json)

        with IndyErrorHandler(
            "Exception raised by ledger transaction", LedgerTransactionError
        ):
            request_result_json = await submit_op

        request_result = json.loads(request_result_json)

        operation = request_result.get("op", "")

        if operation in ("REQNACK", "REJECT"):
            raise LedgerTransactionError(
                f"Ledger rejected transaction request: {request_result['reason']}"
            )

        elif operation == "REPLY":
            return request_result_json

        else:
            raise LedgerTransactionError(
                f"Unexpected operation code from ledger: {operation}"
            )

    async def send_schema(
        self, schema_name: str, schema_version: str, attribute_names: Sequence[str]
    ):
        """
        Send schema to ledger.

        Args:
            schema_name: The schema name
            schema_version: The schema version
            attribute_names: A list of schema attributes

        """

        public_info = await self.wallet.get_public_did()
        if not public_info:
            raise BadLedgerRequestError("Cannot publish schema without a public DID")

        schema_id = await self.check_existing_schema(
            public_info.did, schema_name, schema_version, attribute_names
        )
        if schema_id:
            self.logger.warning("Schema already exists on ledger. Returning ID.")
        else:
            with IndyErrorHandler("Exception when creating schema definition"):
                schema_id, schema_json = await indy.anoncreds.issuer_create_schema(
                    public_info.did,
                    schema_name,
                    schema_version,
                    json.dumps(attribute_names),
                )

            with IndyErrorHandler("Exception when building schema request"):
                request_json = await indy.ledger.build_schema_request(
                    public_info.did, schema_json
                )

            try:
                await self._submit(request_json, public_did=public_info.did)
            except LedgerTransactionError as e:
                # Identify possible duplicate schema errors on indy-node < 1.9 and > 1.9
                if (
                    "can have one and only one SCHEMA with name" in e.message
                    or "UnauthorizedClientRequest" in e.message
                ):
                    # handle potential race condition if multiple agents are publishing
                    # the same schema simultaneously
                    schema_id = await self.check_existing_schema(
                        public_info.did, schema_name, schema_version, attribute_names
                    )
                    if schema_id:
                        self.logger.warning(
                            "Schema already exists on ledger. Returning ID. Error: %s",
                            e,
                        )
                else:
                    raise

        schema_id_parts = schema_id.split(":")
        schema_tags = {
            "schema_id": schema_id,
            "schema_issuer_did": public_info.did,
            "schema_name": schema_id_parts[-2],
            "schema_version": schema_id_parts[-1],
            "epoch": str(int(time())),
        }
        record = StorageRecord(SCHEMA_SENT_RECORD_TYPE, schema_id, schema_tags,)
        storage = self.get_indy_storage()
        await storage.add_record(record)

        return schema_id

    async def check_existing_schema(
        self,
        public_did: str,
        schema_name: str,
        schema_version: str,
        attribute_names: Sequence[str],
    ) -> str:
        """Check if a schema has already been published."""
        fetch_schema_id = f"{public_did}:2:{schema_name}:{schema_version}"
        schema = await self.fetch_schema_by_id(fetch_schema_id)
        if schema:
            fetched_attrs = schema["attrNames"].copy()
            fetched_attrs.sort()
            cmp_attrs = list(attribute_names)
            cmp_attrs.sort()
            if fetched_attrs != cmp_attrs:
                raise LedgerTransactionError(
                    "Schema already exists on ledger, but attributes do not match: "
                    + f"{schema_name}:{schema_version} {fetched_attrs} != {cmp_attrs}"
                )
            return fetch_schema_id

    async def get_schema(self, schema_id: str):
        """
        Get a schema from the cache if available, otherwise fetch from the ledger.

        Args:
            schema_id: The schema id (or stringified sequence number) to retrieve

        """
        if self.cache:
            result = await self.cache.get(f"schema::{schema_id}")
            if result:
                return result

        if schema_id.isdigit():
            return await self.fetch_schema_by_seq_no(int(schema_id))
        else:
            return await self.fetch_schema_by_id(schema_id)

    async def fetch_schema_by_id(self, schema_id: str):
        """
        Get schema from ledger.

        Args:
            schema_id: The schema id (or stringified sequence number) to retrieve

        Returns:
            Indy schema dict

        """

        public_info = await self.wallet.get_public_did()
        public_did = public_info.did if public_info else None

        with IndyErrorHandler("Exception when building schema request"):
            request_json = await indy.ledger.build_get_schema_request(
                public_did, schema_id
            )

        response_json = await self._submit(request_json, public_did=public_did)
        response = json.loads(response_json)
        if not response["result"]["seqNo"]:
            # schema not found
            return None

        with IndyErrorHandler("Exception when parsing schema response"):
            _, parsed_schema_json = await indy.ledger.parse_get_schema_response(
                response_json
            )

        parsed_response = json.loads(parsed_schema_json)
        if parsed_response and self.cache:
            await self.cache.set(
                [f"schema::{schema_id}", f"schema::{response['result']['seqNo']}"],
                parsed_response,
                self.cache_duration,
            )

        return parsed_response

    async def fetch_schema_by_seq_no(self, seq_no: int):
        """
        Fetch a schema by its sequence number.

        Args:
            seq_no: schema ledger sequence number

        Returns:
            Indy schema dict

        """
        # get txn by sequence number, retrieve schema identifier components
        request_json = await indy.ledger.build_get_txn_request(
            None, None, seq_no=seq_no
        )
        response = json.loads(await self._submit(request_json))

        # transaction data format assumes node protocol >= 1.4 (circa 2018-07)
        data_txn = (response["result"].get("data", {}) or {}).get("txn", {})
        if data_txn.get("type", None) == "101":  # marks indy-sdk schema txn type
            (origin_did, name, version) = (
                data_txn["metadata"]["from"],
                data_txn["data"]["data"]["name"],
                data_txn["data"]["data"]["version"],
            )
            schema_id = f"{origin_did}:2:{name}:{version}"
            return await self.get_schema(schema_id)

        raise LedgerTransactionError(
            f"Could not get schema from ledger for seq no {seq_no}"
        )

    async def send_credential_definition(self, schema_id: str, tag: str = None):
        """
        Send credential definition to ledger and store relevant key matter in wallet.

        Args:
            schema_id: The schema id of the schema to create cred def for
            tag: Option tag to distinguish multiple credential definitions

        """

        public_info = await self.wallet.get_public_did()
        if not public_info:
            raise BadLedgerRequestError(
                "Cannot publish credential definition without a public DID"
            )

        schema = await self.get_schema(schema_id)

        # TODO: add support for tag, sig type, and config
        try:
            (
                credential_definition_id,
                credential_definition_json,
            ) = await indy.anoncreds.issuer_create_and_store_credential_def(
                self.wallet.handle,
                public_info.did,
                json.dumps(schema),
                tag or "default",
                "CL",
                json.dumps({"support_revocation": False}),
            )
        # If the cred def already exists in the wallet, we need some way of obtaining
        # that cred def id (from schema id passed) since we can now assume we can use
        # it in future operations.
        except IndyError as error:
            if error.error_code == ErrorCode.AnoncredsCredDefAlreadyExistsError:
                try:
                    credential_definition_id = re.search(
                        r"\w*:3:CL:(([1-9][0-9]*)|(.{21,22}:2:.+:[0-9.]+)):\w*",
                        error.message,
                    ).group(0)
                # The regex search failed so let the error bubble up
                except AttributeError:
                    raise LedgerError(
                        "Previous credential definition exists, but ID could "
                        "not be extracted"
                    )
            else:
                raise IndyErrorHandler.wrap_error(error) from error

        # check if the cred def already exists on the ledger
        cred_def = json.loads(credential_definition_json)
        exist_def = await self.fetch_credential_definition(credential_definition_id)
        if exist_def:
            if exist_def["value"] != cred_def["value"]:
                self.logger.warning(
                    "Ledger definition of cred def %s will be replaced",
                    credential_definition_id,
                )
                exist_def = None

        if not exist_def:
            with IndyErrorHandler("Exception when building cred def request"):
                request_json = await indy.ledger.build_cred_def_request(
                    public_info.did, credential_definition_json
                )
            await self._submit(request_json, True, public_did=public_info.did)
        else:
            self.logger.warning(
                "Ledger definition of cred def %s already exists",
                credential_definition_id,
            )

        schema_id_parts = schema_id.split(":")
        cred_def_tags = {
            "schema_id": schema_id,
            "schema_issuer_did": schema_id_parts[0],
            "schema_name": schema_id_parts[-2],
            "schema_version": schema_id_parts[-1],
            "issuer_did": public_info.did,
            "cred_def_id": credential_definition_id,
            "epoch": str(int(time())),
        }
        record = StorageRecord(
            CRED_DEF_SENT_RECORD_TYPE, credential_definition_id, cred_def_tags,
        )
        storage = self.get_indy_storage()
        await storage.add_record(record)

        return credential_definition_id

    async def get_credential_definition(self, credential_definition_id: str):
        """
        Get a credential definition from the cache if available, otherwise the ledger.

        Args:
            credential_definition_id: The schema id of the schema to fetch cred def for

        """
        if self.cache:
            result = await self.cache.get(
                f"credential_definition::{credential_definition_id}"
            )
            if result:
                return result

        return await self.fetch_credential_definition(credential_definition_id)

    async def fetch_credential_definition(self, credential_definition_id: str):
        """
        Get a credential definition from the ledger by id.

        Args:
            credential_definition_id: The cred def id of the cred def to fetch

        """

        public_info = await self.wallet.get_public_did()
        public_did = public_info.did if public_info else None

        with IndyErrorHandler("Exception when building cred def request"):
            request_json = await indy.ledger.build_get_cred_def_request(
                public_did, credential_definition_id
            )

        response_json = await self._submit(request_json, public_did=public_did)

        with IndyErrorHandler("Exception when parsing cred def response"):
            try:
                (
                    _,
                    parsed_credential_definition_json,
                ) = await indy.ledger.parse_get_cred_def_response(response_json)
                parsed_response = json.loads(parsed_credential_definition_json)
            except IndyError as error:
                if error.error_code == ErrorCode.LedgerNotFound:
                    parsed_response = None

        if parsed_response and self.cache:
            await self.cache.set(
                f"credential_definition::{credential_definition_id}",
                parsed_response,
                self.cache_duration,
            )

        return parsed_response

    async def credential_definition_id2schema_id(self, credential_definition_id):
        """
        From a credential definition, get the identifier for its schema.

        Args:
            credential_definition_id: The identifier of the credential definition
                from which to identify a schema
        """

        # scrape schema id or sequence number from cred def id
        tokens = credential_definition_id.split(":")
        if len(tokens) == 8:  # node protocol >= 1.4: cred def id has 5 or 8 tokens
            return ":".join(tokens[3:7])  # schema id spans 0-based positions 3-6

        # get txn by sequence number, retrieve schema identifier components
        seq_no = tokens[3]
        return (await self.get_schema(seq_no))["id"]

    async def get_key_for_did(self, did: str) -> str:
        """Fetch the verkey for a ledger DID.

        Args:
            did: The DID to look up on the ledger or in the cache
        """
        nym = self.did_to_nym(did)
        public_info = await self.wallet.get_public_did()
        public_did = public_info.did if public_info else None
        with IndyErrorHandler("Exception when building nym request"):
            request_json = await indy.ledger.build_get_nym_request(public_did, nym)
        response_json = await self._submit(request_json, public_did=public_did)
        data_json = (json.loads(response_json))["result"]["data"]
        return json.loads(data_json)["verkey"]

    async def get_endpoint_for_did(self, did: str) -> str:
        """Fetch the endpoint for a ledger DID.

        Args:
            did: The DID to look up on the ledger or in the cache
        """
        nym = self.did_to_nym(did)
        public_info = await self.wallet.get_public_did()
        public_did = public_info.did if public_info else None
        with IndyErrorHandler("Exception when building attribute request"):
            request_json = await indy.ledger.build_get_attrib_request(
                public_did, nym, "endpoint", None, None
            )
        response_json = await self._submit(request_json, public_did=public_did)
        endpoint_json = json.loads(response_json)["result"]["data"]
        if endpoint_json:
            address = json.loads(endpoint_json)["endpoint"].get("endpoint", None)
        else:
            address = None

        return address

    async def update_endpoint_for_did(self, did: str, endpoint: str) -> bool:
        """Check and update the endpoint on the ledger.

        Args:
            did: The ledger DID
            endpoint: The endpoint address
            transport_vk: The endpoint transport verkey
        """
        exist_endpoint = await self.get_endpoint_for_did(did)
        if exist_endpoint != endpoint:
            nym = self.did_to_nym(did)
            attr_json = json.dumps({"endpoint": {"endpoint": endpoint}})
            with IndyErrorHandler("Exception when building attribute request"):
                request_json = await indy.ledger.build_attrib_request(
                    nym, nym, None, attr_json, None
                )
            await self._submit(request_json, True, True)
            return True
        return False

    async def register_nym(
        self, did: str, verkey: str, alias: str = None, role: str = None
    ):
        """
        Register a nym on the ledger.

        Args:
            did: DID to register on the ledger.
            verkey: The verification key of the keypair.
            alias: Human-friendly alias to assign to the DID.
            role: For permissioned ledgers, what role should the new DID have.
        """
        public_info = await self.wallet.get_public_did()
        public_did = public_info.did if public_info else None
        r = await indy.ledger.build_nym_request(public_did, did, verkey, alias, role)
        await self._submit(r, True, True, public_did=public_did)

    def nym_to_did(self, nym: str) -> str:
        """Format a nym with the ledger's DID prefix."""
        if nym:
            # remove any existing prefix
            nym = self.did_to_nym(nym)
            return f"did:sov:{nym}"

    async def get_txn_author_agreement(self, reload: bool = False):
        """Get the current transaction author agreement, fetching it if necessary."""
        if not self.taa_cache or reload:
            self.taa_cache = await self.fetch_txn_author_agreement()
        return self.taa_cache

    async def fetch_txn_author_agreement(self):
        """Fetch the current AML and TAA from the ledger."""
        public_info = await self.wallet.get_public_did()
        public_did = public_info.did if public_info else None

        get_aml_req = await indy.ledger.build_get_acceptance_mechanisms_request(
            public_did, None, None
        )
        response_json = await self._submit(get_aml_req, public_did=public_did)
        aml_found = (json.loads(response_json))["result"]["data"]

        get_taa_req = await indy.ledger.build_get_txn_author_agreement_request(
            public_did, None
        )
        response_json = await self._submit(get_taa_req, public_did=public_did)
        taa_found = (json.loads(response_json))["result"]["data"]
        taa_required = taa_found and taa_found["text"]
        if taa_found:
            taa_plaintext = taa_found["version"] + taa_found["text"]
            taa_found["digest"] = sha256(taa_plaintext.encode("utf-8")).digest().hex()

        return {
            "aml_record": aml_found,
            "taa_record": taa_found,
            "taa_required": taa_required,
        }

    def get_indy_storage(self) -> IndyStorage:
        """Get an IndyStorage instance for the current wallet."""
        return IndyStorage(self.wallet)

    def taa_rough_timestamp(self) -> int:
        """Get a timestamp accurate to the day.

        Anything more accurate is a privacy concern.
        """
        return int(datetime.combine(date.today(), datetime.min.time()).timestamp())

    async def accept_txn_author_agreement(
        self,
        taa_record: dict,
        mechanism: str,
        accept_time: int = None,
        store: bool = False,
    ):
        """Save a new record recording the acceptance of the TAA."""
        if not accept_time:
            accept_time = self.taa_rough_timestamp()
        acceptance = {
            "text": taa_record["text"],
            "version": taa_record["version"],
            "digest": taa_record["digest"],
            "mechanism": mechanism,
            "time": accept_time,
        }
        record = StorageRecord(
            TAA_ACCEPTED_RECORD_TYPE,
            json.dumps(acceptance),
            {"pool_name": self.pool_name},
        )
        storage = self.get_indy_storage()
        await storage.add_record(record)
        cache_key = TAA_ACCEPTED_RECORD_TYPE + "::" + self.pool_name
        await self.cache.set(cache_key, acceptance, self.cache_duration)

    async def get_latest_txn_author_acceptance(self):
        """Look up the latest TAA acceptance."""
        cache_key = TAA_ACCEPTED_RECORD_TYPE + "::" + self.pool_name
        acceptance = await self.cache.get(cache_key)
        if acceptance is None:
            storage = self.get_indy_storage()
            tag_filter = {"pool_name": self.pool_name}
            found = await storage.search_records(
                TAA_ACCEPTED_RECORD_TYPE, tag_filter
            ).fetch_all()
            if found:
                records = list(json.loads(record.value) for record in found)
                records.sort(key=lambda v: v["time"], reverse=True)
                acceptance = records[0]
            else:
                acceptance = {}
            await self.cache.set(cache_key, acceptance, self.cache_duration)
        return acceptance
