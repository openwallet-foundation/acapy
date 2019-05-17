"""Utils for messages."""

import asyncio
import datetime
import os
import logging
from typing import Union

import aiohttp

LOGGER = logging.getLogger(__name__)

WEBHOOK_URL = os.environ.get("WEBHOOK_URL")


async def send_webhook(topic, payload, retries=5):
    """Send a webhook to WEBHOOK_URL if set."""
    if not WEBHOOK_URL:
        LOGGER.warning("WEBHOOK_URL is not set")
        return

    async with aiohttp.ClientSession() as session:
        full_webhook_url = f"{WEBHOOK_URL}/topic/{topic}/"
        LOGGER.info(f"Sending webhook to {full_webhook_url}")
        try:
            response = await session.post(full_webhook_url, json=payload)
            if response.status < 200 or response.status > 299:
                raise Exception()
        except Exception:
            if retries > 0:
                await asyncio.sleep(5)
                await send_webhook(topic, payload, retries - 1)


def time_now(datetime_format=False) -> Union[str, datetime.datetime]:
    """Timestamp in ISO format."""
    dt = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    if datetime_format:
        return dt
    return dt.isoformat(" ")
