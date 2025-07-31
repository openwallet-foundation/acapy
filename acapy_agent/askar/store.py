"""Askar store configuration and management."""

import asyncio
import json
import logging
import urllib.parse
from dataclasses import dataclass
from typing import Optional

from aries_askar import AskarError, AskarErrorCode, Store

from ..core.error import ProfileDuplicateError, ProfileError, ProfileNotFoundError
from ..core.profile import Profile
from ..utils.env import storage_path

LOGGER = logging.getLogger(__name__)


class AskarStoreConfig:
    """Helper for handling Askar store configuration."""

    DEFAULT_KEY = ""
    DEFAULT_KEY_DERIVATION = "kdf:argon2i:mod"
    SUPPORTED_STORAGE_TYPES = ("sqlite", "postgres")

    def __init__(self, config: Optional[dict] = None):
        """Initialize store configuration."""
        config = config or {}

        self.auto_recreate = config.get("auto_recreate", False)
        self.auto_remove = config.get("auto_remove", False)

        self.key = config.get("key", self.DEFAULT_KEY)
        self.key_derivation_method = (
            config.get("key_derivation_method") or self.DEFAULT_KEY_DERIVATION
        )
        self.rekey = config.get("rekey")
        self.rekey_derivation_method = (
            config.get("rekey_derivation_method") or self.DEFAULT_KEY_DERIVATION
        )
        self.name = config.get("name") or Profile.DEFAULT_NAME

        self.storage_config = config.get("storage_config")
        self.storage_creds = config.get("storage_creds")

        storage_type = config.get("storage_type") or "sqlite"
        if storage_type == "default":
            storage_type = "sqlite"
        elif storage_type == "postgres_storage":
            storage_type = "postgres"
        if storage_type not in self.SUPPORTED_STORAGE_TYPES:
            raise ProfileError(f"Unsupported storage type: {storage_type}")
        self.storage_type = storage_type

    def get_uri(self, create: bool = False, in_memory: Optional[bool] = False) -> str:
        """Construct the storage URI."""
        if self.storage_type == "sqlite":
            return self._build_sqlite_uri(in_memory, create)
        elif self.storage_type == "postgres":
            return self._build_postgres_uri()
        raise ProfileError(f"Unsupported storage type: {self.storage_type}")

    def _build_sqlite_uri(self, in_memory: Optional[bool], create: bool) -> str:
        if in_memory:
            return "sqlite://:memory:"
        path = storage_path("wallet", self.name, create=create).as_posix()
        return f"sqlite://{urllib.parse.quote(f'{path}/sqlite.db')}"

    def _build_postgres_uri(self) -> str:
        config, creds = self._validate_postgres_config()

        account = urllib.parse.quote(creds["account"])
        password = urllib.parse.quote(creds["password"])
        db_name = urllib.parse.quote(self.name)

        uri = f"postgres://{account}:{password}@{config['url']}/{db_name}"

        params = {}
        if "connection_timeout" in config:
            params["connect_timeout"] = config["connection_timeout"]
        if "max_connections" in config:
            params["max_connections"] = config["max_connections"]
        if "min_idle_count" in config:
            params["min_connections"] = config["min_idle_count"]
        if "admin_account" in creds:
            params["admin_account"] = creds["admin_account"]
        if "admin_password" in creds:
            params["admin_password"] = creds["admin_password"]

        if params:
            uri += "?" + urllib.parse.urlencode(params)

        return uri

    def _validate_postgres_config(self):
        if not self.storage_config:
            raise ProfileError("No 'storage_config' provided for postgres store")
        if not self.storage_creds:
            raise ProfileError("No 'storage_creds' provided for postgres store")

        try:
            config = json.loads(self.storage_config)
            creds = json.loads(self.storage_creds)
        except json.JSONDecodeError as e:
            raise ProfileError("Invalid JSON in storage config or creds") from e

        if "url" not in config:
            raise ProfileError("Missing 'url' in postgres storage_config")
        if "account" not in creds:
            raise ProfileError("Missing 'account' in postgres storage_creds")
        if "password" not in creds:
            raise ProfileError("Missing 'password' in postgres storage_creds")

        return config, creds

    async def remove_store(self):
        """Remove the store if it exists."""
        try:
            await Store.remove(self.get_uri())
        except AskarError as err:
            if err.code == AskarErrorCode.NOT_FOUND:
                raise ProfileNotFoundError(f"Store '{self.name}' not found")
            raise ProfileError("Error removing store") from err

    async def _handle_open_error(self, err: AskarError, retry=False):
        if err.code == AskarErrorCode.BACKEND:
            LOGGER.warning(
                "Askar backend error: %s. This may indicate multiple instances "
                "attempting to create the same store at the same time or a misconfigured "
                "backend.",
                err,
            )
            await asyncio.sleep(0.5)  # Wait before retrying
            return
        elif err.code == AskarErrorCode.DUPLICATE:
            raise ProfileDuplicateError(f"Duplicate store '{self.name}'")
        elif err.code == AskarErrorCode.NOT_FOUND:
            raise ProfileNotFoundError(f"Store '{self.name}' not found")
        elif retry and self.rekey:
            return
        raise ProfileError("Error opening store") from err

    async def _attempt_store_open(self, uri: str, provision: bool):
        if provision:
            return await Store.provision(
                uri,
                self.key_derivation_method,
                self.key,
                recreate=self.auto_recreate,
            )
        store = await Store.open(uri, self.key_derivation_method, self.key)
        if self.rekey:
            await Store.rekey(store, self.rekey_derivation_method, self.rekey)
        return store

    def _finalize_open(self, store, provision: bool) -> "AskarOpenStore":
        return AskarOpenStore(self, provision, store)

    async def open_store(
        self, provision: bool = False, in_memory: Optional[bool] = False
    ) -> "AskarOpenStore":
        """Open or provision the store based on configuration."""
        uri = self.get_uri(create=provision, in_memory=in_memory)

        for attempt in range(1, 4):
            LOGGER.debug("Store open attempt %d/3", attempt)
            try:
                store = await self._attempt_store_open(uri, provision)
                LOGGER.debug("Store opened successfully on attempt %d", attempt)
                return self._finalize_open(store, provision)
            except AskarError as err:
                LOGGER.debug(
                    "AskarError during store open attempt %d/3: %s", attempt, err
                )
                await self._handle_open_error(err, retry=True)

        raise ProfileError("Failed to open or provision store after retries")


@dataclass
class AskarOpenStore:
    """Handle and metadata for an opened Askar store."""

    config: AskarStoreConfig
    created: bool
    store: Store

    @property
    def name(self) -> str:
        """Accessor for the store name."""
        return self.config.name

    async def close(self):
        """Close and optionally remove the store."""
        if self.store:
            await self.store.close(remove=self.config.auto_remove)
            self.store = None
