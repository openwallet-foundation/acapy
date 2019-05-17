"""Utils for messages."""

import asyncio
from datetime import datetime, timedelta, timezone
import os
import logging
from math import floor
import re
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
