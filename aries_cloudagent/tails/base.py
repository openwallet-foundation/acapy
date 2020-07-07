"""Tails server interface base class."""

from abc import ABC, abstractmethod, ABCMeta

from ..config.injection_context import InjectionContext


class TailsServer(ABC, metaclass=ABCMeta):
    """Base class for tails server interface."""

    @abstractmethod
    async def upload_tails_file(
        self, context: InjectionContext, revo_reg_def_id: str, tails_file_path: str
    ) -> str:
        """Upload tails file to tails server.

        Args:
            revo_reg_def_id: The Revocation registry definition ID
            tails_file: The path to the tails file to upload
        """

        context.settings.get()

        with open(genesis_path, "rb") as genesis_file:
            async with session.put(
                f"{tails_server_url}/{revo_reg_def['id']}",
                data={
                    "genesis": genesis_file,
                    "tails": file_sender(revo_reg_def["value"]["tailsLocation"]),
                },
            ) as resp:
                return resp

    @abstractmethod
    async def download_tails_file(
        self, context: InjectionContext, revo_reg_def_id: str, location: str
    ) -> str:
        """Download tails file from tails server.

        Args:
            revo_reg_def_id: The Revocation registry definition ID
            loction: Path to download destination
        """
