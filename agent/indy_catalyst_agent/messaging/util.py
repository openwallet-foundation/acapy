import os
import logging

import aiohttp

LOGGER = logging.getLogger(__name__)

WEBHOOK_URL = os.environ.get()


async def send_webhook(topic, payload, retries=5):
    if not WEBHOOK_URL:
        LOGGER.warning("WEBHOOK_URL is not set")

    async with aiohttp.ClientSession() as session:
        full_webhook_url = f"{WEBHOOK_URL}/topic/{topic}"
        LOGGER.info(f"Sending webhook to {full_webhook_url}")
        await session.post(full_webhook_url, json=payload)
