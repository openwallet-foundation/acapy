"""Indy tails server interface class."""

import aiohttp

from .base import BaseTailsServer
from .error import TailsServerNotConfiguredError


class IndyTailsServer(BaseTailsServer):
    """Indy tails server interface."""

    async def upload_tails_file(
        self, context, rev_reg_id: str, tails_file_path: str
    ) -> (bool, str):
        """Upload tails file to tails server.

        Args:
            rev_reg_id: The revocation registry identifier
            tails_file: The path to the tails file to upload
        """

        genesis_transactions = context.settings.get("ledger.genesis_transactions")
        tails_server_base_url = context.settings.get("tails_server_base_url")

        if not tails_server_base_url:
            raise TailsServerNotConfiguredError(
                "tails_server_base_url setting is not set"
            )

        with open(tails_file_path, "rb") as tails_file:
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    f"{tails_server_base_url}/{rev_reg_id}",
                    data={"genesis": genesis_transactions, "tails": tails_file},
                ) as resp:
                    if resp.status == 200:
                        return True, None
                    else:
                        return False, resp.reason
