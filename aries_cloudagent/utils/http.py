"""HTTP utility methods."""

import asyncio

from aiohttp import BaseConnector, ClientError, ClientResponse, ClientSession
from aiohttp.web import HTTPConflict

from ..core.error import BaseError

from .repeat import RepeatSequence


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
        session = ClientSession(connector=connector, connector_owner=(not connector))
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
        session = ClientSession(connector=connector, connector_owner=(not connector))
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


async def put(
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
    data = {**extra_data}
    limit = max_attempts if retry else 1

    if not session:
        session = ClientSession(connector=connector, connector_owner=(not connector))
    async with session:
        async for attempt in RepeatSequence(limit, interval, backoff):
            try:
                async with attempt.timeout(request_timeout):
                    with open(file_path, "rb") as f:
                        data[data_key] = f
                        response: ClientResponse = await session.put(url, data=data)
                        if (response.status < 200 or response.status >= 300) and (
                            response.status != HTTPConflict.status_code
                        ):
                            raise ClientError(
                                f"Bad response from server: {response.status}, "
                                f"{response.reason}"
                            )
                        return await (response.json() if json else response.text())
            except (ClientError, asyncio.TimeoutError) as e:
                if attempt.final:
                    raise PutError("Exceeded maximum put attempts") from e
