"""Indy ledger pool implementation."""

import asyncio
import json
import logging
from os import path
import tempfile

from indy.error import IndyError
from aries_cloudagent.ledger.error import LedgerConfigError, LedgerError
from ...indy.sdk.error import IndyErrorHandler

import indy.pool

from aries_cloudagent.ledger.pool.base import BaseLedgerPool

LOGGER = logging.getLogger(__name__)

GENESIS_TRANSACTION_FILE = "indy_genesis_transactions.txt"


class IndyLegderPool(BaseLedgerPool):
    """Indy ledger pool class."""

    POOL_TYPE = "indy"

    def __init__(
        self,
        pool_name: str,
        *,
        keepalive: int = 0,
    ):
        """
        Initialize a BaseLedgerPool instance.

        Args:
            pool_name: The Indy pool ledger configuration name
            keepalive: How many seconds to keep the ledger open
        """

        self.ref_count = 0
        self.ref_lock = asyncio.Lock()
        self._name = pool_name
        self.keepalive = keepalive
        self.close_task: asyncio.Future = None
        self._handle = None
        self._created = False

    @property
    def name(self) -> str:
        """
        Accessor for the pool name.

        Returns:
            The pool name

        """
        return self._name

    @property
    def type(self) -> str:
        """Accessor for the pool type."""
        return IndyLegderPool.POOL_TYPE

    @property
    def handle(self):
        """
        Get internal pool reference.

        Returns:
            A handle to the pool

        """
        return self._handle

    @property
    def opened(self) -> bool:
        """
        Check whether pool is currently open.

        Returns:
            True if open, else False

        """
        return bool(self._handle)

    async def create_pool_config(
        self, genesis_transactions: str, recreate: bool = False
    ):
        """Create the pool ledger configuration."""

        # indy-sdk requires a file to pass the pool configuration
        # the file path includes the pool name to avoid conflicts
        txn_path = path.join(
            tempfile.gettempdir(), f"{self.name}_{GENESIS_TRANSACTION_FILE}"
        )
        with open(txn_path, "w") as genesis_file:
            genesis_file.write(genesis_transactions)
        pool_config = json.dumps({"genesis_txn": txn_path})

        if await self.check_pool_config():
            if recreate:
                LOGGER.debug("Removing existing ledger config")
                await indy.pool.delete_pool_ledger_config(self.name)
            else:
                raise LedgerConfigError(
                    "Ledger pool configuration already exists: %s", self.name
                )

        LOGGER.debug("Creating pool ledger config")
        with IndyErrorHandler(
            "Exception creating pool ledger config", LedgerConfigError
        ):
            await indy.pool.create_pool_ledger_config(self.name, pool_config)

    async def check_pool_config(self) -> bool:
        """Check if a pool config has been created."""
        pool_names = {cfg["pool"] for cfg in await indy.pool.list_pools()}
        return self.name in pool_names

    async def open(self):
        """Open the pool ledger, creating it if necessary."""
        # We only support proto ver 2
        with IndyErrorHandler(
            "Exception setting ledger protocol version", LedgerConfigError
        ):
            await indy.pool.set_protocol_version(2)

        with IndyErrorHandler(
            f"Exception opening pool ledger {self.name}", LedgerConfigError
        ):
            self._handle = await indy.pool.open_pool_ledger(self.name, "{}")

    async def close(self):
        """Close the pool ledger."""
        if self.opened:
            exc = None
            for attempt in range(3):
                try:
                    await indy.pool.close_pool_ledger(self.handle)
                except IndyError as err:
                    await asyncio.sleep(0.01)
                    exc = err
                    continue

                self._handle = None
                exc = None
                break

            if exc:
                LOGGER.error("Exception closing pool ledger")
                self.ref_count += 1  # if we are here, we should have self.ref_lock
                self.close_task = None
                raise IndyErrorHandler.wrap_error(
                    exc, "Exception closing pool ledger", LedgerError
                )

    async def _context_open(self):
        """Open the pool if necessary and increase the number of active references."""
        async with self.ref_lock:
            if self.close_task:
                self.close_task.cancel()
            if not self.opened:
                LOGGER.debug("Opening the pool ledger")
                await self.open()
            self.ref_count += 1

    async def _context_close(self):
        """Release the reference and schedule closing of the pool ledger."""

        async def closer(timeout: int):
            """Close the pool ledger after a timeout."""
            await asyncio.sleep(timeout)
            async with self.ref_lock:
                if not self.ref_count:
                    LOGGER.debug("Closing pool ledger after timeout")
                    await self.close()

        async with self.ref_lock:
            self.ref_count -= 1
            if not self.ref_count:
                if self.keepalive:
                    self.close_task = asyncio.ensure_future(closer(self.keepalive))
                else:
                    await self.close()

    async def __aenter__(self) -> "IndyLegderPool":
        """
        Context manager entry.

        Returns:
            The current instance

        """
        await super().__aenter__()
        await self._context_open()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Context manager exit."""
        await self._context_close()
        await super().__aexit__(exc_type, exc, tb)
