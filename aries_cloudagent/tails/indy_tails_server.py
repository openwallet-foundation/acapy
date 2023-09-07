"""Indy tails server interface class."""

import logging

from typing import Tuple

from ..config.injection_context import InjectionContext
from ..ledger.base import BaseLedger
from ..ledger.multiple_ledger.base_manager import BaseMultipleLedgerManager
from ..utils.http import put_file, PutError

from .base import BaseTailsServer
from .error import TailsServerNotConfiguredError


LOGGER = logging.getLogger(__name__)


class IndyTailsServer(BaseTailsServer):
    """Indy tails server interface."""

    async def upload_tails_file(
        self,
        context: InjectionContext,
        rev_reg_id: str,
        tails_file_path: str,
        interval: float = 1.0,
        backoff: float = 0.25,
        max_attempts: int = 5,
    ) -> Tuple[bool, str]:
        """Upload tails file to tails server.

        Args:
            context: context with configuration settings
            rev_reg_id: revocation registry identifier
            tails_file_path: path to the tails file to upload
            interval: initial interval between attempts
            backoff: exponential backoff in retry interval
            max_attempts: maximum number of attempts to make
        """
        tails_server_upload_url = context.settings.get("tails_server_upload_url")
        genesis_transactions = context.settings.get("ledger.genesis_transactions")

        if not genesis_transactions:
            ledger_manager = context.injector.inject(BaseMultipleLedgerManager)
            write_ledger = context.injector.inject(BaseLedger)
            available_write_ledgers = await ledger_manager.get_write_ledgers()
            LOGGER.debug(f"available write_ledgers = {available_write_ledgers}")
            LOGGER.debug(f"write_ledger = {write_ledger}")
            pool = write_ledger.pool
            LOGGER.debug(f"write_ledger pool = {pool}")

            genesis_transactions = pool.genesis_txns

        if not genesis_transactions:
            raise TailsServerNotConfiguredError(
                "no genesis_transactions for writable ledger"
            )

        if not tails_server_upload_url:
            raise TailsServerNotConfiguredError(
                "tails_server_upload_url setting is not set"
            )

        upload_url = tails_server_upload_url.rstrip("/") + f"/{rev_reg_id}"

        try:
            await put_file(
                upload_url,
                {"tails": tails_file_path},
                {"genesis": genesis_transactions},
                interval=interval,
                backoff=backoff,
                max_attempts=max_attempts,
            )
        except PutError as x_put:
            return (False, x_put.message)

        return True, upload_url
