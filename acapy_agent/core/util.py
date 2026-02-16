"""Core utilities and constants."""

import re

CORE_EVENT_PREFIX = "acapy::core::"
STARTUP_EVENT_TOPIC = CORE_EVENT_PREFIX + "startup"
STARTUP_EVENT_PATTERN = re.compile(f"^{STARTUP_EVENT_TOPIC}?$")
SHUTDOWN_EVENT_TOPIC = CORE_EVENT_PREFIX + "shutdown"
SHUTDOWN_EVENT_PATTERN = re.compile(f"^{SHUTDOWN_EVENT_TOPIC}?$")
MULTITENANT_EVENT_PREFIX = CORE_EVENT_PREFIX + "multitenant::"
MULTITENANT_WALLET_CREATED_TOPIC = MULTITENANT_EVENT_PREFIX + "wallet::created"
MULTITENANT_WALLET_CREATED_PATTERN = re.compile(
    f"^{MULTITENANT_WALLET_CREATED_TOPIC}::[a-zA-Z0-9-]+$"
)
WARNING_DEGRADED_FEATURES = "version-with-degraded-features"
WARNING_VERSION_MISMATCH = "fields-ignored-due-to-version-mismatch"
WARNING_VERSION_NOT_SUPPORTED = "version-not-supported"
