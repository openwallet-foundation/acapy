"""Module docstring."""

import json
import logging
import os
import urllib
from typing import Optional

import base58
from aries_askar import AskarError, AskarErrorCode, Store

from ..askar.store import ERR_NO_STORAGE_CONFIG, ERR_NO_STORAGE_CREDS
from ..core.error import ProfileDuplicateError, ProfileError, ProfileNotFoundError
from ..core.profile import Profile
from ..database_manager.db_errors import DBCode, DBError
from ..database_manager.dbstore import (
    DBStore,
    DBStoreError,
    DBStoreErrorCode,
)
from ..utils.env import storage_path

LOGGER = logging.getLogger(__name__)

ERR_STORAGE_TYPE_UNSUPPORTED = "Unsupported storage type: {}"
ERR_DBSTORE_STORAGE_TYPE_UNSUPPORTED = "Unsupported dbstore storage type: {}"
ERR_JSON_INVALID = "{} must be valid JSON: {}"
ERR_NO_URL = "No 'url' provided for postgres store"
ERR_NO_ACCOUNT = "No 'account' provided for postgres store"
ERR_NO_PASSWORD = "No 'password' provided for postgres store"
ERR_REMOVE_STORE = "Error removing {} store: {}"


class KanonStoreConfig:
    """A helper class for handling Kanon store configuration."""

    DEFAULT_KEY = ""
    DEFAULT_KEY_DERIVATION = "kdf:argon2i:mod"
    DEFAULT_STORAGE_TYPE = None
    DEFAULT_SCHEMA_CONFIG = "normalize"

    # Current schema release number refers to the schema version currently
    # supported by this ACA-Py release.
    # If the schema version in the database is lower than the current
    # release version,
    # then during store opening, the system will halt and prompt the user to
    # perform an upgrade.
    CURRENT_SCHEMA_RELEASE_NUMBER = "release_0_1"

    KEY_DERIVATION_RAW = "RAW"
    KEY_DERIVATION_ARGON2I_INT = "kdf:argon2i:int"
    KEY_DERIVATION_ARGON2I_MOD = "kdf:argon2i:mod"

    # {
    #   "url": "postgresql://localhost:5432/mydb",
    #   "min_connections": 4,
    #   "max_connections": 10,
    #   "connect_timeout_ms": 30000,
    #   "max_idle": 5.0,
    #   "max_lifetime": 3600.0,
    #   "tls": {
    #     "sslmode": "verify-full",
    #     "sslcert": "/path/to/client-cert.pem",
    #     "sslkey": "/path/to/client-key.pem",
    #     "sslrootcert": "/path/to/root-cert.pem"
    #   }
    # }

    def __init__(self, config: Optional[dict] = None, store_class: str = "dbstore"):
        """Initialize a `KanonStoreConfig` instance."""
        if not config:
            config = {}
        self.store_class = store_class

        self._init_basic_config(config)
        self._init_askar_config(config)
        self._init_dbstore_config(config)

    def _init_basic_config(self, config: dict):
        """Initialize basic configuration settings."""
        self.auto_recreate = config.get("auto_recreate", False)
        self.auto_remove = config.get("auto_remove", False)
        self.key = config.get("key", self.DEFAULT_KEY)
        self.key_is_encoded = config.get("key_is_encoded", False)
        self.key_derivation_method = (
            config.get("key_derivation_method") or self.DEFAULT_KEY_DERIVATION
        )
        self.rekey = config.get("rekey")
        self.rekey_derivation_method = (
            config.get("rekey_derivation_method") or self.DEFAULT_KEY_DERIVATION
        )
        self.name = config.get("name") or Profile.DEFAULT_NAME

    def _init_askar_config(self, config: dict):
        """Initialize Askar-specific configuration."""
        self.storage_config = config.get("storage_config", None)
        self.storage_creds = config.get("storage_creds", None)

        storage_type = config.get("storage_type")
        if not storage_type or storage_type == "default":
            storage_type = "sqlite"
        elif storage_type == "postgres_storage":
            storage_type = "postgres"
        if storage_type not in ("postgres", "sqlite"):
            raise ProfileError(ERR_STORAGE_TYPE_UNSUPPORTED.format(storage_type))
        self.storage_type = storage_type

    def _init_dbstore_config(self, config: dict):
        """Initialize DBStore-specific configuration."""
        self.dbstore_key = config.get("dbstore_key")
        LOGGER.debug("dbstore_key: %s", self.dbstore_key)
        self.dbstore_rekey = config.get("dbstore_rekey")
        LOGGER.debug("dbstore_rekey: %s", self.dbstore_rekey)

        self._validate_dbstore_storage_config(config)
        self._init_dbstore_schema_config(config)
        self._init_dbstore_storage_type(config)

    def _validate_dbstore_storage_config(self, config: dict):
        """Validate DBStore storage configuration."""
        self.dbstore_storage_config = config.get("dbstore_storage_config", None)
        if self.dbstore_storage_config:
            try:
                config_dict = json.loads(self.dbstore_storage_config)
                required_keys = ["url"]
                for key in required_keys:
                    if key not in config_dict:
                        raise ProfileError(
                            f"Missing required key '{key}' in dbstore_storage_config"
                        )
                self._validate_tls_config(config_dict)
            except json.JSONDecodeError as e:
                LOGGER.error(
                    "Invalid JSON in dbstore_storage_config: %s",
                    self.dbstore_storage_config,
                )
                raise ProfileError(
                    ERR_JSON_INVALID.format("dbstore_storage_config", str(e))
                )
        LOGGER.debug("dbstore_storage_config: %s", self.dbstore_storage_config)

        self.dbstore_storage_creds = config.get("dbstore_storage_creds", None)
        LOGGER.debug("dbstore_storage_creds: %s", self.dbstore_storage_creds)

    def _validate_tls_config(self, config_dict: dict):
        """Validate TLS configuration settings."""
        if "tls" in config_dict and isinstance(config_dict["tls"], dict):
            tls_config = config_dict["tls"]
            valid_sslmodes = [
                "disable",
                "allow",
                "prefer",
                "require",
                "verify-ca",
                "verify-full",
            ]
            if "sslmode" in tls_config and tls_config["sslmode"] not in valid_sslmodes:
                raise ProfileError("Invalid sslmode in tls configuration")

    def _init_dbstore_schema_config(self, config: dict):
        """Initialize DBStore schema configuration."""
        self.dbstore_schema_config = config.get(
            "dbstore_schema_config", self.DEFAULT_SCHEMA_CONFIG
        )
        LOGGER.debug("dbstore_schema_config: %s", self.dbstore_schema_config)

        self.dbstore_schema_migration = config.get("dbstore_schema_migration", None)
        LOGGER.debug("dbstore_schema_migration: %s", self.dbstore_schema_migration)

    def _init_dbstore_storage_type(self, config: dict):
        """Initialize and validate DBStore storage type."""
        dbstore_storage_type = config.get("dbstore_storage_type")
        if not dbstore_storage_type or dbstore_storage_type == "default":
            dbstore_storage_type = "sqlite"
        elif dbstore_storage_type == "postgres_storage":
            dbstore_storage_type = "postgres"
        if dbstore_storage_type not in ("postgres", "sqlite"):
            raise ProfileError(
                ERR_DBSTORE_STORAGE_TYPE_UNSUPPORTED.format(dbstore_storage_type)
            )
        self.dbstore_storage_type = dbstore_storage_type
        LOGGER.debug("dbstore_storage_type: %s", self.dbstore_storage_type)

        if self.dbstore_storage_type == "postgres" and self.dbstore_storage_creds:
            try:
                json.loads(self.dbstore_storage_creds)
            except json.JSONDecodeError as e:
                LOGGER.error(
                    "Invalid JSON in dbstore_storage_creds: %s",
                    self.dbstore_storage_creds,
                )
                raise ProfileError(
                    ERR_JSON_INVALID.format("dbstore_storage_creds", str(e))
                )

    @staticmethod
    def validate_base58_key(key: str):
        """Validate base58 key."""
        try:
            decoded = base58.b58decode(key)
            print(f"Decoded length: {len(decoded)}")
        except ValueError as e:
            print(f"Decode error: {e}")

    def get_dbstore_uri(
        self, create: bool = False, in_memory: Optional[bool] = False
    ) -> str:
        """Get DBStore URI."""
        LOGGER.debug(
            "DBStore URI: dbstore_storage_type=%s, create=%s, in_memory=%s",
            self.dbstore_storage_type,
            create,
            in_memory,
        )
        uri = f"{self.dbstore_storage_type}://"
        if self.dbstore_storage_type == "sqlite":
            return self._build_sqlite_dbstore_uri(uri, create, in_memory)
        elif self.dbstore_storage_type == "postgres":
            return self._build_postgres_dbstore_uri(uri)
        return uri

    def _build_sqlite_dbstore_uri(
        self, base_uri: str, create: bool, in_memory: Optional[bool]
    ) -> str:
        """Build SQLite DBStore URI."""
        if in_memory:
            uri = base_uri + ":memory:"
            LOGGER.debug("Generated SQLite in-memory URI: %s", uri)
            return uri
        base_path = storage_path("wallet", self.name, create=create).as_posix()
        db_file = "sqlite_dbstore.db"
        path = f"{base_path}/dbstore"
        os.makedirs(path, exist_ok=True)
        uri = base_uri + urllib.parse.quote(f"{path}/{db_file}")
        LOGGER.debug("Generated SQLite file URI: %s", uri)
        return uri

    def _build_postgres_dbstore_uri(self, base_uri: str) -> str:
        """Build PostgreSQL DBStore URI."""
        self._validate_postgres_dbstore_config()
        config = json.loads(self.dbstore_storage_config)
        creds = json.loads(self.dbstore_storage_creds)
        LOGGER.debug("Parsed dbstore_storage_config (keys): %s", list(config.keys()))
        LOGGER.debug("Parsed dbstore_storage_creds (keys): %s", list(creds.keys()))

        config_url = self._validate_postgres_dbstore_url(config)
        account, password = self._validate_postgres_dbstore_creds(creds)

        db_name = urllib.parse.quote(self.name + "_dbstore")
        uri = base_uri + f"{account}:{password}@{config_url}/{db_name}"

        params = self._build_postgres_dbstore_params(config, creds)
        if params:
            uri += "?" + urllib.parse.urlencode(params)

        # Log redacted version for security
        redacted_uri = base_uri + f"{account}:***@{config_url}/{db_name}"
        if params:
            redacted_uri += "?" + urllib.parse.urlencode(params)
        LOGGER.debug("Generated PostgreSQL URI: %s", redacted_uri)
        return uri

    def _validate_postgres_dbstore_config(self):
        """Validate PostgreSQL DBStore configuration."""
        if not self.dbstore_storage_config:
            LOGGER.error(ERR_NO_STORAGE_CONFIG)
            raise ProfileError(ERR_NO_STORAGE_CONFIG)
        if not self.dbstore_storage_creds:
            LOGGER.error(ERR_NO_STORAGE_CREDS)
            raise ProfileError(ERR_NO_STORAGE_CREDS)

    def _validate_postgres_dbstore_url(self, config: dict) -> str:
        """Validate and return PostgreSQL DBStore URL."""
        config_url = config.get("url")
        if not config_url:
            LOGGER.error(ERR_NO_URL)
            raise ProfileError(ERR_NO_URL)
        return config_url

    def _validate_postgres_dbstore_creds(self, creds: dict) -> tuple[str, str]:
        """Validate and return PostgreSQL DBStore credentials."""
        if "account" not in creds:
            LOGGER.error(ERR_NO_ACCOUNT)
            raise ProfileError(ERR_NO_ACCOUNT)
        if "password" not in creds:
            LOGGER.error(ERR_NO_PASSWORD)
            raise ProfileError(ERR_NO_PASSWORD)
        account = urllib.parse.quote(creds["account"])
        password = urllib.parse.quote(creds["password"])
        return account, password

    def _build_postgres_dbstore_params(self, config: dict, creds: dict) -> dict:
        """Build PostgreSQL DBStore connection parameters."""
        params = {}
        if "connection_timeout" in config:
            params["connect_timeout"] = config["connection_timeout"]
        self._add_tls_params(config, params)
        self._add_admin_params(creds, params)
        return params

    def _add_tls_params(self, config: dict, params: dict):
        """Add TLS parameters to connection params."""
        if "tls" in config:
            tls_config = config["tls"]
            if isinstance(tls_config, dict):
                tls_fields = ["sslmode", "sslcert", "sslkey", "sslrootcert"]
                for field in tls_fields:
                    if field in tls_config:
                        params[field] = tls_config[field]

    def _add_admin_params(self, creds: dict, params: dict):
        """Add admin parameters to connection params."""
        admin_fields = ["admin_account", "admin_password"]
        for field in admin_fields:
            if field in creds:
                params[field] = creds[field]

    def get_askar_uri(
        self, create: bool = False, in_memory: Optional[bool] = False
    ) -> str:
        """Get Askar URI."""
        uri = f"{self.storage_type}://"
        if self.storage_type == "sqlite":
            return self._build_sqlite_askar_uri(uri, create, in_memory)
        elif self.storage_type == "postgres":
            return self._build_postgres_askar_uri(uri)
        return uri

    def _build_sqlite_askar_uri(
        self, base_uri: str, create: bool, in_memory: Optional[bool]
    ) -> str:
        """Build SQLite Askar URI."""
        if in_memory:
            return base_uri + ":memory:"
        base_path = storage_path("wallet", self.name, create=create).as_posix()
        db_file = "sqlite_kms.db"
        path = f"{base_path}/askar"
        os.makedirs(path, exist_ok=True)
        return base_uri + urllib.parse.quote(f"{path}/{db_file}")

    def _build_postgres_askar_uri(self, base_uri: str) -> str:
        """Build PostgreSQL Askar URI."""
        self._validate_postgres_askar_config()
        config = json.loads(self.storage_config)
        creds = json.loads(self.storage_creds)

        config_url = self._validate_postgres_askar_url(config)
        account, password = self._validate_postgres_askar_creds(creds)

        db_name = urllib.parse.quote(self.name)
        uri = base_uri + f"{account}:{password}@{config_url}/{db_name}"

        params = self._build_postgres_askar_params(config, creds)
        if params:
            uri += "?" + urllib.parse.urlencode(params)
        return uri

    def _validate_postgres_askar_config(self):
        """Validate PostgreSQL Askar configuration."""
        if not self.storage_config:
            raise ProfileError(ERR_NO_STORAGE_CONFIG)
        if not self.storage_creds:
            raise ProfileError(ERR_NO_STORAGE_CREDS)

    def _validate_postgres_askar_url(self, config: dict) -> str:
        """Validate and return PostgreSQL Askar URL."""
        config_url = config.get("url")
        if not config_url:
            raise ProfileError(ERR_NO_URL)
        return config_url

    def _validate_postgres_askar_creds(self, creds: dict) -> tuple[str, str]:
        """Validate and return PostgreSQL Askar credentials."""
        if "account" not in creds:
            raise ProfileError(ERR_NO_ACCOUNT)
        if "password" not in creds:
            raise ProfileError(ERR_NO_PASSWORD)
        account = urllib.parse.quote(creds["account"])
        password = urllib.parse.quote(creds["password"])
        return account, password

    def _build_postgres_askar_params(self, config: dict, creds: dict) -> dict:
        """Build PostgreSQL Askar connection parameters."""
        params = {}
        if "connection_timeout" in config:
            params["connect_timeout"] = config["connection_timeout"]
        if "max_connections" in config:
            params["max_connections"] = config["max_connections"]
        if "min_idle_count" in config:
            params["min_connections"] = config["min_idle_count"]

        admin_fields = ["admin_account", "admin_password"]
        for field in admin_fields:
            if field in creds:
                params[field] = creds[field]
        return params

    # ---------- helpers to reduce cognitive complexity ----------

    def _build_sqlite_uri(self, base: str, subdir: str, filename: str) -> str:
        base_path = storage_path("wallet", self.name, create=base == "dbstore").as_posix()
        path = f"{base_path}/{subdir}"
        os.makedirs(path, exist_ok=True)
        return urllib.parse.quote(f"{path}/{filename}")

    async def _open_or_provision_dbstore(
        self,
        db_uri: str,
        provision: bool,
        config: dict,
    ):
        if provision:
            release_number = (
                "release_0"
                if self.dbstore_schema_config == "generic"
                else self.CURRENT_SCHEMA_RELEASE_NUMBER
            )
            return await DBStore.provision(
                db_uri,
                self.key_derivation_method,
                self.dbstore_key,
                profile=self.name,
                recreate=self.auto_recreate,
                release_number=release_number,
                schema_config=self.dbstore_schema_config,
                config=config,
            )
        target_release = self.CURRENT_SCHEMA_RELEASE_NUMBER
        return await DBStore.open(
            db_uri,
            self.key_derivation_method,
            self.dbstore_key,
            profile=self.name,
            schema_migration=self.dbstore_schema_migration,
            target_schema_release_number=target_release,
            config=config,
        )

    async def _open_or_provision_askar(self, askar_uri: str, provision: bool):
        if provision:
            return await Store.provision(
                askar_uri,
                self.key_derivation_method,
                self.key,
                profile=self.name,
                recreate=self.auto_recreate,
            )
        return await Store.open(
            askar_uri,
            self.key_derivation_method,
            self.key,
            profile=self.name,
        )

    async def remove_store(self):
        """Remove store."""
        try:
            if self.store_class == "askar":
                await Store.remove(self.get_askar_uri())
            else:
                config = (
                    json.loads(self.dbstore_storage_config)
                    if self.dbstore_storage_config
                    else {}
                )
                await DBStore.remove(self.get_dbstore_uri(), config=config)
        except DBError as err:
            if err.code in DBCode.NOT_FOUND:
                raise ProfileNotFoundError(f"Store '{self.name}' not found")
            raise ProfileError(
                ERR_REMOVE_STORE.format(self.store_class, str(err))
            ) from err

    def _handle_askar_open_error(self, err: AskarError, retry: bool = False):
        if err.code == AskarErrorCode.DUPLICATE:
            raise ProfileDuplicateError(f"Duplicate store '{self.name}'")
        if err.code == AskarErrorCode.NOT_FOUND:
            raise ProfileNotFoundError(f"Store '{self.name}' not found")
        if retry and self.rekey:
            return
        raise ProfileError("Error opening Askar store") from err

    async def open_store(
        self, provision: bool = False, in_memory: Optional[bool] = False
    ) -> "KanonOpenStore":
        """Open or provision both DBStore and Askar Store with separate error handling."""
        db_uri = self.get_dbstore_uri(create=provision, in_memory=in_memory)
        askar_uri = self.get_askar_uri(create=provision, in_memory=in_memory)

        config = (
            json.loads(self.dbstore_storage_config) if self.dbstore_storage_config else {}
        )

        db_store = await self._open_dbstore_with_error_handling(db_uri, provision, config)
        askar_store = await self._open_askar_with_error_handling(askar_uri, provision)

        await self._handle_store_rekeying(db_store, askar_store)

        return KanonOpenStore(self, provision, db_store, askar_store)

    async def _open_dbstore_with_error_handling(
        self, db_uri: str, provision: bool, config: dict
    ):
        """Open DBStore with proper error handling."""
        try:
            return await self._open_or_provision_dbstore(db_uri, provision, config)
        except DBStoreError as err:
            if err.code == DBStoreErrorCode.NOT_FOUND:
                raise ProfileNotFoundError(f"DBStore '{self.name}' not found")
            elif err.code == DBStoreErrorCode.DUPLICATE:
                raise ProfileDuplicateError(f"Duplicate DBStore '{self.name}'")
            raise ProfileError("Error opening DBStore") from err

    async def _open_askar_with_error_handling(self, askar_uri: str, provision: bool):
        """Open Askar store with proper error handling and retry logic."""
        try:
            return await self._open_or_provision_askar(askar_uri, provision)
        except AskarError as err:
            self._handle_askar_open_error(err, retry=True)
            if self.rekey:
                return await self._retry_askar_open_with_rekey(askar_uri)
            return None

    async def _retry_askar_open_with_rekey(self, askar_uri: str):
        """Retry opening Askar store with rekey."""
        try:
            askar_store = await Store.open(
                askar_uri,
                self.key_derivation_method,
                self.DEFAULT_KEY,
                profile=self.name,
            )
            await askar_store.rekey(self.rekey_derivation_method, self.rekey)
            return askar_store
        except AskarError as retry_err:
            raise ProfileError("Error opening Askar store after retry") from retry_err

    async def _handle_store_rekeying(self, db_store, askar_store):
        """Handle rekeying for both stores if required."""
        if db_store and self.dbstore_rekey:
            try:
                await db_store.rekey(self.rekey_derivation_method, self.dbstore_rekey)
            except DBStoreError as err:
                raise ProfileError("Error rekeying DBStore") from err
        if askar_store and self.rekey:
            try:
                await askar_store.rekey(self.rekey_derivation_method, self.rekey)
            except AskarError as err:
                raise ProfileError("Error rekeying Askar store") from err


class KanonOpenStore:
    """Kanon open store."""

    def __init__(
        self, config: KanonStoreConfig, created, db_store: DBStore, askar_store: Store
    ):
        """Initialize KanonOpenStore with configuration and stores."""
        self.config = config
        self.created = created
        self.db_store = db_store
        self.askar_store = askar_store

    @property
    def name(self) -> str:
        """Get store name."""
        return self.config.name

    async def close(self):
        """Close store."""
        if self.db_store:
            await self.db_store.close(remove=self.config.auto_remove)
        if self.askar_store:
            await self.askar_store.close(remove=self.config.auto_remove)
