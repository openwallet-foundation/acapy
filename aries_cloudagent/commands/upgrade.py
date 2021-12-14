"""Upgrade command for handling breaking changes when updating ACA-PY versions."""

import asyncio
from configargparse import ArgumentParser
from typing import Sequence

from ..core.profile import Profile
from ..config import argparse as arg
from ..config.default_context import DefaultContextBuilder
from ..config.base import BaseError
from ..config.util import common_config
from ..config.wallet import wallet_config
from ..messaging.models.base_record import BaseRecord, BaseExchangeRecord
from ..utils.classloader import ClassLoader, ClassNotFoundError

from . import PROG


class UpgradeError(BaseError):
    """Base exception for upgrade related errors."""


def init_argument_parser(parser: ArgumentParser):
    """Initialize an argument parser with the module's arguments."""
    return arg.load_argument_groups(parser, *arg.group.get_registered(arg.CAT_UPGRADE))


async def upgrade(settings: dict):
    """Perform upgradation steps."""
    context_builder = DefaultContextBuilder(settings)
    context = await context_builder.build_context()
    try:
        root_profile, public_did = await wallet_config(context)
        # Step 1 re-saving all BaseRecord and BaseExchangeRecord
        resave_record_paths = settings.get("upgrade.resave_records")
        for record_path in resave_record_paths:
            try:
                record_type = ClassLoader.load_class(record_path)
            except ClassNotFoundError as err:
                raise UpgradeError(f"Unknown Record type {record_path}") from err
            if not issubclass(record_type, BaseRecord) and not issubclass(
                record_type, BaseExchangeRecord
            ):
                raise UpgradeError(
                    "Only BaseRecord and BaseExchangeRecord can be resaved"
                    f", found: {str(record_type)}"
                )
            async with root_profile.session() as session:
                all_records = await record_type.query(session)
                for record in all_records:
                    await record.save(
                        session, reason="re-saving record during ACA-Py upgradation"
                    )
                print(f"All records of {str(record_type)} successfully re-saved.")
        # Step 2 Update existing records, if required
        if settings.get("upgrade.update_existing_records"):
            await update_existing_records(root_profile)
        await root_profile.close()
    except BaseError as e:
        raise UpgradeError(f"Error during upgrade: {e}")


async def update_existing_records(profile: Profile):
    """
    Handle addition of required attributes to Marshmallow schema.

    Args:
        profile: Root profile

    """
    pass


def execute(argv: Sequence[str] = None):
    """Entrypoint."""
    parser = arg.create_argument_parser(prog=PROG)
    parser.prog += " upgrade"
    get_settings = init_argument_parser(parser)
    args = parser.parse_args(argv)
    settings = get_settings(args)
    common_config(settings)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(upgrade(settings))


def main():
    """Execute the main line."""
    if __name__ == "__main__":
        execute()


main()
