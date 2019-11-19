"""Http outbound transport."""

import logging
from typing import Union

from aiohttp import ClientSession, DummyCookieJar, TCPConnector

from ..stats import StatsTracer

from .base import BaseOutboundTransport, OutboundTransportError


class HttpTransport(BaseOutboundTransport):
    """Http outbound transport class."""

    schemes = ("http", "https")

    def __init__(self) -> None:
        """Initialize an `HttpTransport` instance."""
        super(HttpTransport, self).__init__()
        self.client_session: ClientSession = None
        self.connector: TCPConnector = None
        self.logger = logging.getLogger(__name__)

    async def start(self):
        """Start the transport."""
        session_args = {}
        self.connector = TCPConnector(limit=200, limit_per_host=50)
        if self.collector:
            session_args["trace_configs"] = [
                StatsTracer(self.collector, "outbound-http:")
            ]
        session_args["cookie_jar"] = DummyCookieJar()
        session_args["connector"] = self.connector
        self.client_session = ClientSession(**session_args)
        return self

    async def stop(self):
        """Stop the transport."""
        await self.client_session.close()
        self.client_session = None

    async def handle_message(self, payload: Union[str, bytes], endpoint: str):
        """
        Handle message from queue.

        Args:
            message: `OutboundMessage` to send over transport implementation
        """
        if not endpoint:
            raise OutboundTransportError("No endpoint provided")
        headers = {}
        if isinstance(payload, bytes):
            headers["Content-Type"] = "application/ssi-agent-wire"
        else:
            headers["Content-Type"] = "application/json"
        async with self.client_session.post(
            endpoint, data=payload, headers=headers
        ) as response:
            if response.status < 200 or response.status > 299:
                raise OutboundTransportError("Unexpected response status")
