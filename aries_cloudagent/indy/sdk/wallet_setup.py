"""Indy-SDK wallet setup and configuration."""

import json
import logging

from typing import Any, Mapping

import indy.anoncreds
import indy.did
import indy.crypto
import indy.wallet

from indy.error import IndyError, ErrorCode

from ...core.error import ProfileError, ProfileNotFoundError
from ...core.profile import Profile

from .error import IndyErrorHandler
from .wallet_plugin import load_postgres_plugin

LOGGER = logging.getLogger(__name__)


class IndyWalletConfig:
    DEFAULT_FRESHNESS = 0
    DEFAULT_KEY = ""
    DEFAULT_KEY_DERIVATION = "ARGON2I_MOD"
    DEFAULT_STORAGE_TYPE = None

    KEY_DERIVATION_RAW = "RAW"
    KEY_DERIVATION_ARGON2I_INT = "ARGON2I_INT"
    KEY_DERIVATION_ARGON2I_MOD = "ARGON2I_MOD"

    def __init__(self, config: Mapping[str, Any] = None):
        """Initialize an `IndySdkWalletConfig` instance.

        Args:
            config: {name, key, seed, did, auto-create, auto-remove,
                     storage_type, storage_config, storage_creds}

        """

        config = config or {}
        # self.auto_create = config.get("auto_create", True)
        self.auto_remove = config.get("auto_remove", False)
        self.freshness_time = config.get("freshness_time", False)
        self.key = config.get("key") or self.DEFAULT_KEY
        self.key_derivation_method = (
            config.get("key_derivation_method") or self.DEFAULT_KEY_DERIVATION
        )
        # self.rekey = config.get("rekey")
        # self.rekey_derivation_method = config.get("key_derivation_method")
        self.name = config.get("name") or Profile.DEFAULT_NAME
        self.storage_type = config.get("storage_type") or self.DEFAULT_STORAGE_TYPE
        self.storage_config = config.get("storage_config", None)
        self.storage_creds = config.get("storage_creds", None)

        if self.storage_type == "postgres_storage":
            load_postgres_plugin(self.storage_config, self.storage_creds)

    @property
    def wallet_config(self) -> dict:
        """Accessor for the Indy wallet config."""
        ret = {
            "id": self.name,
            "freshness_time": self.freshness_time,
            "storage_type": self.storage_type,
        }
        if self.storage_config is not None:
            ret["storage_config"] = json.loads(self.storage_config)
        return ret

    @property
    def wallet_access(self) -> dict:
        """Accessor the Indy wallet access info."""
        ret = {"key": self.key, "key_derivation_method": self.key_derivation_method}
        # if self.rekey:
        #     ret["rekey"] = self.rekey
        # if self.rekey_derivation_method:
        #     ret["rekey_derivation_method"] = self.rekey_derivation_method
        if self.storage_creds is not None:
            ret["storage_credentials"] = json.loads(self.storage_creds)
        return ret

    async def create_wallet(self) -> "IndyOpenWallet":
        """
        Create a new wallet.

        Raises:
            ProfileError: If there was a problem removing the wallet
            ProfileError: IF there was a libindy error

        """
        if self.auto_remove:
            try:
                await self.remove_wallet()
            except ProfileNotFoundError:
                pass
        try:
            await indy.wallet.create_wallet(
                config=json.dumps(self.wallet_config),
                credentials=json.dumps(self.wallet_access),
            )
        except IndyError as x_indy:
            raise IndyErrorHandler.wrap_error(
                x_indy,
                "Wallet was not removed by SDK, {} may still be open".format(self.name)
                if x_indy.error_code == ErrorCode.WalletAlreadyExistsError
                else None,
                ProfileError,
            ) from x_indy

        try:
            return await self.open_wallet()
        except ProfileNotFoundError as err:
            raise ProfileError(f"Wallet {self.name} not found after creation") from err

    async def remove_wallet(self):
        """
        Remove an existing wallet.

        Raises:
            ProfileNotFoundError: If the wallet could not be found
            ProfileError: If there was an libindy error

        """
        try:
            await indy.wallet.delete_wallet(
                config=json.dumps(self.wallet_config),
                credentials=json.dumps(self.wallet_access),
            )
        except IndyError as x_indy:
            if x_indy.error_code == ErrorCode.WalletNotFoundError:
                raise IndyErrorHandler.wrap_error(
                    x_indy,
                    "Wallet {} not found".format(self.name),
                    ProfileNotFoundError,
                ) from x_indy
            raise IndyErrorHandler.wrap_error(
                x_indy, "Wallet error", ProfileError
            ) from x_indy

    async def open_wallet(self) -> "IndyOpenWallet":
        """
        Open wallet, removing and/or creating it if so configured.

        Raises:
            ProfileError: If wallet not found after creation
            ProfileNotFoundError: If the wallet is not found
            ProfileError: If the wallet is already open
            ProfileError: If there is a libindy error

        """
        handle = None

        while True:
            try:
                handle = await indy.wallet.open_wallet(
                    config=json.dumps(self.wallet_config),
                    credentials=json.dumps(self.wallet_access),
                )
                # if self.rekey:
                #     self.key = self.rekey
                #     self.rekey = None
                # if self.rekey_derivation_method:
                #     self.key_derivation_method = self.rekey_derivation_method
                #     self.rekey_derivation_method = None
                break
            except IndyError as x_indy:
                if x_indy.error_code == ErrorCode.WalletNotFoundError:
                    raise ProfileNotFoundError("Wallet {} not found".format(self.name))
                elif x_indy.error_code == ErrorCode.WalletAlreadyOpenedError:
                    raise ProfileError("Wallet {} is already open".format(self.name))
                else:
                    raise IndyErrorHandler.wrap_error(
                        x_indy, "Wallet {} error".format(self.name), ProfileError
                    ) from x_indy

        LOGGER.info("Creating master secret...")
        try:
            master_secret_id = await indy.anoncreds.prover_create_master_secret(
                handle, self.name
            )
        except IndyError as x_indy:
            if x_indy.error_code == ErrorCode.AnoncredsMasterSecretDuplicateNameError:
                LOGGER.info("Master secret already exists")
                master_secret_id = self.name
            else:
                raise IndyErrorHandler.wrap_error(
                    x_indy, "Wallet {} error".format(self.name), ProfileError
                ) from x_indy

        return IndyOpenWallet(self, handle, self.name, master_secret_id)


class IndyOpenWallet:
    """Handle and metadata for an opened Indy wallet."""

    def __init__(
        self,
        config: IndyWalletConfig,
        handle,
        name: str,
        master_secret_id: str,
    ):
        """Create a new IndyOpenWallet instance."""
        self.config = config
        self.handle = handle
        self.name = name
        self.master_secret_id = master_secret_id

    async def close(self):
        """Close previously-opened wallet, removing it if so configured."""
        if self.handle:
            await indy.wallet.close_wallet(self.handle)
            self.handle = None
            if self.config.auto_remove:
                await self.config.remove_wallet()
