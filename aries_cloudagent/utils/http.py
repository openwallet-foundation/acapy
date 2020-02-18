"""HTTP utility methods."""

import asyncio

from aiohttp import BaseConnector, ClientError, ClientResponse, ClientSession

from ..core.error import BaseError

from .repeat import RepeatSequence


class FetchError(BaseError):
    """Error raised when an HTTP fetch fails."""


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
                            f"Bad response from server: {response.status}"
                        )
                    return await (response.json() if json else response.text())
            except (ClientError, asyncio.TimeoutError) as e:
                if attempt.final:
                    raise FetchError("Exceeded maximum fetch attempts") from e
