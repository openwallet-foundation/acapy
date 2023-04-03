"""Upgrade command for handling breaking changes when updating ACA-PY versions."""

import asyncio
import logging
import os
import yaml

from configargparse import ArgumentParser
from packaging import version as package_version
from typing import (
    Callable,
    Sequence,
    Optional,
    List,
    Union,
    Mapping,
    Any,
)

from ..core.profile import Profile
from ..config import argparse as arg
from ..config.default_context import DefaultContextBuilder
from ..config.base import BaseError, BaseSettings
from ..config.util import common_config
from ..config.wallet import wallet_config
from ..messaging.models.base_record import BaseRecord
from ..storage.base import BaseStorage
from ..storage.error import StorageNotFoundError
from ..storage.record import StorageRecord
from ..utils.classloader import ClassLoader, ClassNotFoundError
from ..version import __version__, RECORD_TYPE_ACAPY_VERSION

from . import PROG

DEFAULT_UPGRADE_CONFIG_FILE_NAME = "default_version_upgrade_config.yml"
LOGGER = logging.getLogger(__name__)


class UpgradeError(BaseError):
    """Base exception for upgrade related errors."""


class VersionUpgradeConfig:
    """Handle ACA-Py version upgrade config."""

    def __init__(self, config_path: str = None):
        """Initialize config for use during upgrade process."""
        self.function_map_config = UPGRADE_EXISTING_RECORDS_FUNCTION_MAPPING
        self.upgrade_configs = {}
        if config_path:
            self.setup_version_upgrade_config(config_path)
        else:
            self.setup_version_upgrade_config(
                os.path.join(
                    os.path.dirname(os.path.realpath(__file__)),
                    DEFAULT_UPGRADE_CONFIG_FILE_NAME,
                )
            )

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
                config_key_set = set(provided_config.keys())
                try:
                    config_key_set.remove("resave_records")
                except KeyError:
                    pass
                for executable in config_key_set:
                    version_config_dict[version][executable] = (
                        provided_config.get(executable) or False
                    )
            if version_config_dict == {}:
                raise UpgradeError(f"No version configs found in {path}")
            self.upgrade_configs = version_config_dict

    def get_callable(self, executable: str) -> Optional[Callable]:
        """Return callable function for executable name."""
        if executable in self.function_map_config:
            return self.function_map_config.get(executable)
        else:
            return None


def init_argument_parser(parser: ArgumentParser):
    """Initialize an argument parser with the module's arguments."""
    return arg.load_argument_groups(parser, *arg.group.get_registered(arg.CAT_UPGRADE))


def get_upgrade_version_list(
    from_version: str,
    sorted_version_list: Optional[List] = None,
    config_path: Optional[str] = None,
) -> List:
    """Get available versions from the upgrade config."""
    if not sorted_version_list:
        version_upgrade_config_inst = VersionUpgradeConfig(config_path)
        upgrade_configs = version_upgrade_config_inst.upgrade_configs
        versions_found_in_config = upgrade_configs.keys()
        sorted_version_list = sorted(
            versions_found_in_config, key=lambda x: package_version.parse(x)
        )

    version_list = []
    for version in sorted_version_list:
        if package_version.parse(version) >= package_version.parse(from_version):
            version_list.append(version)
    return version_list


async def add_version_record(profile: Profile, version: str):
    """Add an acapy_version storage record for provided version."""
    async with profile.session() as session:
        storage = session.inject(BaseStorage)
        try:
            version_storage_record = await storage.find_record(
                type_filter=RECORD_TYPE_ACAPY_VERSION, tag_query={}
            )
        except StorageNotFoundError:
            version_storage_record = None
        if not version_storage_record:
            await storage.add_record(
                StorageRecord(
                    RECORD_TYPE_ACAPY_VERSION,
                    version,
                )
            )
        else:
            await storage.update_record(version_storage_record, version, {})
    LOGGER.info(f"{RECORD_TYPE_ACAPY_VERSION} storage record set to {version}")


