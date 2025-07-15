"""Retry utilities for exponential backoff strategy."""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict

from ..messaging.util import str_to_datetime

retry_config: Dict[str, int] = {
    "min_retry_duration_seconds": int(
        os.getenv("ANONCREDS_REVOCATION_MIN_RETRY_DURATION_SECONDS", "2")
    ),
    "max_retry_duration_seconds": int(
        os.getenv("ANONCREDS_REVOCATION_MAX_RETRY_DURATION_SECONDS", "60")
    ),
    "retry_multiplier": float(os.getenv("ANONCREDS_REVOCATION_RETRY_MULTIPLIER", "2.0")),
    "recovery_delay_seconds": int(
        os.getenv("ANONCREDS_REVOCATION_RECOVERY_DELAY_SECONDS", "30")
    ),
}


def calculate_exponential_backoff_delay(retry_count: int) -> int:
    """Calculate exponential backoff delay based on retry count.

    With defaults, retry durations will be: 2, 4, 8, 16, etc, up to the max duration.

    Args:
        retry_count: Current retry count (0-based)

    Returns:
        Delay in seconds for the next retry

    """
    min_duration = retry_config["min_retry_duration_seconds"]
    max_duration = retry_config["max_retry_duration_seconds"]
    multiplier = retry_config["retry_multiplier"]

    # Calculate exponential backoff: min_duration * (multiplier ^ retry_count)
    delay = min_duration * (multiplier**retry_count)

    # Cap at maximum duration
    delay = min(delay, max_duration)

    return int(delay)


def calculate_event_expiry_timestamp(retry_count: int) -> str:
    """Calculate when an event should expire for recovery purposes.

    The expiry timestamp is calculated as:
    current_time + retry_delay + recovery_window

    This ensures that:
    1. First retry (retry_count=0) expires after recovery_delay_seconds
    2. Subsequent retries expire after their backoff delay + recovery window
    3. Recovery middleware only picks up truly expired events

    Args:
        retry_count: Current retry count (0-based)

    Returns:
        ISO format timestamp string when the event should expire

    """
    retry_delay = calculate_exponential_backoff_delay(retry_count)
    recovery_window = retry_config["recovery_delay_seconds"]

    # Total delay = retry delay + recovery window buffer
    total_delay_seconds = retry_delay + recovery_window

    expiry_time = datetime.now(timezone.utc) + timedelta(seconds=total_delay_seconds)

    return expiry_time.isoformat()


def is_event_expired(expiry_timestamp: str) -> bool:
    """Check if an event has expired and is ready for recovery.

    Args:
        expiry_timestamp: ISO format timestamp string

    Returns:
        True if the event has expired, False otherwise

    """
    try:
        expiry_time = str_to_datetime(expiry_timestamp)
        current_time = datetime.now(timezone.utc)

        return current_time >= expiry_time

    except (ValueError, TypeError):
        # If we can't parse the timestamp, consider it expired for safety
        return True


def get_retry_metadata_for_storage(retry_count: int) -> Dict[str, int]:
    """Get retry metadata dictionary for event storage.

    Args:
        retry_count: Current retry count

    Returns:
        Dictionary with retry metadata

    """
    return {
        "retry_count": retry_count,
        "retry_delay_seconds": calculate_exponential_backoff_delay(retry_count),
        "min_retry_duration_seconds": retry_config["min_retry_duration_seconds"],
        "max_retry_duration_seconds": retry_config["max_retry_duration_seconds"],
        "retry_multiplier": retry_config["retry_multiplier"],
        "expiry_timestamp": calculate_event_expiry_timestamp(retry_count),
    }
