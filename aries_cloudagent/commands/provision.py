"""Provision command for setting up agent settings before starting."""

import asyncio
from argparse import ArgumentParser
from typing import Sequence

from ..config import argparse as arg
from ..config.default_context import DefaultContextBuilder
from ..config.ledger import ledger_config
from ..config.util import common_config
from ..error import BaseError
from ..wallet.base import BaseWallet
from ..wallet.crypto import seed_to_did


class ProvisionError(BaseError):
    """Base exception for provisioning errors."""


def init_argument_parser(parser: ArgumentParser):
    """Initialize an argument parser with the module's arguments."""
    return arg.load_argument_groups(
        parser, *arg.group.get_registered(arg.CAT_PROVISION)
    )


async def provision(category: str, settings: dict):
    """Perform provisioning."""
    context_builder = DefaultContextBuilder(settings)
    context = await context_builder.build()

    # Initialize wallet
    wallet: BaseWallet = await context.inject(BaseWallet)
    if wallet.type != "indy":
        raise ProvisionError("Cannot provision a non-Indy wallet type")
    if wallet.created:
        print("Created new wallet")
    else:
        print("Opened existing wallet")
    print("Wallet type:", wallet.type)
    print("Wallet name:", wallet.name)
    wallet_seed = context.settings.get("wallet.seed")
    public_did_info = await wallet.get_public_did()
    if public_did_info:
        # If we already have a registered public did and it doesn't match
        # the one derived from `wallet_seed` then we error out.
        # TODO: Add a command to change public did explicitly
        if wallet_seed and seed_to_did(wallet_seed) != public_did_info.did:
            raise ProvisionError(
                "New seed provided which doesn't match the registered"
                + f" public did {public_did_info.did}"
            )
    elif wallet_seed:
        public_did_info = await wallet.create_public_did(seed=wallet_seed)
        print("Created new public DID")
    if public_did_info:
        print("Public DID:", public_did_info.did)
        print("Verkey:", public_did_info.verkey)
    else:
        print("No public DID")

    await ledger_config(context, public_did_info and public_did_info.did, True)


def execute(argv: Sequence[str] = None):
    """Entrypoint."""
    parser = ArgumentParser()
    parser.prog += " provision"
    get_settings = init_argument_parser(parser)
    args = parser.parse_args(argv)
    settings = get_settings(args)
    common_config(settings)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(provision(args.provision_category, settings))


if __name__ == "__main__":
    execute()
