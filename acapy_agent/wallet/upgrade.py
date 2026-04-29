"""Functions for upgrading records to anoncreds."""

import asyncio
import logging

from acapy_agent.cache.base import BaseCache
from acapy_agent.core.profile import Profile
from acapy_agent.multitenant.base import BaseMultitenantManager
from acapy_agent.storage.base import BaseStorage
from acapy_agent.storage.error import StorageNotFoundError
from acapy_agent.storage.record import StorageRecord
from acapy_agent.storage.type import (
    RECORD_TYPE_ACAPY_STORAGE_TYPE,
    RECORD_TYPE_ACAPY_UPGRADING,
    STORAGE_TYPE_VALUE_ANONCREDS,
    STORAGE_TYPE_VALUE_KANON_ANONCREDS,
)
from acapy_agent.wallet.singletons import IsAnonCredsSingleton, UpgradeInProgressSingleton

LOGGER = logging.getLogger(__name__)


UPGRADING_RECORD_IN_PROGRESS = "anoncreds_in_progress"
UPGRADING_RECORD_FINISHED = "anoncreds_finished"


async def finish_upgrading_record(profile: Profile):
    """Update upgrading record to finished."""
    async with profile.session() as session:
        storage = session.inject(BaseStorage)
        try:
            upgrading_record = await storage.find_record(
                RECORD_TYPE_ACAPY_UPGRADING, tag_query={}
            )
            await storage.update_record(upgrading_record, UPGRADING_RECORD_FINISHED, {})
        except StorageNotFoundError:
            return


async def finish_upgrade(profile: Profile):
    """Finish record by setting records and caches."""
    async with profile.session() as session:
        storage = session.inject(BaseStorage)
        try:
            storage_type_record = await storage.find_record(
                type_filter=RECORD_TYPE_ACAPY_STORAGE_TYPE, tag_query={}
            )

            if storage_type_record.value == STORAGE_TYPE_VALUE_KANON_ANONCREDS:
                await storage.update_record(
                    storage_type_record, STORAGE_TYPE_VALUE_KANON_ANONCREDS, {}
                )
            else:
                await storage.update_record(
                    storage_type_record, STORAGE_TYPE_VALUE_ANONCREDS, {}
                )

        # This should only happen for subwallets
        except StorageNotFoundError:
            # Check if this is a Kanon-based profile to determine storage type
            if hasattr(profile, "backend") and "kanon" in profile.backend.lower():
                await storage.add_record(
                    StorageRecord(
                        RECORD_TYPE_ACAPY_STORAGE_TYPE,
                        STORAGE_TYPE_VALUE_KANON_ANONCREDS,
                    )
                )
            else:
                await storage.add_record(
                    StorageRecord(
                        RECORD_TYPE_ACAPY_STORAGE_TYPE,
                        STORAGE_TYPE_VALUE_ANONCREDS,
                    )
                )

    await finish_upgrading_record(profile)
    IsAnonCredsSingleton().set_wallet(profile.name)
    UpgradeInProgressSingleton().remove_wallet(profile.name)


async def upgrade_subwallet(profile: Profile) -> None:
    """Upgrade subwallet to anoncreds."""
    async with profile.session() as session:
        multitenant_mgr = session.inject_or(BaseMultitenantManager)
        wallet_id = profile.settings.get("wallet.id")
        cache = profile.inject_or(BaseCache)
        await cache.flush()
        settings = {"wallet.type": STORAGE_TYPE_VALUE_ANONCREDS}
        await multitenant_mgr.update_wallet(wallet_id, settings)


async def check_upgrade_completion_loop(profile: Profile, is_subwallet=False):
    """Check if upgrading is complete."""
    async with profile.session() as session:
        while True:
            storage = session.inject(BaseStorage)
            LOGGER.debug("Checking upgrade completion for wallet: %s", profile.name)
            try:
                upgrading_record = await storage.find_record(
                    RECORD_TYPE_ACAPY_UPGRADING, tag_query={}
                )
                if upgrading_record.value == UPGRADING_RECORD_FINISHED:
                    IsAnonCredsSingleton().set_wallet(profile.name)
                    UpgradeInProgressSingleton().remove_wallet(profile.name)
                    if is_subwallet:
                        await upgrade_subwallet(profile)
                        await finish_upgrade(profile)
                        LOGGER.info(
                            "Upgrade of subwallet %s has completed. "
                            "Profile is now askar-anoncreds",
                            profile.settings.get("wallet.name"),
                        )
                        return
                    LOGGER.info(
                        "Upgrade complete for wallet: %s, shutting down agent.",
                        profile.name,
                    )
                    # Shut down agent if base wallet
                    asyncio.get_event_loop().stop()
            except StorageNotFoundError:
                # If the record is not found, the upgrade failed
                return

            await asyncio.sleep(1)
