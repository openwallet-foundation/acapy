"""Indy-SDK wallet setup and configuration."""

import json
import logging

from typing import Any, Mapping

import indy.anoncreds
import indy.did
import indy.crypto
import indy.wallet

from indy.error import IndyError, ErrorCode

from ...core.error import ProfileError, ProfileDuplicateError, ProfileNotFoundError
from ...core.profile import Profile

from .error import IndyErrorHandler
from .wallet_plugin import load_postgres_plugin

LOGGER = logging.getLogger(__name__)


class IndyWalletConfig:
    """A helper class for handling Indy-SDK wallet configuration."""

    DEFAULT_FRESHNESS = False
    DEFAULT_KEY = ""
    DEFAULT_KEY_DERIVATION = "ARGON2I_MOD"
    DEFAULT_STORAGE_TYPE = None

    KEY_DERIVATION_RAW = "RAW"
    KEY_DERIVATION_ARGON2I_INT = "ARGON2I_INT"
    KEY_DERIVATION_ARGON2I_MOD = "ARGON2I_MOD"

    def __init__(self, config: Mapping[str, Any] = None):
        """Initialize an `IndySdkWalletConfig` instance.

        Args:
            config: {name, key, seed, did, auto_recreate, auto_remove,
                     storage_type, storage_config, storage_creds}

        """

        config = config or {}
        self.auto_recreate = config.get("auto_recreate", False)
        self.auto_remove = config.get("auto_remove", False)
        self.freshness_time = config.get("freshness_time", self.DEFAULT_FRESHNESS)
        self.key = config.get("key", self.DEFAULT_KEY)
        self.key_derivation_method = (
            config.get("key_derivation_method") or self.DEFAULT_KEY_DERIVATION
        )
        # self.rekey = config.get("rekey")
        # self.rekey_derivation_method = config.get("rekey_derivation_method")
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
            ProfileDuplicateError: If there was an existing wallet with the same name
            ProfileError: If there was a problem removing the wallet
            ProfileError: If there was another libindy error

        """
        if self.auto_recreate:
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
            if x_indy.error_code == ErrorCode.WalletAlreadyExistsError:
                raise IndyErrorHandler.wrap_error(
                    x_indy,
                    f"Cannot create wallet '{self.name}', already exists",
                    ProfileDuplicateError,
                ) from x_indy
            raise IndyErrorHandler.wrap_error(
                x_indy,
                f"Error creating wallet '{self.name}'",
                ProfileError,
            ) from x_indy

        try:
            return await self.open_wallet(created=True)
        except ProfileNotFoundError as err:
            raise ProfileError(
                f"Wallet '{self.name}' not found after creation"
            ) from err

    async def remove_wallet(self):
        """
        Remove an existing wallet.

        Raises:
            ProfileNotFoundError: If the wallet could not be found
            ProfileError: If there was another libindy error

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
                    f"Wallet '{self.name}' not found",
                    ProfileNotFoundError,
                ) from x_indy
            raise IndyErrorHandler.wrap_error(
                x_indy, f"Error removing wallet '{self.name}'", ProfileError
            ) from x_indy

    async def open_wallet(self, created: bool = False) -> "IndyOpenWallet":
        """
        Open wallet, removing and/or creating it if so configured.

        Raises:
            ProfileError: If wallet not found after creation
            ProfileNotFoundError: If the wallet is not found
            ProfileError: If the wallet is already open
            ProfileError: If there is another libindy error

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
                    raise IndyErrorHandler.wrap_error(
                        x_indy, f"Wallet '{self.name}' not found", ProfileNotFoundError
                    ) from x_indy
                elif x_indy.error_code == ErrorCode.WalletAlreadyOpenedError:
                    raise IndyErrorHandler.wrap_error(
                        x_indy, f"Wallet '{self.name}' is already open", ProfileError
                    ) from x_indy
                else:
                    raise IndyErrorHandler.wrap_error(
                        x_indy, f"Error opening wallet '{self.name}'", ProfileError
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
                    x_indy, f"Wallet '{self.name}' error", ProfileError
                ) from x_indy

        return IndyOpenWallet(self, created, handle, master_secret_id)


class IndyOpenWallet:
    """Handle and metadata for an opened Indy wallet."""

    def __init__(
        self,
        config: IndyWalletConfig,
        created,
        handle,
        master_secret_id: str,
    ):
        """Create a new IndyOpenWallet instance."""
        self.config = config
        self.created = created
        self.handle = handle
        self.master_secret_id = master_secret_id

    @property
    def name(self) -> str:
        """Accessor for the opened wallet name."""
        return self.config.name

    async def close(self):
        """Close previously-opened wallet, removing it if so configured."""
        if self.handle:
            await indy.wallet.close_wallet(self.handle)
            self.handle = None
            if self.config.auto_remove:
                await self.config.remove_wallet()
