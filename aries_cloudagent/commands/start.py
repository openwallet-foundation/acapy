"""Entrypoint."""

import asyncio
import functools
import os
import signal
from argparse import ArgumentParser
from typing import Sequence

from ..conductor import Conductor
from ..config import argparse as arg
from ..config.default_context import DefaultContextBuilder
from ..config.util import common_config


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


def init_argument_parser(parser: ArgumentParser):
    return arg.load_argument_groups(
        parser,
        arg.AdminGroup(),
        arg.DebugGroup(),
        arg.GeneralGroup(),
        arg.LedgerGroup(),
        arg.LoggingGroup(),
        arg.ProtocolGroup(),
        arg.TransportGroup(),
        arg.WalletGroup(),
    )


def execute(argv: Sequence[str] = None):
    """Entrypoint."""
    parser = ArgumentParser()
    parser.prog += " start"
    get_settings = init_argument_parser(parser)
    args = parser.parse_args(argv)
    settings = get_settings(args)
    common_config(settings)

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
    execute()
