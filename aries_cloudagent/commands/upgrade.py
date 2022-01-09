"""Upgrade command for handling breaking changes when updating ACA-PY versions."""

import asyncio
import yaml

from configargparse import ArgumentParser
from packaging import version as package_version
from typing import Callable, Sequence, Optional

from ..core.profile import Profile
from ..config import argparse as arg
from ..config.default_context import DefaultContextBuilder
from ..config.base import BaseError
from ..config.util import common_config
from ..config.wallet import wallet_config
from ..messaging.models.base_record import BaseRecord
from ..storage.base import BaseStorage
from ..storage.error import StorageNotFoundError
from ..storage.record import StorageRecord
from ..utils.classloader import ClassLoader, ClassNotFoundError
from ..version import __version__, RECORD_TYPE_ACAPY_VERSION

from . import PROG

DEFAULT_UPGRADE_CONFIG_PATH = (
    "./aries_cloudagent/commands/default_version_upgrade_config.yml"
)


class UpgradeError(BaseError):
    """Base exception for upgrade related errors."""


class VersionUpgradeConfig:
    """Handle ACA-Py version upgrade config."""

    def __init__(self, config_path: str = None):
        """Initialize config for use during upgrade process."""
        self.function_map_config = {}
        self.upgrade_configs = {}
        self.setup_executable_map_config(CONFIG_v7_3)
        if config_path:
            self.setup_version_upgrade_config(config_path)
        else:
            self.setup_version_upgrade_config(DEFAULT_UPGRADE_CONFIG_PATH)

    def setup_executable_map_config(self, config_dict: dict):
        """Set ups config with reference to functions mapped to versions."""
        for version, config in config_dict.items():
            self.function_map_config[version] = {}
            if "update_existing_function_inst" in config:
                self.function_map_config[version][
                    "update_existing_function_inst"
                ] = config.get("update_existing_function_inst")

    def setup_version_upgrade_config(self, path: str):
        """Set ups config dict from the provided YML file."""
        with open(path, "r") as stream:
            config_dict = yaml.safe_load(stream)
            version_config_dict = {}
            for version, provided_config in config_dict.items():
                recs_list = []
                version_config_dict[version] = {}
                if "resave_records" in provided_config:
                    if provided_config.get("resave_records").get("base_record_path"):
                        recs_list = recs_list + provided_config.get(
                            "resave_records"
                        ).get("base_record_path")
                    if provided_config.get("resave_records").get(
                        "base_exch_record_path"
                    ):
                        recs_list = recs_list + provided_config.get(
                            "resave_records"
                        ).get("base_exch_record_path")
                version_config_dict[version]["resave_records"] = recs_list
                version_config_dict[version]["update_existing_records"] = (
                    provided_config.get("update_existing_records") or False
                )
            if version_config_dict == {}:
                raise UpgradeError(f"No version configs found in {path}")
            self.upgrade_configs = version_config_dict

    def get_update_existing_func(self, ver: str) -> Optional[Callable]:
        """Return callable update_existing_records function for specific version."""
        if ver in self.function_map_config:
            return self.function_map_config.get(ver).get(
                "update_existing_function_inst"
            )
        else:
            return None


def init_argument_parser(parser: ArgumentParser):
    """Initialize an argument parser with the module's arguments."""
    return arg.load_argument_groups(parser, *arg.group.get_registered(arg.CAT_UPGRADE))


