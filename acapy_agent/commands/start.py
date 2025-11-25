"""Entrypoint."""

import asyncio
import logging
import signal
import sys
from typing import Sequence

from configargparse import ArgumentParser

from ..config.error import ArgsParseError

try:
    import uvloop
except ImportError:
    uvloop = None

from ..config import argparse as arg
from ..config.default_context import DefaultContextBuilder
from ..config.util import common_config
from ..core.conductor import Conductor
from ..utils.plugin_installer import install_plugins_from_config
from ..version import __version__ as acapy_version
from . import PROG

LOGGER = logging.getLogger(__name__)


async def start_app(conductor: Conductor):
    """Start up the application."""
    await conductor.setup()
    await conductor.start()


async def shutdown_app(conductor: Conductor):
    """Shut down the application."""
    LOGGER.info("Shutting down")
    await conductor.stop()

    # Cancel remaining tasks
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


def init_argument_parser(parser: ArgumentParser):
    """Initialize an argument parser with the module's arguments."""
    return arg.load_argument_groups(parser, *arg.group.get_registered(arg.CAT_START))


async def run_app(argv: Sequence[str] = None):
    """Main async runner for the app."""
    # Preprocess argv to handle --arg-file-url
    if argv:
        argv = arg.preprocess_args_for_remote_config(list(argv))

    parser = arg.create_argument_parser(prog=PROG)
    parser.prog += " start"
    get_settings = init_argument_parser(parser)
    args = parser.parse_args(argv)
    settings = get_settings(args)
    common_config(settings)

    # Install plugins if auto-install is enabled and plugins are specified
    external_plugins = settings.get("external_plugins", [])
    if external_plugins:
        auto_install = settings.get("auto_install_plugins", False)
        plugin_version = settings.get("plugin_install_version")

        if auto_install:
            version_info = (
                f"version {plugin_version}"
                if plugin_version
                else f"current ACA-Py version ({acapy_version})"
            )
            LOGGER.info(
                "Auto-installing plugins from acapy-plugins repository: %s (%s)",
                ", ".join(external_plugins),
                version_info,
            )

            failed_plugins = install_plugins_from_config(
                plugin_names=external_plugins,
                auto_install=auto_install,
                plugin_version=plugin_version,
            )

            if failed_plugins:
                LOGGER.error(
                    "Failed to install the following plugins: %s. "
                    "Please ensure these plugins are available in the "
                    "acapy-plugins repository or install them manually before "
                    "starting ACA-Py.",
                    ", ".join(failed_plugins),
                )
                sys.exit(1)

    # Set ledger to read-only if explicitly specified
    settings["ledger.read_only"] = settings.get("read_only_ledger", False)

    if uvloop:
        uvloop.install()
        LOGGER.info("uvloop installed")

    context_builder = DefaultContextBuilder(settings)
    conductor = Conductor(context_builder)

    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()

    def handle_signal():
        LOGGER.info("Received stop signal")
        shutdown_event.set()

    loop.add_signal_handler(signal.SIGTERM, handle_signal)
    loop.add_signal_handler(signal.SIGINT, handle_signal)

    try:
        await start_app(conductor)
        await shutdown_event.wait()
    finally:
        await shutdown_app(conductor)


def execute(argv: Sequence[str] = None):
    """Entrypoint."""
    try:
        asyncio.run(run_app(argv))
    except ArgsParseError as e:
        LOGGER.error("Argument parsing error: %s", e)
        raise e
    except KeyboardInterrupt:
        LOGGER.info("Interrupted by user")
    except Exception:
        LOGGER.exception("Unexpected exception during execution")
        sys.exit(1)


def main():
    """Execute the main line."""
    execute()


if __name__ == "__main__":
    main()
