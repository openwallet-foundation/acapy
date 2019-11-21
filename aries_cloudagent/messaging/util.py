"""Utils for messages."""

from datetime import datetime, timedelta, timezone
import logging
from math import floor
import re
from typing import Union

LOGGER = logging.getLogger(__name__)


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
            r"(?:\:(\d\d(?:\.\d{1,6})?))?([+-]\d\d:?\d\d|Z|)$",
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
        if tz != "Z" and tz != "":
            tz_sgn = int(tz[0] + "1")
            tz_hours = int(tz[1:3])
            tz_mins = int(tz[-2:])
            if tz_hours or tz_mins:
                result = result - timedelta(minutes=tz_sgn * (tz_hours * 60 + tz_mins))
        return result
    return dt


def str_to_epoch(dt: Union[str, datetime]) -> int:
    """Convert an indy-standard datetime string to epoch seconds.

    Args:
        dt: May be a string or datetime to allow automatic conversion

    """
    return int(str_to_datetime(dt).timestamp())


def epoch_to_str(epoch: int) -> str:
    """Convert epoch seconds to indy-standard datetime string.

    Args:
        epoch: epoch seconds

    """
    return datetime_to_str(datetime.fromtimestamp(epoch, tz=timezone.utc))


def datetime_now() -> datetime:
    """Timestamp in UTC."""
    return datetime.utcnow().replace(tzinfo=timezone.utc)


def time_now() -> str:
    """Timestamp in ISO format."""
    return datetime_to_str(datetime_now())


def canon(raw_attr_name: str) -> str:
    """
    Canonicalize input attribute name for indy proofs and credential offers.

    Args:
        raw_attr_name: raw attribute name

    Returns:
        canonicalized attribute name

    """
    if raw_attr_name:  # do not dereference None, and "" is already canonical
        return raw_attr_name.replace(" ", "").lower()
    return raw_attr_name
