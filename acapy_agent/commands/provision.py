"""Provision command for setting up agent settings before starting."""

import asyncio
import logging
from typing import Sequence

from configargparse import ArgumentParser

from ..config import argparse as arg
from ..config.base import BaseError
from ..config.default_context import DefaultContextBuilder
from ..config.util import common_config
from ..config.wallet import wallet_config
from ..protocols.coordinate_mediation.mediation_invite_store import (
    MediationInviteRecord,
    MediationInviteStore,
)
from ..storage.base import BaseStorage
from . import PROG

LOGGER = logging.getLogger(__name__)


class ProvisionError(BaseError):
    """Base exception for provisioning errors."""


def init_argument_parser(parser: ArgumentParser):
    """Initialize an argument parser with the module's arguments."""
    return arg.load_argument_groups(parser, *arg.group.get_registered(arg.CAT_PROVISION))


async def provision(settings: dict):
    """Perform provisioning."""
    context_builder = DefaultContextBuilder(settings)
    context = await context_builder.build_context()

    try:
        root_profile, _ = await wallet_config(context, provision=True)

        # store mediator invite url if provided
        mediation_invite = settings.get("mediation.invite", None)
        if mediation_invite:
            async with root_profile.session() as session:
                await MediationInviteStore(session.context.inject(BaseStorage)).store(
                    MediationInviteRecord.unused(mediation_invite)
                )

        await root_profile.close()
    except BaseError as e:
        raise ProvisionError("Error during provisioning") from e


def execute(argv: Sequence[str] = None):
    """Entrypoint."""
    # Preprocess argv to handle --arg-file-url
    if argv:
        argv = arg.preprocess_args_for_remote_config(list(argv))

    parser = arg.create_argument_parser(prog=PROG)
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
