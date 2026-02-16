"""Module docstring."""

import importlib
import logging
import os
import sqlite3
from typing import Optional, Tuple

from ...category_registry import RELEASE_ORDER, get_release
from ..errors import DatabaseError, DatabaseErrorCode
from .connection_pool import ConnectionPool

try:
    # Use sqlcipher3 if available (same as connection_pool.py)
    import sqlcipher3

    sqlite3 = sqlcipher3
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)


class SqliteConfig:
    """Configuration for SQLite database connections."""

    def __init__(
        self,
        uri: str = "sqlite://:memory:",
        busy_timeout: float = None,
        pool_size: int = None,
        journal_mode: str = "WAL",
        locking_mode: str = "NORMAL",
        shared_cache: bool = True,
        synchronous: str = "FULL",
        encryption_key: Optional[str] = None,
        schema_config: str = "generic",
    ):
        """Initialize SQLite configuration."""
        self.path = uri.replace("sqlite://", "")
        self.in_memory = self.path == ":memory:"
        self.pool_size = 20 if encryption_key else 100
        self.busy_timeout = 15.0 if encryption_key else 10.0
        if busy_timeout is not None:
            self.busy_timeout = busy_timeout
        self.journal_mode = journal_mode
        self.locking_mode = locking_mode
        self.shared_cache = shared_cache
        self.synchronous = synchronous
        self.encryption_key = encryption_key
        self.schema_config = schema_config

    def provision(
        self,
        profile: Optional[str] = None,
        recreate: bool = False,
        release_number: str = "release_0",
    ) -> Tuple[ConnectionPool, str, str, str]:
        """Provision the SQLite database."""
        if recreate and not self.in_memory:
            try:
                os.remove(self.path)
            except FileNotFoundError:
                pass

        effective_release_number = (
            "release_0" if self.schema_config == "generic" else release_number
        )

        try:
            pool = ConnectionPool(
                db_path=self.path,
                pool_size=self.pool_size,
                busy_timeout=self.busy_timeout,
                encryption_key=self.encryption_key,
                journal_mode=self.journal_mode,
                locking_mode=self.locking_mode,
                synchronous=self.synchronous,
                shared_cache=self.shared_cache,
            )
        except Exception as e:
            LOGGER.error("Failed to create connection pool: %s", str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.CONNECTION_ERROR,
                message="Failed to create connection pool during provisioning",
                actual_error=str(e),
            )

        conn = pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    name TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE,
                    reference TEXT,
                    profile_key TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY,
                    profile_id INTEGER,
                    kind INTEGER,
                    category TEXT,
                    name TEXT,
                    value TEXT,
                    expiry DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (profile_id) REFERENCES profiles (id) 
                ON DELETE CASCADE ON UPDATE CASCADE
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS items_tags (
                    id INTEGER PRIMARY KEY,
                    item_id INTEGER,
                    name TEXT,
                    value TEXT,
                    FOREIGN KEY (item_id) REFERENCES items (id) 
                ON DELETE CASCADE ON UPDATE CASCADE
                )
            """)

            if effective_release_number != "release_0":
                LOGGER.debug(
                    "Loading schema release: %s (type: sqlite)", effective_release_number
                )

                _, schemas, _ = get_release(effective_release_number, "sqlite")

                for category, schema in schemas.items():
                    if category == "default":
                        LOGGER.debug("Skipping default category schema")
                        continue

                    LOGGER.debug(
                        "Processing category=%s with schema=%s", category, schema
                    )
                    if schema is None:
                        LOGGER.warning("Skipping category %s: schema is None", category)
                        continue
                    if not isinstance(schema, dict):
                        LOGGER.error(
                            "Invalid schema type for category %s: expected dict, got %s",
                            category,
                            type(schema),
                        )
                        continue
                    if "sqlite" not in schema:
                        LOGGER.warning(
                            "Skipping category %s: no sqlite schema found in %s",
                            category,
                            schema,
                        )
                        continue

                    LOGGER.debug(
                        "Applying SQLite schema for category %s: %s",
                        category,
                        schema["sqlite"],
                    )
                    for idx, sql in enumerate(schema["sqlite"]):
                        sql_stripped = sql.strip()
                        if not sql_stripped:
                            LOGGER.debug(
                                "Skipping empty SQL [%d] for category '%s'",
                                idx + 1,
                                category,
                            )
                            continue
                        LOGGER.debug(
                            "Executing SQL [%d] for category '%s': %s",
                            idx + 1,
                            category,
                            (
                                sql_stripped[:100] + "..."
                                if len(sql_stripped) > 100
                                else sql_stripped
                            ),
                        )
                        try:
                            cursor.execute(sql_stripped)
                            LOGGER.debug(
                                "Successfully executed SQL [%d] for category '%s'",
                                idx + 1,
                                category,
                            )
                        except sqlite3.OperationalError as e:
                            LOGGER.error(
                                "Failed to apply schema for category '%s' at "
                                "statement [%d]: %s\nSQL: %s",
                                category,
                                idx + 1,
                                str(e),
                                sql_stripped,
                            )
                            raise DatabaseError(
                                code=DatabaseErrorCode.PROVISION_ERROR,
                                message=(
                                    f"Failed to apply schema for category '{category}'"
                                ),
                                actual_error=str(e),
                            )

            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_items_profile_category_name "
                "ON items (profile_id, category, name)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS ix_items_tags_item_id ON items_tags (item_id)"
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_items_expiry ON items (expiry)")
            default_profile = profile or "default_profile"
            cursor.execute(
                "INSERT OR IGNORE INTO config (name, value) "
                "VALUES ('default_profile', ?)",
                (default_profile,),
            )
            cursor.execute(
                "INSERT OR IGNORE INTO config (name, value) VALUES ('key', NULL)"
            )
            cursor.execute(
                "INSERT OR IGNORE INTO config (name, value) "
                "VALUES ('schema_release_number', ?)",
                (effective_release_number,),
            )
            cursor.execute(
                "INSERT OR IGNORE INTO config (name, value) "
                "VALUES ('schema_release_type', 'sqlite')"
            )
            cursor.execute(
                "INSERT OR IGNORE INTO config (name, value) VALUES ('schema_config', ?)",
                (self.schema_config,),
            )
            cursor.execute(
                "INSERT OR IGNORE INTO profiles (name, profile_key) VALUES (?, NULL)",
                (default_profile,),
            )
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_profile_name ON profiles (name);"
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            LOGGER.error("Failed to provision database: %s", str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.PROVISION_ERROR,
                message="Failed to provision database",
                actual_error=str(e),
            )
        finally:
            pool.return_connection(conn)

        return pool, default_profile, self.path, effective_release_number

    def _apply_migrations(
        self, conn, current_release: str, target_release: str, db_type: str = "sqlite"
    ):
        """Apply migrations from current_release to target_release.

        Args:
            conn: Database connection
            current_release: Current schema release
            target_release: Target schema release
            db_type: Database type (sqlite)

        """
        LOGGER.debug(
            f"Applying migrations from release {current_release} to "
            f"{target_release} for {db_type}"
        )
        if current_release == target_release:
            return

        current_index = (
            RELEASE_ORDER.index(current_release)
            if current_release in RELEASE_ORDER
            else -1
        )
        target_index = (
            RELEASE_ORDER.index(target_release) if target_release in RELEASE_ORDER else -1
        )

        if current_index == -1 or target_index == -1 or target_index <= current_index:
            raise DatabaseError(
                code=DatabaseErrorCode.UNSUPPORTED_VERSION,
                message=(
                    f"Invalid migration path from {current_release} to {target_release}"
                ),
            )

        for i in range(current_index, target_index):
            from_release = RELEASE_ORDER[i]
            to_release = RELEASE_ORDER[i + 1]
            try:
                migration_module = importlib.import_module(
                    f"acapy_agent.database_manager.migrations.{db_type}."
                    f"release_{from_release.replace('release_', '')}_to_"
                    f"{to_release.replace('release_', '')}"
                )
                migrate_func = getattr(migration_module, f"migrate_{db_type}", None)
                if not migrate_func:
                    raise ImportError(
                        f"Migration function migrate_{db_type} not found in "
                        f"{from_release} to {to_release}"
                    )
                migrate_func(conn)
                LOGGER.info(
                    f"Applied {db_type} migration from {from_release} to {to_release}"
                )
            except ImportError:
                LOGGER.warning(
                    f"No {db_type} migration script found for {from_release} to "
                    f"{to_release}"
                )
            except Exception as e:
                LOGGER.error(
                    f"{db_type} migration failed from {from_release} to "
                    f"{to_release}: {str(e)}"
                )
                raise DatabaseError(
                    code=DatabaseErrorCode.PROVISION_ERROR,
                    message=(
                        f"{db_type} migration failed from {from_release} to {to_release}"
                    ),
                    actual_error=str(e),
                )

    def open(
        self,
        profile: Optional[str] = None,
        schema_migration: Optional[bool] = None,
        target_schema_release_number: Optional[str] = None,
    ) -> Tuple[ConnectionPool, str, str, str]:
        """Open database connection and validate configuration.

        Args:
            profile: Profile name to use
            schema_migration: Whether schema migration is requested (ignored for SQLite)
            target_schema_release_number: Target schema release number

        Returns:
            Tuple of (connection pool, profile name, db path, release number)

        """
        if not self.in_memory and not os.path.exists(self.path):
            LOGGER.error("Database file not found at %s", self.path)
            raise DatabaseError(
                code=DatabaseErrorCode.DATABASE_NOT_FOUND,
                message=f"Database file does not exist at {self.path}",
            )

        try:
            pool = ConnectionPool(
                db_path=self.path,
                pool_size=self.pool_size,
                busy_timeout=self.busy_timeout,
                encryption_key=self.encryption_key,
                journal_mode=self.journal_mode,
                locking_mode=self.locking_mode,
                synchronous=self.synchronous,
                shared_cache=self.shared_cache,
            )
        except Exception as e:
            LOGGER.error("Failed to create connection pool: %s", str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.CONNECTION_ERROR,
                message="Failed to create connection pool during open",
                actual_error=str(e),
            )

        conn = pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM config WHERE name = 'schema_release_number'"
            )
            release_row = cursor.fetchone()
            db_current_release = release_row[0] if release_row else None
            if not db_current_release:
                LOGGER.error("Release number not found in config table")
                raise DatabaseError(
                    code=DatabaseErrorCode.UNSUPPORTED_VERSION,
                    message="Release number not found in config table",
                )
            effective_release_number = db_current_release

            cursor.execute("SELECT value FROM config WHERE name = 'default_profile'")
            default_profile_row = cursor.fetchone()
            if not default_profile_row:
                LOGGER.error("Default profile not found")
                raise DatabaseError(
                    code=DatabaseErrorCode.DEFAULT_PROFILE_NOT_FOUND,
                    message="Default profile not found in the database",
                )
            default_profile = default_profile_row[0]
            profile_name = profile or default_profile
            cursor.execute("SELECT id FROM profiles WHERE name = ?", (profile_name,))
            if not cursor.fetchone():
                LOGGER.error("Profile '%s' not found", profile_name)
                raise DatabaseError(
                    code=DatabaseErrorCode.PROFILE_NOT_FOUND,
                    message=f"Profile '{profile_name}' not found",
                )
            cursor.execute("SELECT value FROM config WHERE name = 'schema_config'")
            schema_config_row = cursor.fetchone()
            self.schema_config = schema_config_row[0] if schema_config_row else "generic"

            # Enforce generic schema uses release_0
            if self.schema_config == "generic" and db_current_release != "release_0":
                LOGGER.error(
                    "Invalid configuration: schema_config='generic' but "
                    "schema_release_number='%s'",
                    db_current_release,
                )
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=(
                        f"Invalid configuration: schema_config='generic' requires "
                        f"schema_release_number='release_0', found '{db_current_release}'"
                    ),
                )

            # Enforce normalize schema matches target_schema_release_number
            if (
                self.schema_config == "normalize"
                and target_schema_release_number
                and db_current_release != target_schema_release_number
            ):
                LOGGER.error(
                    "Schema release number mismatch: database has '%s', but "
                    "target is '%s'",
                    db_current_release,
                    target_schema_release_number,
                )
                raise DatabaseError(
                    code=DatabaseErrorCode.UNSUPPORTED_VERSION,
                    message=(
                        f"Schema release number mismatch: database has "
                        f"'{db_current_release}', but target is "
                        f"'{target_schema_release_number}'. Please perform an upgrade."
                    ),
                )

        except Exception as e:
            LOGGER.error("Failed to query database configuration: %s", str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message="Failed to query database configuration",
                actual_error=str(e),
            )
        finally:
            pool.return_connection(conn)

        return pool, profile_name, self.path, effective_release_number

    def remove(self) -> bool:
        """Remove the database file.

        Returns:
            True if successful or in-memory database

        """
        if self.in_memory:
            return True
        try:
            os.remove(self.path)
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            LOGGER.error("Failed to remove database file: %s", str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.CONNECTION_ERROR,
                message="Failed to remove database file",
                actual_error=str(e),
            )
