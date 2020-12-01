"""Provision command for setting up agent settings before starting."""

import asyncio
from configargparse import ArgumentParser
from typing import Sequence

from ..config import argparse as arg
from ..config.default_context import DefaultContextBuilder
from ..config.base import BaseError
from ..config.ledger import get_genesis_transactions, ledger_config
from ..config.util import common_config
from ..config.wallet import wallet_config


class ProvisionError(BaseError):
    """Base exception for provisioning errors."""


def init_argument_parser(parser: ArgumentParser):
    """Initialize an argument parser with the module's arguments."""
    return arg.load_argument_groups(
        parser, *arg.group.get_registered(arg.CAT_PROVISION)
    )


async def provision(settings: dict):
    """Perform provisioning."""
    context_builder = DefaultContextBuilder(settings)
    context = await context_builder.build_context()

    try:
        await get_genesis_transactions(context.settings)

        root_profile, public_did = await wallet_config(context, provision=True)

        if await ledger_config(root_profile, public_did and public_did.did, True):
            print("Ledger configured")
        else:
            print("Ledger not configured")

        await root_profile.close()
    except BaseError as e:
        raise ProvisionError("Error during provisioning") from e


def execute(argv: Sequence[str] = None):
    """Entrypoint."""
    parser = arg.create_argument_parser()
    parser.prog += " provision"
    get_settings = init_argument_parser(parser)
    args = parser.parse_args(argv)
    settings = get_settings(args)
    common_config(settings)

    # provision needs write access to the ledger
    # (override if specified otherwise)
    settings["ledger.read_only"] = False

    loop = asyncio.get_event_loop()
    loop.run_until_complete(provision(settings))


def main():
    """Execute the main line."""
    if __name__ == "__main__":
        execute()


main()
