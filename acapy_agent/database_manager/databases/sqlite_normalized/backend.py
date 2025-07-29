import logging
from typing import Optional

from ...dbstore import DatabaseBackend
from ...error import DBStoreError, DBStoreErrorCode
from .config import SqliteConfig
from .database import SqliteDatabase
from ..errors import DatabaseError, DatabaseErrorCode
import sqlite3

LOGGER = logging.getLogger(__name__)

class SqliteBackend(DatabaseBackend):
    def provision(
        self,
        uri: str,
        key_method: Optional[str],
        pass_key: Optional[str],
        profile: Optional[str],
        recreate: bool,
        release_number: str = "release_0",
        schema_config: str = "generic",
        config: Optional[dict] = None
    ):
        """Provision a new SQLite database instance with the specified release number and schema config."""
        LOGGER.debug(
            "[provision_backend] Starting with uri=%s, profile=%s, recreate=%s, release_number=%s, schema_config=%s, config=%s",
            uri, profile, recreate, release_number, schema_config, config
        )
        config_obj = SqliteConfig(uri=uri, encryption_key=pass_key, schema_config=schema_config)
        pool, profile_name, path, effective_release_number = config_obj.provision(
            profile=profile, recreate=recreate, release_number=release_number
        )
        return SqliteDatabase(pool, profile_name, path, effective_release_number)

    def open(
        self,
        uri: str,
        key_method: Optional[str],
        pass_key: Optional[str],
        profile: Optional[str],
        schema_migration: Optional[bool] = None,
        target_schema_release_number: Optional[str] = None,
        schema_config: Optional[str] = None,
        config: Optional[dict] = None
    ):
        """Open an existing SQLite database instance with optional migration."""
        LOGGER.debug(
            "[open_backend] Starting with uri=%s, profile=%s, schema_migration=%s, target_schema_release_number=%s, config=%s",
            uri, profile, schema_migration, target_schema_release_number, config
        )
        config_obj = SqliteConfig(uri=uri, encryption_key=pass_key)
        pool, profile_name, path, effective_release_number = config_obj.open(
            profile=profile, schema_migration=schema_migration, target_schema_release_number=target_schema_release_number
        )
        return SqliteDatabase(pool, profile_name, path, effective_release_number)

    def remove(self, uri: str, release_number: str = "release_0", config: Optional[dict] = None):
        """Remove the SQLite database file."""
        LOGGER.debug("[remove_backend] Starting with uri=%s, release_number=%s, config=%s", uri, release_number, config)
        config_obj = SqliteConfig(uri=uri)
        result = config_obj.remove()
        return result

    def translate_error(self, exception):
        """Translate backend-specific exceptions to DBStoreError."""
        if isinstance(exception, DatabaseError):
            if exception.code == DatabaseErrorCode.DATABASE_NOT_FOUND:
                return DBStoreError(code=DBStoreErrorCode.NOT_FOUND, message="Database Not Found")
            elif exception.code == DatabaseErrorCode.UNSUPPORTED_VERSION:
                return DBStoreError(code=DBStoreErrorCode.UNSUPPORTED, message="Unsupported release number in config table")
            elif exception.code == DatabaseErrorCode.DEFAULT_PROFILE_NOT_FOUND:
                return DBStoreError(code=DBStoreErrorCode.NOT_FOUND, message="Database default profile not found")
            elif exception.code == DatabaseErrorCode.PROFILE_NOT_FOUND:
                return DBStoreError(code=DBStoreErrorCode.NOT_FOUND, message="Database profile not found")
            elif exception.code == DatabaseErrorCode.CONNECTION_POOL_EXHAUSTED:
                return DBStoreError(code=DBStoreErrorCode.UNEXPECTED, message="Connection pool exhausted")
            elif exception.code == DatabaseErrorCode.PROFILE_ALREADY_EXISTS:
                return DBStoreError(code=DBStoreErrorCode.DUPLICATE, message="Profile already exists")
            elif exception.code == DatabaseErrorCode.RECORD_NOT_FOUND:
                return DBStoreError(code=DBStoreErrorCode.NOT_FOUND, message="Record not found")
            elif exception.code == DatabaseErrorCode.DUPLICATE_ITEM_ENTRY_ERROR:
                return DBStoreError(code=DBStoreErrorCode.DUPLICATE, message="Duplicate Item Entry Error")
            elif exception.code == DatabaseErrorCode.DATABASE_NOT_ENCRYPTED:
                return DBStoreError(code=DBStoreErrorCode.UNEXPECTED, message="Cannot rekey an unencrypted database")
            elif exception.code == DatabaseErrorCode.CONNECTION_ERROR:
                return DBStoreError(code=DBStoreErrorCode.UNEXPECTED, message="Connection error")
            elif exception.code == DatabaseErrorCode.QUERY_ERROR:
                return DBStoreError(code=DBStoreErrorCode.UNEXPECTED, message="Query error")
            elif exception.code == DatabaseErrorCode.PROVISION_ERROR:
                return DBStoreError(code=DBStoreErrorCode.UNEXPECTED, message="Provision error")
        elif isinstance(exception, sqlite3.IntegrityError):
            return DBStoreError(code=DBStoreErrorCode.DUPLICATE, message="Duplicate entry")
        elif isinstance(exception, sqlite3.OperationalError):
            return DBStoreError(code=DBStoreErrorCode.BACKEND, message="Database operation failed")
        return DBStoreError(code=DBStoreErrorCode.UNEXPECTED, message="Unexpected error", extra=str(exception))