"""AnonCreds tails server interface class."""

import logging

from typing import Tuple

from ..config.injection_context import InjectionContext
from ..utils.http import put_file, PutError

from .base import BaseTailsServer
from .error import TailsServerNotConfiguredError


LOGGER = logging.getLogger(__name__)


class AnonCredsTailsServer(BaseTailsServer):
    """AnonCreds tails server interface."""

    async def upload_tails_file(
        self,
        context: InjectionContext,
        filename: str,
        tails_file_path: str,
        interval: float = 1.0,
        backoff: float = 0.25,
        max_attempts: int = 5,
    ) -> Tuple[bool, str]:
        """Upload tails file to tails server.

        Args:
            context: context with configuration settings
            filename: file name given to tails server
            tails_file_path: path to the tails file to upload
            interval: initial interval between attempts
            backoff: exponential backoff in retry interval
            max_attempts: maximum number of attempts to make

        Returns:
            Tuple[bool, str]: tuple with success status and url of uploaded
            file or error message if failed

        """
        tails_server_upload_url = context.settings.get("tails_server_upload_url")

        if not tails_server_upload_url:
            raise TailsServerNotConfiguredError(
                "tails_server_upload_url setting is not set"
            )

        upload_url = tails_server_upload_url.rstrip("/") + f"/hash/{filename}"

        try:
            await put_file(
                upload_url,
                {"tails": tails_file_path},
                {},
                interval=interval,
                backoff=backoff,
                max_attempts=max_attempts,
            )
        except PutError as x_put:
            return (False, x_put.message)

        return True, upload_url
