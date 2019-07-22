"""Entrypoint."""

import asyncio
import os
from typing import Any, Mapping

from aiohttp import ClientSession

from .logging import LoggingConfigurator
from ..postgres import load_postgres_plugin


async def get_genesis_transactions(genesis_url: str):
    """Get genesis transactions."""
    headers = {}
    headers["Content-Type"] = "application/json"
    async with ClientSession() as client_session:
        response = await client_session.get(genesis_url, headers=headers)
        genesis_txns = await response.text()
        return genesis_txns


def common_config(settings: Mapping[str, Any]):
    # Set up logging
    log_config = settings.get("log.config")
    log_level = settings.get("log.level") or os.getenv("LOG_LEVEL")
    LoggingConfigurator.configure(log_config, log_level)

    # Fetch genesis transactions if necessary
    if not settings.get("ledger.genesis_transactions") and settings.get(
        "ledger.genesis_url"
    ):
        loop = asyncio.get_event_loop()
        settings["ledger.genesis_transactions"] = loop.run_until_complete(
            get_genesis_transactions(settings["ledger.genesis_url"])
        )

    # Load postgres plug-in if necessary
    if (
        settings.get("wallet.type") == "indy"
        and settings.get("wallet.storage_type") == "postgres_storage"
    ):
        load_postgres_plugin()
