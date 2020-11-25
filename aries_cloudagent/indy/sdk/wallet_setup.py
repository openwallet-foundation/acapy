"""Indy-SDK wallet setup and configuration."""

import json
import logging

import indy.anoncreds
import indy.did
import indy.crypto
import indy.wallet

from indy.error import IndyError, ErrorCode

from ...core.error import ProfileError, ProfileNotFoundError

from .error import IndyErrorHandler
from .wallet_plugin import load_postgres_plugin

LOGGER = logging.getLogger(__name__)


class IndyWalletManager:
    """Manage Indy wallet configuration."""

    DEFAULT_FRESHNESS = 0
    DEFAULT_KEY = ""
    DEFAULT_KEY_DERIVIATION = "ARGON2I_MOD"
    DEFAULT_NAME = "default"
    DEFAULT_STORAGE_TYPE = None

    KEY_DERIVATION_RAW = "RAW"
    KEY_DERIVATION_ARGON2I_INT = "ARGON2I_INT"
    KEY_DERIVATION_ARGON2I_MOD = "ARGON2I_MOD"

    def __init__(self, config: dict = None):
        """
        Initialize a `IndyWalletManager` instance.

        Args:
            config: {name, key, seed, did, auto-create, auto-remove,
                     storage_type, storage_config, storage_creds}

        """
        if not config:
            config = {}
        self._auto_create = config.get("auto_create", True)
        self._auto_remove = config.get("auto_remove", False)
        self._created = False
        self._freshness_time = config.get("freshness_time", False)
        self._instance: IndyOpenWallet = None
        self._key = config.get("key") or self.DEFAULT_KEY
        self._key_derivation_method = (
            config.get("key_derivation_method") or self.DEFAULT_KEY_DERIVIATION
        )
        self._rekey = config.get("rekey")
        self._rekey_derivation_method = config.get("key_derivation_method")
        self._name = config.get("name") or self.DEFAULT_NAME
        self._storage_type = config.get("storage_type") or self.DEFAULT_STORAGE_TYPE
        self._storage_config = config.get("storage_config", None)
        self._storage_creds = config.get("storage_creds", None)
        self._master_secret_id = None

        if self._storage_type == "postgres_storage":
            load_postgres_plugin(self._storage_config, self._storage_creds)

    @property
    def instance(self) -> "IndyOpenWallet":
        """
        Get internal wallet reference.

        Returns:
            A handle to the wallet

        """
        return self._instance

    @property
    def created(self) -> bool:
        """Check whether the wallet was created on the last open call."""
        return self._instance and self._instance.created

    @property
    def opened(self) -> bool:
        """
        Check whether wallet is currently open.

        Returns:
            True if open, else False

        """
        return bool(self._instance)

    @property
    def name(self) -> str:
        """
        Accessor for the wallet name.

        Returns:
            The wallet name

        """
        return self._name

    @property
    def master_secret_id(self) -> str:
        """
        Accessor for the master secret id.

        Returns:
            The master secret id

        """
        return self._master_secret_id

    @property
    def _wallet_config(self) -> dict:
        """
        Accessor for the wallet config.

        Returns:
            The wallet config

        """
        ret = {
            "id": self._name,
            "freshness_time": self._freshness_time,
            "storage_type": self._storage_type,
            # storage_config
        }
        if self._storage_config is not None:
            ret["storage_config"] = json.loads(self._storage_config)
        return ret

    @property
    def _wallet_access(self) -> dict:
        """
        Accessor for the wallet access.

        Returns:
            The wallet access

        """
        ret = {
            "key": self._key,
            "key_derivation_method": self._key_derivation_method,
            # rekey
            # rekey_derivation_method
            # storage_credentials
        }
        if self._rekey:
            ret["rekey"] = self._rekey
        if self._rekey_derivation_method:
            ret["rekey_derivation_method"] = self._rekey_derivation_method
        if self._storage_creds is not None:
            ret["storage_credentials"] = json.loads(self._storage_creds)

        return ret

    async def create(self, replace: bool = False):
        """
        Create a new wallet.

        Args:
            replace: Removes the old wallet if True

        Raises:
            ProfileError: If there was a problem removing the wallet
            ProfileError: IF there was a libindy error

        """
        if replace:
            try:
                await self.remove()
            except ProfileNotFoundError:
                pass
        try:
            await indy.wallet.create_wallet(
                config=json.dumps(self._wallet_config),
                credentials=json.dumps(self._wallet_access),
            )
        except IndyError as x_indy:
            raise IndyErrorHandler.wrap_error(
                x_indy,
                "Wallet was not removed by SDK, {} may still be open".format(self.name)
                if x_indy.error_code == ErrorCode.WalletAlreadyExistsError
                else None,
                ProfileError,
            ) from x_indy

    async def remove(self):
        """
        Remove an existing wallet.

        Raises:
            WalletNotFoundError: If the wallet could not be found
            WalletError: If there was an libindy error

        """
        try:
            await indy.wallet.delete_wallet(
                config=json.dumps(self._wallet_config),
                credentials=json.dumps(self._wallet_access),
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

    async def open(self):
        """
        Open wallet, removing and/or creating it if so configured.

        Raises:
            WalletError: If wallet not found after creation
            WalletNotFoundError: If the wallet is not found
            WalletError: If the wallet is already open
            WalletError: If there is a libindy error

        """
        if self.opened:
            return

        created = False
        handle = None

        while True:
            try:
                handle = await indy.wallet.open_wallet(
                    config=json.dumps(self._wallet_config),
                    credentials=json.dumps(self._wallet_access),
                )
                if self._rekey:
                    self._key = self._rekey
                    self._rekey = None
                if self._rekey_derivation_method:
                    self._key_derivation_method = self._rekey_derivation_method
                    self._rekey_derivation_method = None
                break
            except IndyError as x_indy:
                if x_indy.error_code == ErrorCode.WalletNotFoundError:
                    if created:
                        raise IndyErrorHandler.wrap_error(
                            x_indy,
                            "Wallet {} not found after creation".format(self.name),
                            ProfileError,
                        ) from x_indy
                    if self._auto_create:
                        await self.create(self._auto_remove)
                        created = True
                    else:
                        raise ProfileNotFoundError(
                            "Wallet {} not found".format(self.name)
                        )
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

        self._instance = IndyOpenWallet(handle, self.name, created, master_secret_id)

    async def close(self):
        """Close previously-opened wallet, removing it if so configured."""
        if self._instance:
            await indy.wallet.close_wallet(self._instance.handle)
            self._instance = None
            if self._auto_remove:
                await self.remove()


class IndyOpenWallet:
    """Handle and metadata for an opened Indy wallet."""

    def __init__(self, handle, name: str, created: bool, master_secret_id: str):
        """Create a new IndyOpenWallet instance."""
        self.created = created
        self.handle = handle
        self.name = name
        self.master_secret_id = master_secret_id
