"""Module docstring."""

import logging
import urllib.parse
from typing import Optional

from psycopg import errors as psycopg_errors

from ...dbstore import register_backend
from ...error import DBStoreError, DBStoreErrorCode
from ..errors import DatabaseError, DatabaseErrorCode
from .config import PostgresConfig
from .database import PostgresDatabase

LOGGER = logging.getLogger(__name__)


# Maps for compact error translation to reduce branching complexity
DB_ERROR_MAP = {
    DatabaseErrorCode.DATABASE_NOT_FOUND: (
        DBStoreErrorCode.NOT_FOUND,
        "Database Not Found",
    ),
    DatabaseErrorCode.PROFILE_NOT_FOUND: (
        DBStoreErrorCode.NOT_FOUND,
        "Database profile not found",
    ),
    DatabaseErrorCode.UNSUPPORTED_VERSION: (
        DBStoreErrorCode.UNSUPPORTED,
        "Unsupported release number in config table",
    ),
    DatabaseErrorCode.DEFAULT_PROFILE_NOT_FOUND: (
        DBStoreErrorCode.NOT_FOUND,
        "Database default profile not found",
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
    DatabaseErrorCode.QUERY_ERROR: (
        DBStoreErrorCode.UNEXPECTED,
        "Query error",
    ),
    DatabaseErrorCode.PROVISION_ERROR: (
        DBStoreErrorCode.UNEXPECTED,
        "Provision error",
    ),
}


class PostgresqlBackend:
    """PostgreSQL backend implementation for database manager."""

    async def provision(
        self,
        uri: str,
        _key_method: Optional[str],
        _pass_key: Optional[str],
        profile: Optional[str],
        recreate: bool,
        release_number: str,
        schema_config: Optional[str] = None,
        config: Optional[dict] = None,
    ):
        """Provision a new PostgreSQL database."""
        LOGGER.debug(
            "[provision_backend] uri=%s, profile=%s, recreate=%s, "
            "release_number=%s, schema_config=%s, config=%s",
            uri,
            profile,
            recreate,
            release_number,
            schema_config,
            config,
        )
        config = config or {}
        parsed_uri = urllib.parse.urlparse(uri)
        query_params = urllib.parse.parse_qs(parsed_uri.query)
        min_size = int(
            config.get("min_connections", query_params.get("min_connections", [4])[0])
        )
        max_size = int(
            config.get("max_connections", query_params.get("max_connections", [10])[0])
        )
        timeout = float(
            config.get("connect_timeout", query_params.get("connect_timeout", [30.0])[0])
        )
        max_idle = float(config.get("max_idle", query_params.get("max_idle", [5.0])[0]))
        max_lifetime = float(
            config.get("max_lifetime", query_params.get("max_lifetime", [3600.0])[0])
        )
        max_sessions = int(
            config.get(
                "max_sessions",
                query_params.get("max_sessions", [None])[0] or max_size * 0.75,
            )
        )
        config_obj = PostgresConfig(
            uri=uri,
            min_size=min_size,
            max_size=max_size,
            timeout=timeout,
            max_idle=max_idle,
            max_lifetime=max_lifetime,
            schema_config=schema_config or "generic",
        )
        (
            pool,
            profile_name,
            conn_str,
            effective_release_number,
        ) = await config_obj.provision(
            profile=profile, recreate=recreate, release_number=release_number
        )
        return PostgresDatabase(
            pool,
            profile_name,
            conn_str,
            effective_release_number,
            max_sessions=max_sessions,
            min_size=min_size,
            max_size=max_size,
            timeout=timeout,
            max_idle=max_idle,
            max_lifetime=max_lifetime,
            schema_context=config_obj.schema_context,
            backend=self,
        )

    async def open(
        self,
        uri: str,
        _key_method: Optional[str],
        _pass_key: Optional[str],
        profile: Optional[str],
        schema_migration: Optional[bool] = None,
        target_schema_release_number: Optional[str] = None,
        config: Optional[dict] = None,
    ):
        """Open an existing PostgreSQL database."""
        LOGGER.debug(
            "[open_backend] uri=%s, profile=%s, schema_migration=%s, "
            "target_schema_release_number=%s, config=%s, "
            "schema_config will be retrieved from database",
            uri,
            profile,
            schema_migration,
            target_schema_release_number,
            config,
        )
        config = config or {}
        parsed_uri = urllib.parse.urlparse(uri)
        query_params = urllib.parse.parse_qs(parsed_uri.query)
        min_size = int(
            config.get("min_connections", query_params.get("min_connections", [4])[0])
        )
        max_size = int(
            config.get("max_connections", query_params.get("max_connections", [10])[0])
        )
        timeout = float(
            config.get("connect_timeout", query_params.get("connect_timeout", [30.0])[0])
        )
        max_idle = float(config.get("max_idle", query_params.get("max_idle", [5.0])[0]))
        max_lifetime = float(
            config.get("max_lifetime", query_params.get("max_lifetime", [3600.0])[0])
        )
        max_sessions = int(
            config.get(
                "max_sessions",
                query_params.get("max_sessions", [None])[0] or max_size * 0.75,
            )
        )
        config_obj = PostgresConfig(
            uri=uri,
            min_size=min_size,
            max_size=max_size,
            timeout=timeout,
            max_idle=max_idle,
            max_lifetime=max_lifetime,
        )
        pool, profile_name, conn_str, effective_release_number = await config_obj.open(
            profile=profile,
            schema_migration=schema_migration,
            target_schema_release_number=target_schema_release_number,
        )
        return PostgresDatabase(
            pool,
            profile_name,
            conn_str,
            effective_release_number,
            max_sessions=max_sessions,
            min_size=min_size,
            max_size=max_size,
            timeout=timeout,
            max_idle=max_idle,
            max_lifetime=max_lifetime,
            schema_context=config_obj.schema_context,
            backend=self,
        )

    async def remove(self, uri: str, config: Optional[dict] = None):
        """Remove a PostgreSQL database."""
        LOGGER.debug("[remove_backend] Starting with uri=%s, config=%s", uri, config)
        config = config or {}
        parsed_uri = urllib.parse.urlparse(uri)
        query_params = urllib.parse.parse_qs(parsed_uri.query)
        min_size = int(
            config.get("min_connections", query_params.get("min_connections", [4])[0])
        )
        max_size = int(
            config.get("max_connections", query_params.get("max_connections", [10])[0])
        )
        timeout = float(
            config.get("connect_timeout", query_params.get("connect_timeout", [30.0])[0])
        )
        max_idle = float(config.get("max_idle", query_params.get("max_idle", [5.0])[0]))
        max_lifetime = float(
            config.get("max_lifetime", query_params.get("max_lifetime", [3600.0])[0])
        )
        config_obj = PostgresConfig(
            uri=uri,
            min_size=min_size,
            max_size=max_size,
            timeout=timeout,
            max_idle=max_idle,
            max_lifetime=max_lifetime,
            schema_config="generic",
        )
        result = await config_obj.remove()
        return result

    def translate_error(self, error: Exception) -> DBStoreError:
        """Translate database errors to DBStoreError."""
        LOGGER.debug("Translating error: %s, type=%s", str(error), type(error))
        if isinstance(error, DatabaseError):
            mapped = DB_ERROR_MAP.get(error.code)
            if mapped:
                return DBStoreError(code=mapped[0], message=mapped[1])
        elif isinstance(error, psycopg_errors.UniqueViolation):
            return DBStoreError(
                code=DBStoreErrorCode.DUPLICATE, message=f"Duplicate entry: {str(error)}"
            )
        elif isinstance(error, psycopg_errors.ForeignKeyViolation):
            return DBStoreError(
                code=DBStoreErrorCode.UNEXPECTED,
                message=f"Foreign key violation: {str(error)}",
            )
        elif isinstance(error, psycopg_errors.OperationalError):
            return DBStoreError(
                code=DBStoreErrorCode.BACKEND,
                message=f"Database operation failed: {str(error)}",
            )
        elif isinstance(error, TypeError):
            return DBStoreError(
                code=DBStoreErrorCode.UNEXPECTED,
                message=f"Configuration error: {str(error)}",
            )
        return DBStoreError(
            code=DBStoreErrorCode.UNEXPECTED, message=f"Unexpected error: {str(error)}"
        )


register_backend("postgresql", PostgresqlBackend())