async def upgrade(
    settings: Optional[Union[Mapping[str, Any], BaseSettings]] = None,
    profile: Optional[Profile] = None,
):
    """Perform upgradation steps."""
    try:
        if profile and (settings or settings == {}):
            raise UpgradeError("upgrade requires either profile or settings, not both.")
        if profile:
            root_profile = profile
            settings = profile.settings
        else:
            context_builder = DefaultContextBuilder(settings)
            context = await context_builder.build_context()
            root_profile, _ = await wallet_config(context)
        version_upgrade_config_inst = VersionUpgradeConfig(
            settings.get("upgrade.config_path")
        )
        upgrade_configs = version_upgrade_config_inst.upgrade_configs
        upgrade_to_version = f"v{__version__}"
        versions_found_in_config = upgrade_configs.keys()
        sorted_versions_found_in_config = sorted(
            versions_found_in_config, key=lambda x: package_version.parse(x)
        )
        upgrade_from_version_storage = None
        upgrade_from_version_config = None
        upgrade_from_version = None
        async with root_profile.session() as session:
            storage = session.inject(BaseStorage)
            try:
                version_storage_record = await storage.find_record(
                    type_filter=RECORD_TYPE_ACAPY_VERSION, tag_query={}
                )
                upgrade_from_version_storage = version_storage_record.value
            except StorageNotFoundError:
                LOGGER.info("No ACA-Py version found in wallet storage.")
                version_storage_record = None

            if "upgrade.from_version" in settings:
                upgrade_from_version_config = settings.get("upgrade.from_version")
                LOGGER.info(
                    (
                        f"Selecting {upgrade_from_version_config} as "
                        "--from-version from the config."
                    )
                )

        force_upgrade_flag = settings.get("upgrade.force_upgrade") or False
        if upgrade_from_version_storage and upgrade_from_version_config:
            if (
                package_version.parse(upgrade_from_version_storage)
                > package_version.parse(upgrade_from_version_config)
            ) and force_upgrade_flag:
                upgrade_from_version = upgrade_from_version_config
            else:
                upgrade_from_version = upgrade_from_version_storage
        if (
            not upgrade_from_version
            and not upgrade_from_version_storage
            and upgrade_from_version_config
        ):
            upgrade_from_version = upgrade_from_version_config
        if (
            not upgrade_from_version
            and upgrade_from_version_storage
            and not upgrade_from_version_config
        ):
            upgrade_from_version = upgrade_from_version_storage
        if not upgrade_from_version:
            raise UpgradeError(
                "No upgrade from version found in wallet or settings [--from-version]"
            )
        upgrade_version_in_config = get_upgrade_version_list(
            sorted_version_list=sorted_versions_found_in_config,
            from_version=upgrade_from_version,
        )
        to_update_flag = False
        if upgrade_from_version == upgrade_to_version:
            LOGGER.info(
                (
                    f"Version {upgrade_from_version} to upgrade from and "
                    f"current version to upgrade to {upgrade_to_version} "
                    "are same. You can apply upgrade from a lower "
                    "version by running the upgrade command with "
                    f"--from-version [< {upgrade_to_version}] and "
                    "--force-upgrade"
                )
            )
        else:
            resave_record_path_sets = set()
            executables_call_set = set()
            for config_from_version in upgrade_version_in_config:
                LOGGER.info(f"Running upgrade process for {config_from_version}")
                upgrade_config = upgrade_configs.get(config_from_version)
                # Step 1 re-saving all BaseRecord and BaseExchangeRecord
                if "resave_records" in upgrade_config:
                    resave_record_paths = upgrade_config.get("resave_records")
                    for record_path in resave_record_paths:
                        resave_record_path_sets.add(record_path)

                # Step 2 Update existing records, if required
                config_key_set = set(upgrade_config.keys())
                try:
                    config_key_set.remove("resave_records")
                except KeyError:
                    pass
                for callable_name in list(config_key_set):
                    if upgrade_config.get(callable_name) is False:
                        continue
                    executables_call_set.add(callable_name)

            if len(resave_record_path_sets) >= 1 or len(executables_call_set) >= 1:
                to_update_flag = True
            for record_path in resave_record_path_sets:
                try:
                    rec_type = ClassLoader.load_class(record_path)
                except ClassNotFoundError as err:
                    raise UpgradeError(f"Unknown Record type {record_path}") from err
                if not issubclass(rec_type, BaseRecord):
                    raise UpgradeError(
                        f"Only BaseRecord can be resaved, found: {str(rec_type)}"
                    )
                async with root_profile.session() as session:
                    all_records = await rec_type.query(session)
                    for record in all_records:
                        await record.save(
                            session,
                            reason="re-saving record during the upgrade process",
                        )
                    if len(all_records) == 0:
                        LOGGER.info(f"No records of {str(rec_type)} found")
                    else:
                        LOGGER.info(
                            f"All recs of {str(rec_type)} successfully re-saved"
                        )
            for callable_name in executables_call_set:
                _callable = version_upgrade_config_inst.get_callable(callable_name)
                if not _callable:
                    raise UpgradeError(f"No function specified for {callable_name}")
                await _callable(root_profile)

        # Update storage version
        if to_update_flag:
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
                LOGGER.info(
                    f"{RECORD_TYPE_ACAPY_VERSION} storage record "
                    f"set to {upgrade_to_version}"
                )
        if not profile:
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
    loop.run_until_complete(upgrade(settings=settings))


def main():
    """Execute the main line."""
    if __name__ == "__main__":
        execute()


UPGRADE_EXISTING_RECORDS_FUNCTION_MAPPING = {
    "update_existing_records": update_existing_records
}

main()
