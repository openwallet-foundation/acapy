"""Upgrade command for handling breaking changes when updating ACA-PY versions."""

import asyncio
import logging
import os
import json
import yaml

from configargparse import ArgumentParser
from enum import Enum
from packaging import version as package_version
from typing import (
    Callable,
    Sequence,
    Optional,
    List,
    Union,
    Mapping,
    Any,
    Tuple,
)

from ..core.profile import Profile, ProfileSession
from ..config import argparse as arg
from ..config.default_context import DefaultContextBuilder
from ..config.base import BaseError, BaseSettings
from ..config.util import common_config
from ..config.wallet import wallet_config
from ..messaging.models.base import BaseModelError
from ..messaging.models.base_record import BaseRecord, RecordType
from ..storage.base import BaseStorage
from ..storage.error import StorageNotFoundError
from ..storage.record import StorageRecord
from ..revocation.models.issuer_rev_reg_record import IssuerRevRegRecord
from ..utils.classloader import ClassLoader, ClassNotFoundError
from ..version import __version__, RECORD_TYPE_ACAPY_VERSION

from . import PROG

DEFAULT_UPGRADE_CONFIG_FILE_NAME = "default_version_upgrade_config.yml"
LOGGER = logging.getLogger(__name__)


class ExplicitUpgradeOption(Enum):
    """Supported explicit upgrade codes."""

    ERROR_AND_STOP = "critical"
    LOG_AND_PROCEED = "warning"

    @classmethod
    def get(cls, code: str) -> "ExplicitUpgradeOption":
        """Get ExplicitUpgradeOption for code."""
        for option in ExplicitUpgradeOption:
            if code == option.value:
                return option
        return None


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
            tagged_config_dict = {}
            for config_id, provided_config in config_dict.items():
                recs_list = []
                tagged_config_dict[config_id] = {}
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
                tagged_config_dict[config_id]["resave_records"] = recs_list
                config_key_set = set(provided_config.keys())
                try:
                    config_key_set.remove("resave_records")
                except KeyError:
                    pass
                if "explicit_upgrade" in provided_config:
                    tagged_config_dict[config_id][
                        "explicit_upgrade"
                    ] = provided_config.get("explicit_upgrade")
                try:
                    config_key_set.remove("explicit_upgrade")
                except KeyError:
                    pass
                for executable in config_key_set:
                    tagged_config_dict[config_id][executable] = (
                        provided_config.get(executable) or False
                    )
            if tagged_config_dict == {}:
                raise UpgradeError(f"No version configs found in {path}")
            self.upgrade_configs = tagged_config_dict

    def get_callable(self, executable: str) -> Optional[Callable]:
        """Return callable function for executable name."""
        if executable in self.function_map_config:
            return self.function_map_config.get(executable)
        else:
            return None


def init_argument_parser(parser: ArgumentParser):
    """Initialize an argument parser with the module's arguments."""
    return arg.load_argument_groups(parser, *arg.group.get_registered(arg.CAT_UPGRADE))


def explicit_upgrade_required_check(
    to_apply_version_list: List,
    upgrade_config: dict,
) -> Tuple[bool, List, Optional[str]]:
    """Check if explicit upgrade is required."""
    to_skip_versions = []
    for version in to_apply_version_list:
        if "explicit_upgrade" in upgrade_config.get(version):
            exp_upg_flag = upgrade_config.get(version).get("explicit_upgrade")
            if (
                ExplicitUpgradeOption.get(exp_upg_flag)
                is ExplicitUpgradeOption.ERROR_AND_STOP
            ):
                return True, [], version
            elif (
                ExplicitUpgradeOption.get(exp_upg_flag)
                is ExplicitUpgradeOption.LOG_AND_PROCEED
            ):
                to_skip_versions.append(version)
    return False, to_skip_versions, None


