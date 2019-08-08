"""Entrypoint."""

import os
from typing import Any, Mapping

from .logging import LoggingConfigurator
from ..postgres import load_postgres_plugin


def common_config(settings: Mapping[str, Any]):
    """Perform common app configuration."""
    # Set up logging
    log_config = settings.get("log.config")
    log_level = settings.get("log.level") or os.getenv("LOG_LEVEL")
    log_file = settings.get("log.file")
    LoggingConfigurator.configure(log_config, log_level, log_file)

    # Load postgres plug-in if necessary
    if (
        settings.get("wallet.type") == "indy"
        and settings.get("wallet.storage_type") == "postgres_storage"
    ):
        load_postgres_plugin()