async def upgrade(settings: dict):
    """Perform upgradation steps."""
    context_builder = DefaultContextBuilder(settings)
    context = await context_builder.build_context()
    try:
        version_upgrade_config_inst = VersionUpgradeConfig(
            settings.get("upgrade.config_path")
        )
        upgrade_configs = version_upgrade_config_inst.upgrade_configs
        root_profile, public_did = await wallet_config(context)
        version_storage_record = None
        upgrade_to_version = f"v{__version__}"
        versions_found_in_config = upgrade_configs.keys()
        sorted_versions_found_in_config = sorted(
            versions_found_in_config, key=lambda x: package_version.parse(x)
        )
        async with root_profile.session() as session:
            storage = session.inject(BaseStorage)
            try:
                version_storage_record = await storage.find_record(
                    type_filter=RECORD_TYPE_ACAPY_VERSION, tag_query={}
                )
                upgrade_from_version = version_storage_record.value
                if "upgrade.from_version" in settings:
                    print(
                        (
                            f"version {upgrade_from_version} found in storage"
                            ", --from-version will be ignored."
                        )
                    )
            except StorageNotFoundError:
                if "upgrade.from_version" in settings:
                    upgrade_from_version = settings.get("upgrade.from_version")
                else:
                    upgrade_from_version = sorted_versions_found_in_config[-1]
                    print(
                        "No ACA-Py version found in wallet storage and "
                        "no --from-version specified. Selecting "
                        f"{upgrade_from_version} as --from-version from "
                        "the config."
                    )
        if upgrade_from_version == upgrade_to_version:
            raise UpgradeError(
                f"Version {upgrade_from_version} to upgrade from and "
                f"current version to upgrade to {upgrade_to_version} "
                "are same."
            )
        if upgrade_from_version not in sorted_versions_found_in_config:
            raise UpgradeError(
                f"No upgrade configuration found for {upgrade_from_version}"
            )
        upgrade_from_version_index = sorted_versions_found_in_config.index(
            upgrade_from_version
        )
        for config_from_version in sorted_versions_found_in_config[
            upgrade_from_version_index:
        ]:
            print(f"Running upgrade process for {config_from_version}")
            upgrade_config = upgrade_configs.get(config_from_version)
            # Step 1 re-saving all BaseRecord and BaseExchangeRecord
            if "resave_records" in upgrade_config:
                resave_record_paths = upgrade_config.get("resave_records")
                for record_path in resave_record_paths:
                    try:
                        record_type = ClassLoader.load_class(record_path)
                    except ClassNotFoundError as err:
                        raise UpgradeError(
                            f"Unknown Record type {record_path}"
                        ) from err
                    if not issubclass(record_type, BaseRecord):
                        raise UpgradeError(
                            f"Only BaseRecord can be resaved, found: {str(record_type)}"
                        )
                    async with root_profile.session() as session:
                        all_records = await record_type.query(session)
                        for record in all_records:
                            await record.save(
                                session,
                                reason="re-saving record during ACA-Py upgrade process",
                            )
                        if len(all_records) == 0:
                            print(f"No records of {str(record_type)} found")
                        else:
                            print(
                                f"All records of {str(record_type)} successfully re-saved"
                            )
            # Step 2 Update existing records, if required
            if (
                "update_existing_records" in upgrade_config
                and upgrade_config.get("update_existing_records") is True
            ):
                update_existing_recs_callable = (
                    version_upgrade_config_inst.get_update_existing_func(
                        config_from_version
                    )
                )
                if not update_existing_recs_callable:
                    raise UpgradeError(
                        "No update_existing_records function "
                        f"specified for {config_from_version}"
                    )
                await update_existing_recs_callable(root_profile)
        # Update storage version
        async with root_profile.session() as session:
            storage = session.inject(BaseStorage)
            if not version_storage_record:
                await storage.add_record(
                    StorageRecord(
                        RECORD_TYPE_ACAPY_VERSION,
                        upgrade_to_version,
                    )
                )
            else:
                await storage.update_record(
                    version_storage_record, upgrade_to_version, {}
                )
        await root_profile.close()
    except BaseError as e:
        raise UpgradeError(f"Error during upgrade: {e}")


async def update_existing_records(profile: Profile):
    """
    Update existing records.

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


# Update every release
CONFIG_v7_3 = {
    "v0.7.2": {
        "update_existing_function_inst": update_existing_records,
    },
}


main()
