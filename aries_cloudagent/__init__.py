"""Entrypoint."""

import asyncio
import functools
import os
import signal

from aiohttp import ClientSession

from .conductor import Conductor
from .config.argparse import get_settings, parse_args
from .config.default_context import DefaultContextBuilder
from .config.logging import LoggingConfigurator
from .postgres import load_postgres_plugin


async def get_genesis_transactions(genesis_url: str):
    """Get genesis transactions."""
    headers = {}
    headers["Content-Type"] = "application/json"
    async with ClientSession() as client_session:
        response = await client_session.get(genesis_url, headers=headers)
        genesis_txns = await response.text()
        return genesis_txns


async def start_app(conductor: Conductor):
    """Start up."""
    await conductor.setup()
    await conductor.start()


async def shutdown_app(conductor: Conductor):
    """Shut down."""
    print("\nShutting down")
    await conductor.stop()
    tasks = [
        task
        for task in asyncio.Task.all_tasks()
        if task is not asyncio.tasks.Task.current_task()
    ]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    asyncio.get_event_loop().stop()


def main():
    """Entrypoint."""
    args = parse_args()
    settings = get_settings(args)

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
        settings.get("wallet.type")
        and settings.get("wallet.storage_type") == "postgres_storage"
    ):
        if args.wallet_storage_type == "postgres_storage":
            load_postgres_plugin()

    # Support WEBHOOK_URL environment variable
    webhook_url = os.environ.get("WEBHOOK_URL")
    if webhook_url:
        webhook_urls = list(settings.get("admin.webhook_urls") or [])
        webhook_urls.append(webhook_url)
        settings["admin.webhook_urls"] = webhook_urls

    # Create the Conductor instance
    context_builder = DefaultContextBuilder(settings)
    conductor = Conductor(context_builder)

    # Run the application
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(
        signal.SIGTERM,
        functools.partial(asyncio.ensure_future, shutdown_app(conductor), loop=loop),
    )
    asyncio.ensure_future(start_app(conductor), loop=loop)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(shutdown_app(conductor))


if __name__ == "__main__":
    main()  # pragma: no cover
