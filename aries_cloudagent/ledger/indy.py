"""Indy ledger implementation."""

import asyncio
import json
import logging
import re
import tempfile
from os import path
from typing import Sequence

import indy.anoncreds
import indy.ledger
import indy.pool
from indy.error import IndyError, ErrorCode

from ..cache.base import BaseCache
from ..wallet.base import BaseWallet

from .base import BaseLedger
from .error import (
    BadLedgerRequestError,
    ClosedPoolError,
    LedgerTransactionError,
    DuplicateSchemaError,
)

GENESIS_TRANSACTION_PATH = tempfile.gettempdir()
GENESIS_TRANSACTION_PATH = path.join(
    GENESIS_TRANSACTION_PATH, "indy_genesis_transactions.txt"
)


class IndyLedger(BaseLedger):
    """Indy ledger class."""

    def __init__(
        self,
        name: str,
        wallet: BaseWallet,
        genesis_transactions,
        *,
        keepalive: int = 0,
        cache: BaseCache = None,
        cache_duration: int = 600,
    ):
        """
        Initialize an IndyLedger instance.

        Args:
            wallet: IndyWallet instance
            genesis_transactions: String of genesis transactions
            keepalive: How many seconds to keep the ledger open

        """
        self.logger = logging.getLogger(__name__)

        self.created = False
        self.opened = False
        self.ref_count = 0
        self.ref_lock = asyncio.Lock()
        self.keepalive = keepalive
        self.close_task: asyncio.Future = None
        self.name = name
        self.cache = cache
        self.cache_duration = cache_duration
        self.wallet = wallet
        self.pool_handle = None

        # TODO: ensure wallet type is indy

        # indy-sdk requires a file but it's only used once to bootstrap
        # the connection so we take a string instead of create a tmp file
        with open(GENESIS_TRANSACTION_PATH, "w") as genesis_file:
            genesis_file.write(genesis_transactions)

    async def create(self):
        """Create the pool ledger, if necessary."""
        pool_config = json.dumps({"genesis_txn": GENESIS_TRANSACTION_PATH})

        # We only support proto ver 2
        await indy.pool.set_protocol_version(2)

        self.logger.debug("Creating pool ledger...")
        try:
            await indy.pool.create_pool_ledger_config(self.name, pool_config)
        except IndyError as error:
            if error.error_code == ErrorCode.PoolLedgerConfigAlreadyExistsError:
                self.logger.debug("Pool ledger already created.")
            else:
                raise
        self.created = True

    async def open(self):
        """Open the pool ledger, creating it if necessary."""
        if not self.created:
            await self.create()

        # TODO: allow ledger config in init?
        self.pool_handle = await indy.pool.open_pool_ledger(self.name, "{}")
        self.opened = True

    async def close(self):
        """Close the pool ledger."""
        if self.opened:
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

    async def _submit(self, request_json: str, sign=True) -> str:
        """
        Sign and submit request to ledger.

        Args:
            request_json: The json string to submit
            sign: whether or not to sign the request

        """

        if not self.pool_handle:
            raise ClosedPoolError(
                "Cannot sign and submit request to closed pool {}".format(self.name)
            )

        if sign:
            public_did = await self.wallet.get_public_did()
            if not public_did:
                raise BadLedgerRequestError("Cannot sign request without a public DID")
            request_result_json = await indy.ledger.sign_and_submit_request(
                self.pool_handle, self.wallet.handle, public_did.did, request_json
            )
        else:
            request_result_json = await indy.ledger.submit_request(
                self.pool_handle, request_json
            )

        request_result = json.loads(request_result_json)

        operation = request_result.get("op", "")

        # HACK: If only there were a better way to identify this kind
        #       of rejected request...
        if "can have one and only one SCHEMA with name" in request_result_json:
            raise DuplicateSchemaError()

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

        public_did = await self.wallet.get_public_did()
        if not public_did:
            raise BadLedgerRequestError("Cannot publish schema without a public DID")

        schema_id, schema_json = await indy.anoncreds.issuer_create_schema(
            public_did.did, schema_name, schema_version, json.dumps(attribute_names)
        )

        request_json = await indy.ledger.build_schema_request(
            public_did.did, schema_json
        )

        try:
            await self._submit(request_json)
        except DuplicateSchemaError as e:
            self.logger.warning(
                "Schema already exists on ledger. Returning ID. " + f"Error: {str(e)}"
            )
            schema_id = f"{public_did.did}:{2}:{schema_name}:{schema_version}"

        return schema_id

    async def get_schema(self, schema_id: str):
        """
        Get a schema from the cache if available, otherwise fetch from the ledger.

        Args:
            schema_id: The schema id to retrieve

        """
        if self.cache:
            result = await self.cache.get(f"schema::{schema_id}")
            if result:
                return result
        return await self.fetch_schema(schema_id)

    async def fetch_schema(self, schema_id: str):
        """
        Get schema from ledger.

        Args:
            schema_id: The schema id to retrieve

        """

        public_did = await self.wallet.get_public_did()

        request_json = await indy.ledger.build_get_schema_request(
            public_did.did if public_did else None, schema_id
        )

        response_json = await self._submit(request_json, sign=bool(public_did))
        _, parsed_schema_json = await indy.ledger.parse_get_schema_response(
            response_json
        )
        parsed_response = json.loads(parsed_schema_json)

        if parsed_response and self.cache:
            await self.cache.set(
                f"schema::{schema_id}", parsed_response, self.cache_duration
            )

        return parsed_response

    async def send_credential_definition(self, schema_id: str, tag: str = "default"):
        """
        Send credential definition to ledger and store relevant key matter in wallet.

        Args:
            schema_id: The schema id of the schema to create cred def for
            tag: Option tag to distinguish multiple credential definitions

        """

        public_did = await self.wallet.get_public_did()
        if not public_did:
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
                public_did.did,
                json.dumps(schema),
                tag,
                "CL",
                json.dumps({"support_revocation": False}),
            )
        # If the cred def already exists in the wallet, we need some way of obtaining
        # that cred def id (from schema id passed) since we can now assume we can use
        # it in future operations.
        except IndyError as error:
            if error.error_code == ErrorCode.AnoncredsCredDefAlreadyExistsError:
                try:
                    cred_def_id = re.search(r"\w*:\d*:CL:\d*:\w*", error.message).group(
                        0
                    )
                    return cred_def_id
                # The regex search failed so let the error bubble up
                except AttributeError:
                    raise error
            else:
                raise

        request_json = await indy.ledger.build_cred_def_request(
            public_did.did, credential_definition_json
        )

        await self._submit(request_json)

        # TODO: validate response

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
            credential_definition_id: The schema id of the schema to fetch cred def for

        """

        public_did = await self.wallet.get_public_did()

        request_json = await indy.ledger.build_get_cred_def_request(
            public_did.did if public_did else None, credential_definition_id
        )

        response_json = await self._submit(request_json, sign=bool(public_did))

        (
            _,
            parsed_credential_definition_json,
        ) = await indy.ledger.parse_get_cred_def_response(response_json)
        parsed_response = json.loads(parsed_credential_definition_json)

        if parsed_response and self.cache:
            await self.cache.set(
                f"credential_definition::{credential_definition_id}",
                parsed_response,
                self.cache_duration,
            )

        return parsed_response
