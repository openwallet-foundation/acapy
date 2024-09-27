"""aiohttp stats collector support."""

import aiohttp

from ..utils.stats import Collector


class StatsTracer(aiohttp.TraceConfig):
    """Attach hooks to client session events and report statistics."""

    def __init__(self, collector: Collector, prefix: str):
        """Initialize the `StatsTracer` instance."""
        super().__init__()
        self.collector = collector
        self.prefix = prefix
        self.on_request_start.append(self.request_start)
        self.on_connection_queued_start.append(self.connection_queued_start)
        self.on_connection_queued_end.append(self.connection_queued_end)
        self.on_dns_resolvehost_start.append(self.dns_resolvehost_start)
        self.on_dns_resolvehost_end.append(self.dns_resolvehost_end)
        self.on_connection_create_start.append(self.socket_connect_start)
        self.on_dns_cache_hit.append(self.socket_connect_start)  # restart timer
        self.on_dns_cache_miss.append(self.socket_connect_start)  # restart timer
        self.on_connection_reuseconn.append(self.connection_ready)
        self.on_connection_create_end.append(self.connection_ready)
        self.on_request_end.append(self.request_end)

    async def request_start(self, session, context, params):
        """Handle the start of a request."""
        context.method, context.url = params.method, params.url

    async def connection_queued_start(self, session, context, params):
        """Handle the start of a queued connection."""
        context.queue_timer = self.collector.timer(self.prefix + "queued").start()

    async def connection_queued_end(self, session, context, params):
        """Handle the end of a queued connection."""
        context.queue_timer.stop()

    async def dns_resolvehost_start(self, session, context, params):
        """Handle the start of a DNS resolution."""
        context.dns_timer = self.collector.timer(self.prefix + "dns_resolve").start()

    async def dns_resolvehost_end(self, session, context, params):
        """Handle the end of a DNS resolution."""
        context.dns_timer.stop()

    async def socket_connect_start(self, session, context, params):
        """Handle the start of a socket connection."""
        context.socket_timer = self.collector.timer(self.prefix + "connect").start()

    async def connection_ready(self, session, context, params):
        """Handle the end of connection acquisition."""
        try:
            context.socket_timer.stop()
        except AttributeError:
            pass
        context.fetch_timer = self.collector.timer(self.prefix + context.method).start()

    async def request_end(self, session, context, params):
        """Handle the end of request."""
        context.fetch_timer.stop()
