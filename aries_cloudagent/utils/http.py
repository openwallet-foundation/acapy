"""HTTP utility methods."""

import asyncio
import logging
import urllib.parse

from aiohttp import (
    BaseConnector,
    ClientError,
    ClientResponse,
    ClientSession,
    FormData,
)
from aiohttp.web import HTTPConflict

from ..core.error import BaseError

from .repeat import RepeatSequence


LOGGER = logging.getLogger(__name__)


class FetchError(BaseError):
    """Error raised when an HTTP fetch fails."""


class PutError(BaseError):
    """Error raised when an HTTP put fails."""


async def fetch_stream(
    url: str,
    *,
    headers: dict = None,
    retry: bool = True,
    max_attempts: int = 5,
    interval: float = 1.0,
    backoff: float = 0.25,
    request_timeout: float = 10.0,
    connector: BaseConnector = None,
    session: ClientSession = None,
):
    """Fetch from an HTTP server with automatic retries and timeouts.

    Args:
        url: the address to fetch
        headers: an optional dict of headers to send
        retry: flag to retry the fetch
        max_attempts: the maximum number of attempts to make
        interval: the interval between retries, in seconds
        backoff: the backoff interval, in seconds
        request_timeout: the HTTP request timeout, in seconds
        connector: an optional existing BaseConnector
        session: a shared ClientSession
        json: flag to parse the result as JSON

    """
    limit = max_attempts if retry else 1
    if not session:
        session = ClientSession(
            connector=connector, connector_owner=(not connector), trust_env=True
        )
    async with session:
        async for attempt in RepeatSequence(limit, interval, backoff):
            try:
                async with attempt.timeout(request_timeout):
                    response: ClientResponse = await session.get(url, headers=headers)
                    if response.status < 200 or response.status >= 300:
                        raise ClientError(
                            f"Bad response from server: {response.status} - "
                            f"{response.reason}"
                        )
                    return response.content
            except (ClientError, asyncio.TimeoutError) as e:
                if attempt.final:
                    raise FetchError("Exceeded maximum fetch attempts") from e


async def fetch(
    url: str,
    *,
    headers: dict = None,
    retry: bool = True,
    max_attempts: int = 5,
    interval: float = 1.0,
    backoff: float = 0.25,
    request_timeout: float = 10.0,
    connector: BaseConnector = None,
    session: ClientSession = None,
    json: bool = False,
):
    """Fetch from an HTTP server with automatic retries and timeouts.

    Args:
        url: the address to fetch
        headers: an optional dict of headers to send
        retry: flag to retry the fetch
        max_attempts: the maximum number of attempts to make
        interval: the interval between retries, in seconds
        backoff: the backoff interval, in seconds
        request_timeout: the HTTP request timeout, in seconds
        connector: an optional existing BaseConnector
        session: a shared ClientSession
        json: flag to parse the result as JSON

    """
    limit = max_attempts if retry else 1
    if not session:
        session = ClientSession(
            connector=connector, connector_owner=(not connector), trust_env=True
        )
    async with session:
        async for attempt in RepeatSequence(limit, interval, backoff):
            try:
                async with attempt.timeout(request_timeout):
                    response: ClientResponse = await session.get(url, headers=headers)
                    if response.status < 200 or response.status >= 300:
                        raise ClientError(
                            f"Bad response from server: {response.status} - "
                            f"{response.reason}"
                        )
                    return await (response.json() if json else response.text())
            except (ClientError, asyncio.TimeoutError) as e:
                if attempt.final:
                    raise FetchError("Exceeded maximum fetch attempts") from e


async def put_file(
    url: str,
    file_data: dict,
    extra_data: dict,
    *,
    retry: bool = True,
    max_attempts: int = 5,
    interval: float = 1.0,
    backoff: float = 0.25,
    request_timeout: float = 10.0,
    connector: BaseConnector = None,
    session: ClientSession = None,
    json: bool = False,
):
    """Put to HTTP server with automatic retries and timeouts.

    Args:
        url: the address to use
        file_data: dict with data key and path of file to upload
        extra_data: further content to include in data to put
        headers: an optional dict of headers to send
        retry: flag to retry the fetch
        max_attempts: the maximum number of attempts to make
        interval: the interval between retries, in seconds
        backoff: the backoff interval, in seconds
        request_timeout: the HTTP request timeout, in seconds
        connector: an optional existing BaseConnector
        session: a shared ClientSession
        json: flag to parse the result as JSON

    """
    (data_key, file_path) = [k for k in file_data.items()][0]
    limit = max_attempts if retry else 1

    if not session:
        session = ClientSession(
            connector=connector, connector_owner=(not connector), trust_env=True
        )
    async with session:
        async for attempt in RepeatSequence(limit, interval, backoff):
            try:
                async with attempt.timeout(request_timeout):
                    formdata = FormData()
                    try:
                        fp = open(file_path, "rb")
                    except OSError as e:
                        raise PutError("Error opening file for upload") from e
                    if extra_data:
                        for k, v in extra_data.items():
                            formdata.add_field(k, v)
                    formdata.add_field(
                        data_key, fp, content_type="application/octet-stream"
                    )
                    response: ClientResponse = await session.put(
                        url, data=formdata, allow_redirects=False
                    )
                    if (
                        # redirect codes
                        response.status in (301, 302, 303, 307, 308)
                        and not attempt.final
                    ):
                        # NOTE: a redirect counts as another upload attempt
                        to_url = response.headers.get("Location")
                        if not to_url:
                            raise PutError("Redirect missing target URL")
                        try:
                            parsed_to = urllib.parse.urlsplit(to_url)
                            parsed_from = urllib.parse.urlsplit(url)
                        except ValueError:
                            raise PutError("Invalid redirect URL")
                        if parsed_to.hostname != parsed_from.hostname:
                            raise PutError("Redirect denied: hostname mismatch")
                        url = to_url
                        LOGGER.info("Upload redirect: %s", to_url)
                    elif (response.status < 200 or response.status >= 300) and (
                        response.status != HTTPConflict.status_code
                    ):
                        raise ClientError(
                            f"Bad response from server: {response.status}, "
                            f"{response.reason}"
                        )
                    else:
                        return await (response.json() if json else response.text())
            except (ClientError, asyncio.TimeoutError) as e:
                if isinstance(e, ClientError):
                    LOGGER.warning("Upload error: %s", e)
                else:
                    LOGGER.warning("Upload error: request timed out")
                if attempt.final:
                    raise PutError("Exceeded maximum upload attempts") from e
