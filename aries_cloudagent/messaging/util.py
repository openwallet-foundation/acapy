"""Utils for messages."""

import asyncio
from datetime import datetime, timedelta, timezone
import os
import logging
from math import floor
import re
from typing import Union

import aiohttp

from ..config.injection_context import InjectionContext

LOGGER = logging.getLogger(__name__)


class WebhookTransport:
    """Class for managing webhook delivery."""

    def __init__(
        self, target_url: str, default_retries: int = 5, default_wait: int = 5
    ):
        """Initialize the WebhookTransport instance."""
        self.target_url = target_url
        self.client_session: aiohttp.ClientSession = None
        self.default_retries = default_retries
        self.default_wait = default_wait
        self.stop_event = asyncio.Event()

    async def start(self):
        """Start the transport."""
        await self.stop_event.wait()

    def stop(self):
        """Stop the transport."""
        self.stop_event.set()
        if self.client_session:
            self.client_session.close()
            self.client_session = None

    async def send(self, topic: str, payload, retries: int = None):
        """Send a webhook to the registered endpoint."""
        if not self.client_session:
            self.client_session = aiohttp.ClientSession()
        full_webhook_url = f"{self.target_url}/topic/{topic}/"
        LOGGER.info(f"Sending webhook to {full_webhook_url}")
        if retries is None:
            retries = self.default_retries or 0
        try:
            async with self.client_session.post(
                full_webhook_url, json=payload
            ) as response:
                if response.status < 200 or response.status > 299:
                    raise Exception()
        except Exception:
            if retries > 0:
                await asyncio.sleep(self.default_wait)
                await self.send(topic, payload, retries - 1)

    @classmethod
    async def perform_send(
        cls, context: InjectionContext, topic: str, payload, retries: int = None
    ):
        """Look up the registered WebhookTransport and send the message."""
        server: WebhookTransport = await context.inject(
            WebhookTransport, required=False
        )
        if server:
            await server.send(topic, payload, retries)


async def init_webhooks(context: InjectionContext):
    """Register a standard WebhookTransport in the context."""
    webhook_url = os.environ.get("WEBHOOK_URL")
    if webhook_url:
        context.injector.bind_instance(WebhookTransport, WebhookTransport(webhook_url))
    else:
        LOGGER.warning("WEBHOOK_URL is not set")


async def stop_webhooks(context: InjectionContext):
    """Register a standard WebhookTransport in the context."""
    instance = await context.inject(WebhookTransport, required=False)
    if instance:
        instance.stop()


def send_webhook(
    context: InjectionContext, topic: str, payload, *, retries: int = None
):
    """Send a webhook to the active WebhookTransport if present."""
    asyncio.ensure_future(
        WebhookTransport.perform_send(context, topic, payload, retries)
    )


def datetime_to_str(dt: Union[str, datetime]) -> str:
    """Convert a datetime object to an indy-standard datetime string.

    Args:
        dt: May be a string or datetime to allow automatic conversion
    """
    if isinstance(dt, datetime):
        dt = dt.replace(tzinfo=timezone.utc).isoformat(" ").replace("+00:00", "Z")
    return dt


def str_to_datetime(dt: Union[str, datetime]) -> datetime:
    """Convert an indy-standard datetime string to a datetime.

    Using a fairly lax regex pattern to match slightly different formats.
    In Python 3.7 datetime.fromisoformat might be used.

    Args:
        dt: May be a string or datetime to allow automatic conversion
    """
    if isinstance(dt, str):
        match = re.match(
            r"^(\d{4})-(\d\d)-(\d\d)[T ](\d\d):(\d\d)"
            r"(?:\:(\d\d(?:\.\d{1,6})?))?([+-]\d\d:?\d\d|Z)$",
            dt,
        )
        if not match:
            raise ValueError("String does not match expected time format")
        year, month, day = match[1], match[2], match[3]
        hour, minute, second = match[4], match[5], match[6]
        tz = match[7]
        if not second:
            second = 0
            microsecond = 0
        else:
            flt_second = float(second)
            second = floor(flt_second)
            microsecond = round((flt_second - second) * 1_000_000)
        result = datetime(
            int(year),
            int(month),
            int(day),
            int(hour),
            int(minute),
            int(second),
            microsecond,
            timezone.utc,
        )
        if tz != "Z":
            tz_sgn = int(tz[0] + "1")
            tz_hours = int(tz[1:3])
            tz_mins = int(tz[-2:])
            if tz_hours or tz_mins:
                result = result - timedelta(minutes=tz_sgn * (tz_hours * 60 + tz_mins))
        return result
    return dt


def datetime_now() -> datetime:
    """Timestamp in UTC."""
    return datetime.utcnow().replace(tzinfo=timezone.utc)


def time_now() -> str:
    """Timestamp in ISO format."""
    return datetime_to_str(datetime_now())
