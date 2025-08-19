import json
import logging
import urllib
import os
from typing import Optional
import base58

from aries_askar import AskarError, AskarErrorCode, Store
from ..core.profile import Profile
from ..database_manager.dbstore import (
    DBStoreError,
    DBStoreErrorCode,
    DBStore,
)
from ..core.error import ProfileDuplicateError, ProfileError, ProfileNotFoundError
from ..utils.env import storage_path

LOGGER = logging.getLogger(__name__)


class KanonStoreConfig:
    """A helper class for handling Kanon store configuration."""

    DEFAULT_KEY = ""
    DEFAULT_KEY_DERIVATION = "kdf:argon2i:mod"
    DEFAULT_STORAGE_TYPE = None
    DEFAULT_SCHEMA_CONFIG = "normalize"

    # Current schema release number refers to the schema version currently supported by this ACA-Py release.
    # If the schema version in the database is lower than the current release version,
    # then during store opening, the system will halt and prompt the user to perform an upgrade.
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
        self.storage_config = config.get("storage_config", None)
        self.storage_creds = config.get("storage_creds", None)

        storage_type = config.get("storage_type")
        if not storage_type or storage_type == "default":
            storage_type = "sqlite"
        elif storage_type == "postgres_storage":
            storage_type = "postgres"
        if storage_type not in ("postgres", "sqlite"):
            raise ProfileError(f"Unsupported storage type: {storage_type}")
        self.storage_type = storage_type

        self.dbstore_key = config.get("dbstore_key")
        LOGGER.debug("dbstore_key: %s", self.dbstore_key)
        self.dbstore_rekey = config.get("dbstore_rekey")
        LOGGER.debug("dbstore_rekey: %s", self.dbstore_rekey)
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
                if "tls" in config_dict and isinstance(config_dict["tls"], dict):
                    tls_config = config_dict["tls"]
                    if "sslmode" in tls_config and tls_config["sslmode"] not in [
                        "disable",
                        "allow",
                        "prefer",
                        "require",
                        "verify-ca",
                        "verify-full",
                    ]:
                        raise ProfileError("Invalid sslmode in tls configuration")
            except json.JSONDecodeError as e:
                LOGGER.error(
                    "Invalid JSON in dbstore_storage_config: %s",
                    self.dbstore_storage_config,
                )
                raise ProfileError(f"dbstore_storage_config must be valid JSON: {str(e)}")
        LOGGER.debug("dbstore_storage_config: %s", self.dbstore_storage_config)

        self.dbstore_storage_creds = config.get("dbstore_storage_creds", None)
        LOGGER.debug("dbstore_storage_creds: %s", self.dbstore_storage_creds)

        self.dbstore_schema_config = config.get(
            "dbstore_schema_config", self.DEFAULT_SCHEMA_CONFIG
        )
        LOGGER.debug("dbstore_schema_config: %s", self.dbstore_schema_config)

        self.dbstore_schema_migration = config.get("dbstore_schema_migration", None)
        LOGGER.debug("dbstore_schema_migration: %s", self.dbstore_schema_migration)

        dbstore_storage_type = config.get("dbstore_storage_type")
        if not dbstore_storage_type or dbstore_storage_type == "default":
            dbstore_storage_type = "sqlite"
        elif dbstore_storage_type == "postgres_storage":
            dbstore_storage_type = "postgres"
        if dbstore_storage_type not in ("postgres", "sqlite"):
            raise ProfileError(
                f"Unsupported dbstore storage type: {dbstore_storage_type}"
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
                raise ProfileError(f"dbstore_storage_creds must be valid JSON: {str(e)}")

    @staticmethod
    def validate_base58_key(key: str):
        try:
            decoded = base58.b58decode(key)
            print(f"Decoded length: {len(decoded)}")
        except ValueError as e:
            print(f"Decode error: {e}")

    def get_dbstore_uri(
        self, create: bool = False, in_memory: Optional[bool] = False
    ) -> str:
        LOGGER.debug(
            "Generating DBStore URI with dbstore_storage_type=%s, create=%s, in_memory=%s",
            self.dbstore_storage_type,
            create,
            in_memory,
        )
        uri = f"{self.dbstore_storage_type}://"
        if self.dbstore_storage_type == "sqlite":
            if in_memory:
                uri += ":memory:"
                LOGGER.debug("Generated SQLite in-memory URI: %s", uri)
                return uri
            base_path = storage_path("wallet", self.name, create=create).as_posix()
            db_file = "sqlite_dbstore.db"
            path = f"{base_path}/dbstore"
            os.makedirs(path, exist_ok=True)
            uri += urllib.parse.quote(f"{path}/{db_file}")
            LOGGER.debug("Generated SQLite file URI: %s", uri)
        elif self.dbstore_storage_type == "postgres":
            if not self.dbstore_storage_config:
                LOGGER.error("No 'storage_config' provided for postgres store")
                raise ProfileError("No 'storage_config' provided for postgres store")
            if not self.dbstore_storage_creds:
                LOGGER.error("No 'storage_creds' provided for postgres store")
                raise ProfileError("No 'storage_creds' provided for postgres store")
            config = json.loads(self.dbstore_storage_config)
            creds = json.loads(self.dbstore_storage_creds)
            LOGGER.debug("Parsed dbstore_storage_config: %s", config)
            LOGGER.debug("Parsed dbstore_storage_creds: %s", creds)
            config_url = config.get("url")
            if not config_url:
                LOGGER.error("No 'url' provided for postgres store")
                raise ProfileError("No 'url' provided for postgres store")
            if "account" not in creds:
                LOGGER.error("No 'account' provided for postgres store")
                raise ProfileError("No 'account' provided for postgres store")
            if "password" not in creds:
                LOGGER.error("No 'password' provided for postgres store")
                raise ProfileError("No 'password' provided for postgres store")
            account = urllib.parse.quote(creds["account"])
            password = urllib.parse.quote(creds["password"])
            # db_name = urllib.parse.quote(self.name)
            db_name = urllib.parse.quote(
                self.name + "_dbstore"
            )  # add _dbstore in the db name to ensure no conflict with askar
            uri += f"{account}:{password}@{config_url}/{db_name}"
            params = {}
            if "connection_timeout" in config:
                params["connect_timeout"] = config["connection_timeout"]
            if "tls" in config:
                tls_config = config["tls"]
                if isinstance(tls_config, dict):
                    if "sslmode" in tls_config:
                        params["sslmode"] = tls_config["sslmode"]
                    if "sslcert" in tls_config:
                        params["sslcert"] = tls_config["sslcert"]
                    if "sslkey" in tls_config:
                        params["sslkey"] = tls_config["sslkey"]
                    if "sslrootcert" in tls_config:
                        params["sslrootcert"] = tls_config["sslrootcert"]
            if "admin_account" in creds:
                params["admin_account"] = creds["admin_account"]
            if "admin_password" in creds:
                params["admin_password"] = creds["admin_password"]
            if params:
                uri += "?" + urllib.parse.urlencode(params)
            LOGGER.debug("Generated PostgreSQL URI: %s", uri)
        return uri

    def get_askar_uri(
        self, create: bool = False, in_memory: Optional[bool] = False
    ) -> str:
        uri = f"{self.storage_type}://"
        if self.storage_type == "sqlite":
            if in_memory:
                uri += ":memory:"
                return uri
            base_path = storage_path("wallet", self.name, create=create).as_posix()
            db_file = "sqlite_kms.db"
            path = f"{base_path}/askar"
            os.makedirs(path, exist_ok=True)
            uri += urllib.parse.quote(f"{path}/{db_file}")
        elif self.storage_type == "postgres":
            if not self.storage_config:
                raise ProfileError("No 'storage_config' provided for postgres store")
            if not self.storage_creds:
                raise ProfileError("No 'storage_creds' provided for postgres store")
            config = json.loads(self.storage_config)
            creds = json.loads(self.storage_creds)
            config_url = config.get("url")
            if not config_url:
                raise ProfileError("No 'url' provided for postgres store")
            if "account" not in creds:
                raise ProfileError("No 'account' provided for postgres store")
            if "password" not in creds:
                raise ProfileError("No 'password' provided for postgres store")
            account = urllib.parse.quote(creds["account"])
            password = urllib.parse.quote(creds["password"])
            db_name = urllib.parse.quote(self.name)
            uri += f"{account}:{password}@{config_url}/{db_name}"
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

    async def remove_store(self):
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
        except (AskarError, DBStoreError) as err:
            if (isinstance(err, AskarError) and err.code == AskarErrorCode.NOT_FOUND) or (
                isinstance(err, DBStoreError) and err.code == DBStoreErrorCode.NOT_FOUND
            ):
                raise ProfileNotFoundError(f"Store '{self.name}' not found")
            raise ProfileError(
                f"Error removing {self.store_class} store: {str(err)}"
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
        db_store = None
        askar_store = None

        config = (
            json.loads(self.dbstore_storage_config) if self.dbstore_storage_config else {}
        )

        try:
            if provision:
                release_number = (
                    "release_0"
                    if self.dbstore_schema_config == "generic"
                    else self.CURRENT_SCHEMA_RELEASE_NUMBER
                )
                db_store = await DBStore.provision(
                    db_uri,
                    self.key_derivation_method,
                    self.dbstore_key,
                    profile=self.name,
                    recreate=self.auto_recreate,
                    release_number=release_number,
                    schema_config=self.dbstore_schema_config,
                    config=config,
                )
            else:
                target_release = self.CURRENT_SCHEMA_RELEASE_NUMBER
                db_store = await DBStore.open(
                    db_uri,
                    self.key_derivation_method,
                    self.dbstore_key,
                    profile=self.name,
                    schema_migration=self.dbstore_schema_migration,
                    target_schema_release_number=target_release,
                    config=config,
                )
        except DBStoreError as err:
            if err.code == DBStoreErrorCode.NOT_FOUND:
                raise ProfileNotFoundError(f"DBStore '{self.name}' not found")
            elif err.code == DBStoreErrorCode.DUPLICATE:
                raise ProfileDuplicateError(f"Duplicate DBStore '{self.name}'")
            raise ProfileError("Error opening DBStore") from err

        try:
            if provision:
                askar_store = await Store.provision(
                    askar_uri,
                    self.key_derivation_method,
                    self.key,
                    profile=self.name,
                    recreate=self.auto_recreate,
                )
            else:
                askar_store = await Store.open(
                    askar_uri, self.key_derivation_method, self.key, profile=self.name
                )
        except AskarError as err:
            self._handle_askar_open_error(err, retry=True)
            if self.rekey:
                try:
                    askar_store = await Store.open(
                        askar_uri,
                        self.key_derivation_method,
                        self.DEFAULT_KEY,
                        profile=self.name,
                    )
                    await askar_store.rekey(self.rekey_derivation_method, self.rekey)
                except AskarError as retry_err:
                    raise ProfileError(
                        "Error opening Askar store after retry"
                    ) from retry_err

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

        return KanonOpenStore(self, provision, db_store, askar_store)


class KanonOpenStore:
    def __init__(
        self, config: KanonStoreConfig, created, db_store: DBStore, askar_store: Store
    ):
        self.config = config
        self.created = created
        self.db_store = db_store
        self.askar_store = askar_store

    @property
    def name(self) -> str:
        return self.config.name

    async def close(self):
        if self.db_store:
            await self.db_store.close(remove=self.config.auto_remove)
        if self.askar_store:
            await self.askar_store.close(remove=self.config.auto_remove)
