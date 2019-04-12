import asyncio
import os
import logging

import aiohttp

LOGGER = logging.getLogger(__name__)

WEBHOOK_URL = os.environ.get("WEBHOOK_URL")


async def send_webhook(topic, payload, retries=5):
    if not WEBHOOK_URL:
        LOGGER.warning("WEBHOOK_URL is not set")

    async with aiohttp.ClientSession() as session:
        full_webhook_url = f"{WEBHOOK_URL}/topic/{topic}/"
        LOGGER.info(f"Sending webhook to {full_webhook_url}")
        try:
            response = await session.post(full_webhook_url, json=payload)
            if response.status < 200 or response.status > 299:
                raise Exception()
        except:
            if retries > 0:
                await asyncio.sleep(5)
                await send_webhook(topic, payload, retries - 1)
