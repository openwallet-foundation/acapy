"""Provision command for setting up agent settings before starting."""

import asyncio
from argparse import ArgumentParser
from typing import Sequence

from ..config import argparse as arg
from ..config.base import BaseError
from ..config.default_context import DefaultContextBuilder
from ..config.ledger import ledger_config
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
    context = await context_builder.build()

    try:
        public_did = await wallet_config(context, True)

        if await ledger_config(context, public_did, True):
            print("Ledger configured")
        else:
            print("Ledger not configured")
    except BaseError as e:
        raise ProvisionError("Error during provisioning") from e


def execute(argv: Sequence[str] = None):
    """Entrypoint."""
    parser = ArgumentParser()
    parser.prog += " provision"
    get_settings = init_argument_parser(parser)
    args = parser.parse_args(argv)
    settings = get_settings(args)
    common_config(settings)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(provision(settings))


if __name__ == "__main__":
    execute()
