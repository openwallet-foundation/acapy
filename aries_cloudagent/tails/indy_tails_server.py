"""Indy tails server interface class."""

import aiohttp

from .base import TailsServer


class IndyTailsServer(TailsServer):
    """Indy tails server interface."""

    async def upload_tails_file(
        self, context, revo_reg_def_id: str, tails_file_path: str
    ) -> str:
        """Upload tails file to tails server.

        Args:
            revo_reg_def_id: The Revocation registry definition ID
            tails_file: The path to the tails file to upload
        """

        genesis_transactions = context.settings.get("ledger.genesis_transactions")
        tails_server_base_url = context.settings.get("tails.base_url")

        session = aiohttp.ClientSession()
        with open(tails_file_path, "rb") as tails_file:
            async with session.put(
                f"{tails_server_base_url}/{revo_reg_def_id}",
                data={"genesis": genesis_transactions, "tails": tails_file},
            ) as resp:
                return resp

    async def download_tails_file(self, revo_reg_def_id: str, location: str) -> str:
        """Download tails file from tails server.

        Args:
            revo_reg_def_id: The Revocation registry definition ID
            loction: Path to download destination
        """
