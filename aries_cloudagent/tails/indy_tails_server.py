"""Indy tails server interface class."""

from typing import Tuple

from ..utils.http import put_file, PutError

from .base import BaseTailsServer
from .error import TailsServerNotConfiguredError


class IndyTailsServer(BaseTailsServer):
    """Indy tails server interface."""

    async def upload_tails_file(
        self,
        context,
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

        genesis_transactions = context.settings.get("ledger.genesis_transactions")
        tails_server_upload_url = context.settings.get("tails_server_upload_url")

        if not tails_server_upload_url:
            raise TailsServerNotConfiguredError(
                "tails_server_upload_url setting is not set"
            )

        try:
            return (
                True,
                await put_file(
                    f"{tails_server_upload_url}/{rev_reg_id}",
                    {"tails": tails_file_path},
                    {"genesis": genesis_transactions},
                    interval=interval,
                    backoff=backoff,
                    max_attempts=max_attempts,
                ),
            )
        except PutError as x_put:
            return (False, x_put.message)
