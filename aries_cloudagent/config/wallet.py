"""Wallet configuration."""

import logging

from ..wallet.base import BaseWallet
from ..wallet.crypto import seed_to_did

from .base import ConfigError
from .injection_context import InjectionContext

LOGGER = logging.getLogger(__name__)


async def wallet_config(context: InjectionContext, provision: bool = False):
    """Initialize the wallet."""
    wallet: BaseWallet = context.inject(BaseWallet)
    if provision:
        if wallet.type != "indy":
            raise ConfigError("Cannot provision a non-Indy wallet type")
        if wallet.created:
            print("Created new wallet")
        else:
            print("Opened existing wallet")
        print("Wallet type:", wallet.type)
        print("Wallet name:", wallet.name)

    wallet_seed = context.settings.get("wallet.seed")
    wallet_local_did = context.settings.get("wallet.local_did")
    public_did_info = await wallet.get_public_did()
    public_did = None

    if public_did_info:
        public_did = public_did_info.did
        if wallet_seed and seed_to_did(wallet_seed) != public_did:
            if context.settings.get("wallet.replace_public_did"):
                replace_did_info = await wallet.create_local_did(wallet_seed)
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
                seed=wallet_seed, metadata=metadata
            )
            local_did = local_did_info.did
            if provision:
                print(f"Created new local DID: {local_did}")
                print(f"Verkey: {local_did_info.verkey}")
        else:
            public_did_info = await wallet.create_public_did(seed=wallet_seed)
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
            seed=test_seed, metadata={"endpoint": "1.2.3.4:8021"}
        )

    return public_did
