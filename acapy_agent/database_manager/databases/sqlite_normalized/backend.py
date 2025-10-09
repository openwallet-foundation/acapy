"""Module docstring."""

import logging
import sqlite3
from typing import Optional

from ...dbstore import DatabaseBackend
from ...error import DBStoreError, DBStoreErrorCode
from ..errors import DatabaseError, DatabaseErrorCode
from .config import SqliteConfig
from .database import SqliteDatabase

LOGGER = logging.getLogger(__name__)


class SqliteBackend(DatabaseBackend):
    """SQLite backend implementation for database manager."""

    def provision(
        self,
        uri: str,
        key_method: Optional[str],
        pass_key: Optional[str],
        profile: Optional[str],
        recreate: bool,
        release_number: str = "release_0",
        schema_config: str = "generic",
        config: Optional[dict] = None,
    ):
        """Provision a new SQLite database instance.

        Uses specified release number and schema config.
        """
        LOGGER.debug(
            "[provision_backend] Starting with uri=%s, profile=%s, recreate=%s, "
            "release_number=%s, schema_config=%s, config=%s",
            uri,
            profile,
            recreate,
            release_number,
            schema_config,
            config,
        )
        config_obj = SqliteConfig(
            uri=uri, encryption_key=pass_key, schema_config=schema_config
        )
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
        config: Optional[dict] = None,
    ):
        """Open an existing SQLite database instance with optional migration."""
        LOGGER.debug(
            "[open_backend] Starting with uri=%s, profile=%s, schema_migration=%s, "
            "target_schema_release_number=%s, config=%s",
            uri,
            profile,
            schema_migration,
            target_schema_release_number,
            config,
        )
        config_obj = SqliteConfig(uri=uri, encryption_key=pass_key)
        pool, profile_name, path, effective_release_number = config_obj.open(
            profile=profile,
            schema_migration=schema_migration,
            target_schema_release_number=target_schema_release_number,
        )
        return SqliteDatabase(pool, profile_name, path, effective_release_number)

    def remove(
        self, uri: str, release_number: str = "release_0", config: Optional[dict] = None
    ):
        """Remove the SQLite database file."""
        LOGGER.debug(
            "[remove_backend] Starting with uri=%s, release_number=%s, config=%s",
            uri,
            release_number,
            config,
        )
        config_obj = SqliteConfig(uri=uri)
        result = config_obj.remove()
        return result

    def translate_error(self, exception):
        """Translate backend-specific exceptions to DBStoreError."""
        # Map DatabaseError codes to DBStoreError
        database_error_mapping = {
            DatabaseErrorCode.DATABASE_NOT_FOUND: (
                DBStoreErrorCode.NOT_FOUND,
                "Database Not Found",
            ),
            DatabaseErrorCode.UNSUPPORTED_VERSION: (
                DBStoreErrorCode.UNSUPPORTED,
                "Unsupported release number in config table",
            ),
            DatabaseErrorCode.DEFAULT_PROFILE_NOT_FOUND: (
                DBStoreErrorCode.NOT_FOUND,
                "Database default profile not found",
            ),
            DatabaseErrorCode.PROFILE_NOT_FOUND: (
                DBStoreErrorCode.NOT_FOUND,
                "Database profile not found",
            ),
            DatabaseErrorCode.CONNECTION_POOL_EXHAUSTED: (
                DBStoreErrorCode.UNEXPECTED,
                "Connection pool exhausted",
            ),
            DatabaseErrorCode.PROFILE_ALREADY_EXISTS: (
                DBStoreErrorCode.DUPLICATE,
                "Profile already exists",
            ),
            DatabaseErrorCode.RECORD_NOT_FOUND: (
                DBStoreErrorCode.NOT_FOUND,
                "Record not found",
            ),
            DatabaseErrorCode.DUPLICATE_ITEM_ENTRY_ERROR: (
                DBStoreErrorCode.DUPLICATE,
                "Duplicate Item Entry Error",
            ),
            DatabaseErrorCode.DATABASE_NOT_ENCRYPTED: (
                DBStoreErrorCode.UNEXPECTED,
                "Cannot rekey an unencrypted database",
            ),
            DatabaseErrorCode.CONNECTION_ERROR: (
                DBStoreErrorCode.UNEXPECTED,
                "Connection error",
            ),
            DatabaseErrorCode.QUERY_ERROR: (DBStoreErrorCode.UNEXPECTED, "Query error"),
            DatabaseErrorCode.PROVISION_ERROR: (
                DBStoreErrorCode.UNEXPECTED,
                "Provision error",
            ),
        }

        if isinstance(exception, DatabaseError):
            mapping = database_error_mapping.get(exception.code)
            if mapping:
                return DBStoreError(code=mapping[0], message=mapping[1])
        elif isinstance(exception, sqlite3.IntegrityError):
            return DBStoreError(
                code=DBStoreErrorCode.DUPLICATE, message="Duplicate entry"
            )
        elif isinstance(exception, sqlite3.OperationalError):
            return DBStoreError(
                code=DBStoreErrorCode.BACKEND, message="Database operation failed"
            )

        return DBStoreError(
            code=DBStoreErrorCode.UNEXPECTED,
            message="Unexpected error",
            extra=str(exception),
        )
