"""Wallet configuration."""

import logging
from typing import Tuple

from ..core.error import ProfileNotFoundError, StartupError
from ..core.profile import Profile, ProfileManager, ProfileSession
from ..storage.base import BaseStorage
from ..storage.error import StorageNotFoundError
from ..version import RECORD_TYPE_ACAPY_VERSION, __version__
from ..wallet.base import BaseWallet
from ..wallet.crypto import seed_to_did
from ..wallet.did_info import DIDInfo
from ..wallet.did_method import SOV
from ..wallet.key_type import ED25519
from .base import ConfigError
from .injection_context import InjectionContext

LOGGER = logging.getLogger(__name__)

CFG_MAP = {
    "key",
    "key_derivation_method",
    "rekey",
    "name",
    "storage_config",
    "storage_creds",
    "storage_type",
    "test",
}


def _create_config_with_settings(settings) -> dict:
    profile_config = {}

    for k in CFG_MAP:
        pk = f"wallet.{k}"
        if pk in settings:
            profile_config[k] = settings[pk]

    # may be set by `aca-py provision --recreate`
    if settings.get("wallet.recreate"):
        profile_config["auto_recreate"] = True

    return profile_config


async def _attempt_open_profile(
    profile_manager: ProfileManager,
    context: InjectionContext,
    profile_config: dict,
    settings: dict,
) -> Tuple[Profile, bool]:
    provision = False
    try:
        profile = await profile_manager.open(context, profile_config)
    except ProfileNotFoundError:
        if settings.get("auto_provision", False):
            profile = await profile_manager.provision(context, profile_config)
            provision = True
        else:
            error_msg = (
                "Profile not found. Use `aca-py start --auto-provision` to create."
            )
            LOGGER.error(error_msg)
            raise StartupError(error_msg)

    return (profile, provision)


async def _replace_public_did_if_seed_mismatch(
    public_did_info: DIDInfo,
    wallet: BaseWallet,
    settings: dict,
    wallet_seed: str,
) -> DIDInfo:
    """Replace the public DID if a seed is provided and doesn't match the current DID.

    Args:
        public_did_info: Current public DID info
        wallet: Wallet instance
        settings: Configuration settings
        wallet_seed: Optional seed to check against current DID

    Returns:
        DIDInfo: Either the original DID info or a new one if replaced
    """
    if not wallet_seed:
        return public_did_info

    public_did = public_did_info.did
    if seed_to_did(wallet_seed) == public_did:
        return public_did_info

    if not settings.get("wallet.replace_public_did"):
        raise ConfigError(
            "New seed provided which doesn't match the registered "
            f"public did {public_did}"
        )

    LOGGER.info(
        "Replacing public DID which doesn't match the seed "
        "(as configured by --replace-public-did)"
    )
    replace_did_info = await wallet.create_local_did(
        method=SOV, key_type=ED25519, seed=wallet_seed
    )
    await wallet.set_public_did(replace_did_info.did)
    LOGGER.info(
        "Created new public DID: %s, with verkey: %s",
        replace_did_info.did,
        replace_did_info.verkey,
    )
    return replace_did_info


async def _initialize_with_debug_settings(settings: dict, wallet: BaseWallet):
    test_seed = settings.get("debug.seed")
    if settings.get("debug.enabled") and not test_seed:
        test_seed = "testseed000000000000000000000001"
    if test_seed:
        await wallet.create_local_did(
            method=SOV,
            key_type=ED25519,
            seed=test_seed,
            metadata={"endpoint": "1.2.3.4:8021"},
        )


async def _initialize_with_seed(
    settings: dict, wallet: BaseWallet, create_local_did: bool, seed: str
) -> DIDInfo:
    if create_local_did:
        endpoint = settings.get("default_endpoint")
        metadata = {"endpoint": endpoint} if endpoint else None

        did_info = await wallet.create_local_did(
            method=SOV,
            key_type=ED25519,
            seed=seed,
            metadata=metadata,
        )
    else:
        did_info = await wallet.create_public_did(method=SOV, key_type=ED25519, seed=seed)

    LOGGER.info(
        "Created new %s DID: %s, Verkey: %s",
        "local" if create_local_did else "public",
        did_info.did,
        did_info.verkey,
    )
    return did_info


async def wallet_config(
    context: InjectionContext, provision: bool = False
) -> Tuple[Profile, DIDInfo]:
    """Initialize the root profile."""

    profile_manager = context.inject(ProfileManager)

    settings = context.settings
    profile_config = _create_config_with_settings(settings)
    wallet_seed = settings.get("wallet.seed")
    create_local_did = settings.get("wallet.local_did")

    if provision:
        profile = await profile_manager.provision(context, profile_config)
    else:
        profile, provision = await _attempt_open_profile(
            profile_manager, context, profile_config, settings
        )

    LOGGER.info(
        "%s Profile name: %s, backend: %s",
        "Created new profile -" if profile.created else "Opened existing profile -",
        profile.name,
        profile.backend,
    )

    txn = await profile.transaction()
    wallet = txn.inject(BaseWallet)
    public_did_info = await wallet.get_public_did()

    if public_did_info:
        # Check if we need to replace the public DID due to seed mismatch
        public_did_info = await _replace_public_did_if_seed_mismatch(
            public_did_info, wallet, settings, wallet_seed
        )
    elif wallet_seed:
        # Create new public DID from seed if none exists
        public_did_info = await _initialize_with_seed(
            settings, wallet, create_local_did, wallet_seed
        )

    public_did = public_did_info.did if public_did_info else None
    if provision and not create_local_did and not public_did:
        LOGGER.info("No public DID created")

    await _initialize_with_debug_settings(settings, wallet)

    await txn.commit()

    return (profile, public_did_info)


async def add_or_update_version_to_storage(session: ProfileSession):
    """Add or update ACA-Py version StorageRecord."""
    storage: BaseStorage = session.inject(BaseStorage)
    try:
        record = await storage.find_record(RECORD_TYPE_ACAPY_VERSION, {})
        await storage.update_record(record, f"v{__version__}", {})
    except StorageNotFoundError:
        raise ConfigError(
            (
                "No wallet storage version found, Run aca-py "
                "upgrade command with --from-version argument "
                "to fix this."
            )
        )
