"""Wallet configuration."""

import logging
import json

from typing import Tuple, Mapping, Any

from ..core.error import ProfileNotFoundError
from ..core.profile import Profile, ProfileManager, ProfileSession
from ..ledger.base import BaseLedger
from ..storage.base import BaseStorage, StorageRecord
from ..storage.error import (
    StorageNotFoundError,
    StorageDuplicateError,
    StorageError,
)
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
}


def is_multi_ledger(settings: Mapping[str, Any]) -> bool:
    """Check whether mutli-ledger mode is enabled."""
    if (
        settings.get_value("ledger.ledger_config_list")
        and len(settings.get_value("ledger.ledger_config_list")) >= 1
    ):
        return True
    return False


async def update_public_did_ledger_id_map(
    session,
    info: DIDInfo,
    config: dict,
):
    """Add or update acapy_ledger_public_did_map storage record."""
    _curr_write_ledger = session.inject_or(BaseLedger)
    storage = session.inject_or(BaseStorage)
    ledger_id = config.get("ledger_pool_name") or _curr_write_ledger.pool_name
    record_type_ledger_did_map = (
        config.get("record_type_name") or "acapy_ledger_public_did_map"
    )
    try:
        ledger_id_public_did_map_record: StorageRecord = await storage.find_record(
            type_filter=record_type_ledger_did_map, tag_query={}
        )
        ledger_id_public_did_map = json.loads(ledger_id_public_did_map_record.value)
        ledger_id_public_did_map[ledger_id] = {
            "did": info.did,
            "routing_keys": config.get("routing_keys"),
            "mediation_endpoint": config.get("mediator_endpoint"),
            "connection_id": config.get("connection_id"),
            "write_ledger": config.get("write_ledger"),
        }
        await storage.update_record(
            ledger_id_public_did_map_record,
            json.dumps(ledger_id_public_did_map),
            {},
        )
    except (StorageError, StorageNotFoundError, StorageDuplicateError):
        ledger_id_public_did_map = {
            ledger_id: {
                "did": info.did,
                "routing_keys": config.get("routing_keys"),
                "mediation_endpoint": config.get("mediator_endpoint"),
                "connection_id": config.get("connection_id"),
                "write_ledger": config.get("write_ledger"),
            }
        }
        record = StorageRecord(
            record_type_ledger_did_map,
            json.dumps(ledger_id_public_did_map),
            {},
        )
        await storage.add_record(record)


async def wallet_config(
    context: InjectionContext, provision: bool = False
) -> Tuple[Profile, DIDInfo]:
    """Initialize the root profile."""

    mgr = context.inject(ProfileManager)

    settings = context.settings
    profile_cfg = {}
    for k in CFG_MAP:
        pk = f"wallet.{k}"
        if pk in settings:
            profile_cfg[k] = settings[pk]

    # may be set by `aca-py provision --recreate`
    if settings.get("wallet.recreate"):
        profile_cfg["auto_recreate"] = True

    if provision:
        profile = await mgr.provision(context, profile_cfg)
    else:
        try:
            profile = await mgr.open(context, profile_cfg)
        except ProfileNotFoundError:
            if settings.get("auto_provision", False):
                profile = await mgr.provision(context, profile_cfg)
            else:
                raise

    if provision:
        if profile.created:
            print("Created new profile")
        else:
            print("Opened existing profile")
        print("Profile backend:", profile.backend)
        print("Profile name:", profile.name)

    wallet_seed = context.settings.get("wallet.seed")
    wallet_local_did = context.settings.get("wallet.local_did")
    txn = await profile.transaction()
    wallet = txn.inject(BaseWallet)

    public_did_info = await wallet.get_public_did()
    public_did = None

    if public_did_info:
        public_did = public_did_info.did
        if wallet_seed and seed_to_did(wallet_seed) != public_did:
            if context.settings.get("wallet.replace_public_did"):
                replace_did_info = await wallet.create_local_did(
                    method=SOV, key_type=ED25519, seed=wallet_seed
                )
                public_did = replace_did_info.did
                await wallet.set_public_did(public_did)
                print(f"Created new public DID: {public_did}")
                print(f"Verkey: {replace_did_info.verkey}")
            else:
                # If we already have a registered public did and it doesn't match
                # the one derived from `wallet_seed` then we error out.
                raise ConfigError(
                    "New seed provided which doesn't match the registered"
                    + f" public did {public_did}"
                )
        # wait until ledger config to set public DID endpoint - wallet goes first
    elif wallet_seed:
        if wallet_local_did:
            endpoint = context.settings.get("default_endpoint")
            metadata = {"endpoint": endpoint} if endpoint else None

            local_did_info = await wallet.create_local_did(
                method=SOV,
                key_type=ED25519,
                seed=wallet_seed,
                metadata=metadata,
            )
            local_did = local_did_info.did
            if provision:
                print(f"Created new local DID: {local_did}")
                print(f"Verkey: {local_did_info.verkey}")
        else:
            public_did_info = await wallet.create_public_did(
                method=SOV,
                key_type=ED25519,
                seed=wallet_seed,
                context=context,
            )
            public_did = public_did_info.did
            if provision:
                print(f"Created new public DID: {public_did}")
                print(f"Verkey: {public_did_info.verkey}")
            # wait until ledger config to set public DID endpoint - wallet goes first

    if provision and not wallet_local_did and not public_did:
        print("No public DID")

    # Debug settings
    test_seed = context.settings.get("debug.seed")
    if context.settings.get("debug.enabled"):
        if not test_seed:
            test_seed = "testseed000000000000000000000001"
    if test_seed:
        await wallet.create_local_did(
            method=SOV,
            key_type=ED25519,
            seed=test_seed,
            metadata={"endpoint": "1.2.3.4:8021"},
        )

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
