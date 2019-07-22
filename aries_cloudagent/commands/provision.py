import asyncio
from argparse import ArgumentParser
from typing import Sequence

from ..config import argparse as arg
from ..config.default_context import DefaultContextBuilder
from ..config.util import common_config
from ..error import BaseError
from ..wallet.base import BaseWallet
from ..wallet.crypto import seed_to_did


class ProvisionError(BaseError):
    """Base exception for provisioning errors."""


def init_argument_parser(parser: ArgumentParser):
    return arg.load_argument_groups(
        parser, arg.GeneralGroup(), arg.LoggingGroup(), arg.WalletGroup()
    )


async def provision(category: str, settings: dict):
    """Perform provisioning."""
    context_builder = DefaultContextBuilder(settings)
    context = await context_builder.build()

    if category == "wallet":
        # Initialize wallet
        wallet: BaseWallet = await context.inject(BaseWallet)
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


def execute(argv: Sequence[str] = None):
    """Entrypoint."""
    parser = ArgumentParser()
    parser.prog += " provision"
    parser.add_argument(
        dest="provision_category",
        type=str,
        metavar=("<category>"),
        choices=["wallet"],
        help="The provision command to invoke",
    )
    get_settings = init_argument_parser(parser)
    args = parser.parse_args(argv)
    settings = get_settings(args)
    common_config(settings)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(provision(args.provision_category, settings))


if __name__ == "__main__":
    execute()