def get_upgrade_version_list(
    from_version: str,
    sorted_version_list: Optional[List] = None,
    config_path: Optional[str] = None,
) -> List:
    """Get available versions from the upgrade config."""
    if not sorted_version_list:
        version_upgrade_config_inst = VersionUpgradeConfig(config_path)
        upgrade_configs = version_upgrade_config_inst.upgrade_configs
        tags_found_in_config = upgrade_configs.keys()
        version_found_in_config, _ = _get_version_and_name_tags(
            list(tags_found_in_config)
        )
        sorted_version_list = sorted(
            version_found_in_config, key=lambda x: package_version.parse(x)
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


def _get_version_and_name_tags(tags_found_in_config: List) -> Tuple[List, List]:
    """Get version and named tag key lists from config."""
    version_found_in_config = []
    named_tag_found_in_config = []
    for tag in tags_found_in_config:
        try:
            package_version.parse(tag)
            version_found_in_config.append(tag)
        except package_version.InvalidVersion:
            named_tag_found_in_config.append(tag)
    return version_found_in_config, named_tag_found_in_config


def _perform_upgrade(
    upgrade_config: dict,
    resave_record_path_sets: set,
    executables_call_set: set,
    tag: str,
) -> Tuple[set, set]:
    """Update and return resave record path and executables call sets."""
    LOGGER.info(f"Running upgrade process for {tag}")
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
    return resave_record_path_sets, executables_call_set


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
        upgrade_from_tags = None
        force_upgrade_flag = settings.get("upgrade.force_upgrade") or False
        if force_upgrade_flag:
            upgrade_from_tags = settings.get("upgrade.named_tags")
        upgrade_configs = version_upgrade_config_inst.upgrade_configs
        upgrade_to_version = f"v{__version__}"
        tags_found_in_config = upgrade_configs.keys()
        version_found_in_config, named_tag_found_in_config = _get_version_and_name_tags(
            list(tags_found_in_config)
        )
        sorted_versions_found_in_config = sorted(
            version_found_in_config, key=lambda x: package_version.parse(x)
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
        if not upgrade_from_version and not upgrade_from_tags:
            raise UpgradeError(
                "No upgrade from version or tags found in wallet"
                " or settings [--from-version or --named-tag]"
            )
        resave_record_path_sets = set()
        executables_call_set = set()
        to_update_flag = False
        if upgrade_from_version:
            upgrade_version_in_config = get_upgrade_version_list(
                sorted_version_list=sorted_versions_found_in_config,
                from_version=upgrade_from_version,
            )
            # Perform explicit upgrade check if the function was called during startup
            if profile:
                (
                    explicit_flag,
                    to_skip_explicit_versions,
                    explicit_upg_ver,
                ) = explicit_upgrade_required_check(
                    to_apply_version_list=upgrade_version_in_config,
                    upgrade_config=upgrade_configs,
                )
                if explicit_flag:
                    raise UpgradeError(
                        "Explicit upgrade flag with critical value found "
                        f"for {explicit_upg_ver} config. Please use ACA-Py "
                        "upgrade command to complete the process and proceed."
                    )
                if len(to_skip_explicit_versions) >= 1:
                    LOGGER.warning(
                        "Explicit upgrade flag with warning value found "
                        f"for {str(to_skip_explicit_versions)} versions. "
                        "Proceeding with ACA-Py startup. You can apply "
                        "the explicit upgrades using the ACA-Py upgrade "
                        "command later."
                    )
                    return
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
                for config_from_version in upgrade_version_in_config:
                    resave_record_path_sets, executables_call_set = _perform_upgrade(
                        upgrade_config=upgrade_configs.get(config_from_version),
                        resave_record_path_sets=resave_record_path_sets,
                        executables_call_set=executables_call_set,
                        tag=config_from_version,
                    )
        if upgrade_from_tags and len(upgrade_from_tags) >= 1:
            for named_tag in upgrade_from_tags:
                if named_tag not in named_tag_found_in_config:
                    continue
                resave_record_path_sets, executables_call_set = _perform_upgrade(
                    upgrade_config=upgrade_configs.get(named_tag),
                    resave_record_path_sets=resave_record_path_sets,
                    executables_call_set=executables_call_set,
                    tag=named_tag,
                )
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
                    LOGGER.info(f"All recs of {str(rec_type)} successfully re-saved")
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


##########################################################
# Fix for ACA-Py Issue #2485
# issuance_type attribue in IssuerRevRegRecord was removed
# in 0.5.3 version. IssuerRevRegRecord created previously
# will need
##########################################################


async def find_affected_issue_rev_reg_records(
    session: ProfileSession,
) -> Sequence[RecordType]:
    """Get IssuerRevRegRecord records with issuance_type for re-saving.

    Args:
        session: The profile session to use
    """
    storage = session.inject(BaseStorage)
    rows = await storage.find_all_records(
        IssuerRevRegRecord.RECORD_TYPE,
    )
    issue_rev_reg_records_to_update = []
    for record in rows:
        vals = json.loads(record.value)
        to_update = False
        try:
            record_id = record.id
            record_id_name = IssuerRevRegRecord.RECORD_ID_NAME
            if record_id_name in vals:
                raise ValueError(f"Duplicate {record_id_name} inputs; {vals}")
            params = dict(**vals)
            # Check for issuance_type and add record_id for later tracking
            if "issuance_type" in params:
                LOGGER.info(
                    f"IssuerRevRegRecord {record_id} tagged for fixing issuance_type."
                )
                del params["issuance_type"]
                to_update = True
            params[record_id_name] = record_id
            if to_update:
                issue_rev_reg_records_to_update.append(IssuerRevRegRecord(**params))
        except BaseModelError as err:
            raise BaseModelError(f"{err}, for record id {record.id}")
    return issue_rev_reg_records_to_update


async def fix_issue_rev_reg_records(profile: Profile):
    """Update IssuerRevRegRecord records.

    Args:
        profile: Root profile

    """
    async with profile.session() as session:
        issue_rev_reg_records = await find_affected_issue_rev_reg_records(session)
        for record in issue_rev_reg_records:
            await record.save(
                session,
                reason="re-saving issue_rev_reg record without issuance type",
            )


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
    "update_existing_records": update_existing_records,
    "fix_issue_rev_reg_records": fix_issue_rev_reg_records,
}

main()
