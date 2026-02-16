"""Module docstring."""

import asyncio
import importlib
import logging
import urllib.parse
from typing import Optional, Tuple

import psycopg.pq as pq
from psycopg.sql import SQL, Identifier
from psycopg_pool import AsyncConnectionPool

from ...category_registry import RELEASE_ORDER, get_release
from ..errors import DatabaseError, DatabaseErrorCode
from .connection_pool import PostgresConnectionPool
from .schema_context import SchemaContext

LOGGER = logging.getLogger(__name__)


# Common SQL and error message constants
SQL_SELECT_DB_EXISTS = "SELECT 1 FROM pg_database WHERE datname = %s"
SQL_DROP_TABLE_IF_EXISTS = "DROP TABLE IF EXISTS"
SQL_DROP_TABLE = "DROP TABLE"
ERR_NO_DB_IN_CONN_STR = "No database name specified in connection string"


class PostgresConfig:
    """Configuration for PostgreSQL database connections."""

    def __init__(
        self,
        uri: str,
        min_size: int = None,
        max_size: int = None,
        timeout: float = None,
        max_idle: float = None,
        max_lifetime: float = None,
        schema_config: Optional[str] = None,
        release_number: Optional[str] = None,
    ):
        """Initialize PostgreSQL configuration."""
        parsed = urllib.parse.urlparse(uri)
        query_params = urllib.parse.parse_qs(parsed.query)
        valid_params = {
            "connect_timeout",
            "sslmode",
            "sslcert",
            "sslkey",
            "sslrootcert",
            "admin_account",
            "admin_password",
        }
        for param in query_params:
            if param not in valid_params:
                LOGGER.warning(
                    "Invalid URI query parameter '%s' in uri, will be ignored", param
                )
        self.conn_str = uri
        self.min_size = (
            min_size
            if min_size is not None
            else int(query_params.get("min_connections", [4])[0])
        )
        self.max_size = (
            max_size
            if max_size is not None
            else int(query_params.get("max_connections", [10])[0])
        )
        self.timeout = (
            timeout
            if timeout is not None
            else float(query_params.get("connect_timeout", [30.0])[0])
        )
        self.max_idle = (
            max_idle
            if max_idle is not None
            else float(query_params.get("max_idle", [5.0])[0])
        )
        self.max_lifetime = (
            max_lifetime
            if max_lifetime is not None
            else float(query_params.get("max_lifetime", [3600.0])[0])
        )
        self.schema_config = schema_config  # Used in provision, overwritten in open
        self.release_number = release_number

        self.schema_context = SchemaContext(
            parsed.username
        )  # starting point here:  Initialize SchemaContext with username from URI

    def _get_default_conn_str(self) -> str:
        parsed = urllib.parse.urlparse(self.conn_str)
        db_name = parsed.path.lstrip("/")
        if db_name:
            new_path = "/postgres"
            new_conn_str = parsed._replace(path=new_path).geturl()
            LOGGER.debug(f"Replaced database {db_name} with postgres: {new_conn_str}")
            return new_conn_str
        return parsed._replace(path="/postgres").geturl()

    # Helpers to reduce complexity in DROP statement handling
    def _is_valid_drop_sql(self, sql: str) -> bool:
        up = sql.upper().lstrip()
        return (
            up.startswith(SQL_DROP_TABLE)
            or up.startswith("DROP INDEX")
            or up.startswith("DROP TRIGGER")
            or up.startswith("DROP FUNCTION")
        )

    def _qualify_drop_sql(self, sql: str) -> str:
        up = sql.upper()
        if up.startswith(SQL_DROP_TABLE):
            table_name = sql.split(f"{SQL_DROP_TABLE_IF_EXISTS} ")[-1].split()[0].strip()
            return sql.replace(
                f"{SQL_DROP_TABLE_IF_EXISTS} {table_name}",
                (
                    f"{SQL_DROP_TABLE_IF_EXISTS} "
                    f"{self.schema_context.qualify_table(table_name)}"
                ),
            )
        if up.startswith("DROP INDEX"):
            index_name = sql.split("DROP INDEX IF EXISTS ")[-1].split()[0].strip()
            return sql.replace(
                f"DROP INDEX IF EXISTS {index_name}",
                (f"DROP INDEX IF EXISTS {self.schema_context.qualify_table(index_name)}"),
            )
        if up.startswith("DROP TRIGGER"):
            return sql.replace(" ON ", f" ON {self.schema_context}.")
        if up.startswith("DROP FUNCTION"):
            function_name = sql.split("IF EXISTS")[-1].split("CASCADE")[0].strip()
            return sql.replace(
                f"IF EXISTS {function_name}",
                f"IF EXISTS {self.schema_context}.{function_name}",
            )
        return sql

    def _is_redundant_drop(self, modified_sql: str, dropped_tables: set) -> bool:
        if SQL_DROP_TABLE not in modified_sql.upper():
            return False
        try:
            table_name = modified_sql.split(SQL_DROP_TABLE_IF_EXISTS)[-1].split()[0]
            table_name = table_name.strip(";").split(".")[-1]
        except Exception:
            for table in dropped_tables:
                if table in modified_sql:
                    return True
            return False
        return table_name in dropped_tables

    async def _read_config_values_from_conn(
        self,
        conn,
        schema_name: str,
        fallback_release_number: str,
    ) -> Tuple[str, str, str, Optional[str]]:
        """Read schema config, release number/type, and default profile.

        Returns (schema_config, schema_release_number, schema_release_type,
        default_profile).
        Uses provided fallback_release_number when the value is not found.
        """
        async with conn.cursor() as cursor:
            await cursor.execute(f"SET search_path TO {schema_name}, public")

            await cursor.execute(
                f"SELECT value FROM "
                f"{self.schema_context.qualify_table('config')} "
                f"WHERE name = 'schema_config'"
            )
            schema_config_row = await cursor.fetchone()
            schema_config = (
                schema_config_row[0] if schema_config_row else self.schema_config
            )

            await cursor.execute(
                f"SELECT value FROM "
                f"{self.schema_context.qualify_table('config')} "
                f"WHERE name = 'schema_release_number'"
            )
            schema_release_number_row = await cursor.fetchone()
            schema_release_number = (
                schema_release_number_row[0]
                if schema_release_number_row
                else fallback_release_number
            )

            await cursor.execute(
                f"SELECT value FROM "
                f"{self.schema_context.qualify_table('config')} "
                f"WHERE name = 'schema_release_type'"
            )
            schema_release_type_row = await cursor.fetchone()
            schema_release_type = (
                schema_release_type_row[0] if schema_release_type_row else "postgresql"
            )

            await cursor.execute(
                f"SELECT value FROM "
                f"{self.schema_context.qualify_table('config')} "
                f"WHERE name = 'default_profile'"
            )
            default_profile_row = await cursor.fetchone()
            default_profile = default_profile_row and default_profile_row[0]

        return schema_config, schema_release_number, schema_release_type, default_profile

    async def _apply_migrations(
        self, conn, current_release: str, target_release: str, db_type: str = "postgresql"
    ):
        LOGGER.debug(
            "Applying migrations from release %s to %s for %s",
            current_release,
            target_release,
            db_type,
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
                await migrate_func(conn)
                LOGGER.info(
                    f"Applied {db_type} migration from {from_release} to {to_release}"
                )
            except ImportError:
                LOGGER.warning(
                    f"No {db_type} migration script found for "
                    f"{from_release} to {to_release}"
                )
            except Exception as e:
                LOGGER.error(
                    f"{db_type} migration failed from {from_release} to {to_release}: %s",
                    str(e),
                )
                raise DatabaseError(
                    code=DatabaseErrorCode.PROVISION_ERROR,
                    message=(
                        f"{db_type} migration failed from {from_release} to {to_release}"
                    ),
                    actual_error=str(e),
                )

    async def _drop_tables(
        self,
        target_db: str,
        schema_config: str,
        release_number: str,
        schema_release_type: str,
    ):
        target_pool = PostgresConnectionPool(
            conn_str=f"{self.conn_str}",
            min_size=1,
            max_size=1,
            timeout=self.timeout,
            max_idle=self.max_idle,
            max_lifetime=self.max_lifetime,
        )
        await target_pool.initialize()
        target_conn = None
        try:
            target_conn = await target_pool.getconn()
            await target_conn.rollback()
            await target_conn.set_autocommit(True)
            async with target_conn.cursor() as cursor:
                core_tables = ["config", "profiles", "items", "items_tags"]
                for table in core_tables:
                    try:
                        LOGGER.debug(
                            "Dropping core table %s",
                            self.schema_context.qualify_table(table),
                        )
                        await cursor.execute(
                            f"{SQL_DROP_TABLE_IF_EXISTS} "
                            f"{self.schema_context.qualify_table(table)} CASCADE"
                        )
                        LOGGER.debug(
                            "Successfully dropped table %s",
                            self.schema_context.qualify_table(table),
                        )
                    except Exception as e:
                        LOGGER.error(
                            "Failed to drop table %s: %s",
                            self.schema_context.qualify_table(table),
                            str(e),
                        )
                        raise DatabaseError(
                            code=DatabaseErrorCode.QUERY_ERROR,
                            message=(
                                f"Failed to drop table "
                                f"{self.schema_context.qualify_table(table)}"
                            ),
                            actual_error=str(e),
                        )

                if schema_config != "generic":
                    _, _, drop_schemas = get_release(release_number, schema_release_type)
                    dropped_tables = set(core_tables)
                    for category in drop_schemas:  # iterate over drop_schemas.keys()
                        LOGGER.debug("Processing drop schemas for category %s", category)
                        category_drop = drop_schemas.get(category)
                        if category_drop and category_drop.get(schema_release_type):
                            drop_statements = category_drop[
                                schema_release_type
                            ]  # Get the list for this db_type
                            LOGGER.debug(
                                "DROP_SCHEMAS for category %s: %s",
                                category,
                                drop_statements,
                            )
                            for sql in drop_statements:
                                if not self._is_valid_drop_sql(sql):
                                    LOGGER.debug(
                                        "Skipping non-drop statement for category %s: %s",
                                        category,
                                        sql,
                                    )
                                    continue

                                modified_sql = self._qualify_drop_sql(sql)

                                if self._is_redundant_drop(modified_sql, dropped_tables):
                                    LOGGER.debug(
                                        "Skipping redundant drop statement for "
                                        "category %s: %s",
                                        category,
                                        modified_sql,
                                    )
                                    continue
                                try:
                                    LOGGER.debug(
                                        "Executing drop statement for category %s: %s",
                                        category,
                                        modified_sql,
                                    )
                                    await cursor.execute(modified_sql)
                                    LOGGER.debug(
                                        "Successfully executed drop statement for "
                                        "category %s: %s",
                                        category,
                                        modified_sql,
                                    )
                                    if SQL_DROP_TABLE in modified_sql.upper():
                                        table_name = (
                                            modified_sql.split(SQL_DROP_TABLE_IF_EXISTS)[
                                                -1
                                            ]
                                            .split()[0]
                                            .strip(";")
                                            .split(".")[-1]
                                        )
                                        dropped_tables.add(table_name)
                                except Exception as e:
                                    LOGGER.error(
                                        "Error executing drop statement for "
                                        "category %s: %s",
                                        category,
                                        str(e),
                                    )
                                    raise DatabaseError(
                                        code=DatabaseErrorCode.QUERY_ERROR,
                                        message=(
                                            "Failed to execute drop statement for "
                                            f"category {category}: {modified_sql}"
                                        ),
                                        actual_error=str(e),
                                    )
                        else:
                            LOGGER.debug(
                                "No DROP_SCHEMAS found for category %s", category
                            )
                await target_conn.commit()
        except Exception as e:
            LOGGER.error("Failed to drop tables in %s: %s", target_db, str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.PROVISION_ERROR,
                message=f"Failed to drop tables in {target_db}",
                actual_error=str(e),
            )
        finally:
            if target_conn:
                await target_pool.putconn(target_conn)
            await target_pool.close()

    async def _check_and_create_database(
        self, target_db: str, recreate: bool, profile: Optional[str], release_number: str
    ) -> Tuple[str, Optional[str], bool]:
        LOGGER.debug(
            "Entering _check_and_create_database with target_db=%s, "
            "recreate=%s, profile=%s, release_number=%s",
            target_db,
            recreate,
            profile,
            release_number,
        )
        default_conn_str = self._get_default_conn_str()
        pool_temp = PostgresConnectionPool(
            conn_str=default_conn_str,
            min_size=1,
            max_size=1,
            timeout=self.timeout,
            max_idle=self.max_idle,
            max_lifetime=self.max_lifetime,
        )
        try:
            await pool_temp.initialize()
        except Exception as e:
            LOGGER.error("Failed to initialize temporary connection pool: %s", str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.CONNECTION_ERROR,
                message="Failed to initialize connection pool for 'postgres' database",
                actual_error=str(e),
            )

        conn = None
        default_profile = profile or "default_profile"
        schema_release_number = release_number
        skip_create_tables = False

        try:
            conn = await pool_temp.getconn()
            if conn.pgconn.transaction_status != pq.TransactionStatus.IDLE:
                await conn.rollback()
            await conn.set_autocommit(True)

            async with conn.cursor() as cursor:
                schema_name = str(self.schema_context)
                await cursor.execute(
                    "SELECT rolsuper, rolcreatedb FROM pg_roles WHERE rolname = %s",
                    (schema_name,),
                )
                role_info = await cursor.fetchone()
                if not role_info:
                    LOGGER.error("User %s not found in pg_roles", schema_name)
                    raise DatabaseError(
                        code=DatabaseErrorCode.PERMISSION_ERROR,
                        message=f"User {schema_name} not found",
                    )
                is_superuser, can_create_db = role_info
                if not (is_superuser or can_create_db):
                    LOGGER.error("User %s lacks CREATEDB privilege", schema_name)
                    raise DatabaseError(
                        code=DatabaseErrorCode.PERMISSION_ERROR,
                        message=f"User {schema_name} lacks CREATEDB privilege",
                    )

                await cursor.execute(f"SET search_path TO {schema_name}, public")
                await cursor.execute(SQL_SELECT_DB_EXISTS, (target_db,))
                db_exists = await cursor.fetchone()

                if db_exists and not recreate:
                    # Database exists and recreate=False: check config and
                    # skip table creation
                    target_pool = PostgresConnectionPool(
                        conn_str=self.conn_str,
                        min_size=1,
                        max_size=1,
                        timeout=self.timeout,
                        max_idle=self.max_idle,
                        max_lifetime=self.max_lifetime,
                    )
                    await target_pool.initialize()
                    target_conn = None
                    try:
                        target_conn = await target_pool.getconn()
                        if (
                            target_conn.pgconn.transaction_status
                            != pq.TransactionStatus.IDLE
                        ):
                            await target_conn.rollback()
                        await target_conn.set_autocommit(True)

                        (
                            schema_config,
                            schema_release_number,
                            schema_release_type,
                            default_profile_db,
                        ) = await self._read_config_values_from_conn(
                            target_conn, schema_name, release_number
                        )

                        if default_profile_db:
                            profile_name = profile or default_profile_db
                            if profile_name != default_profile_db:
                                raise DatabaseError(
                                    code=DatabaseErrorCode.PROFILE_NOT_FOUND,
                                    message=(
                                        f"Profile '{profile_name}' does not match "
                                        f"default profile '{default_profile_db}'"
                                    ),
                                )

                        # Since recreate=False and database exists, skip table creation
                        skip_create_tables = True
                    except Exception as e:
                        error_message = str(e).lower()
                        if (
                            "does not exist" in error_message
                            and "config" in error_message
                        ):
                            LOGGER.debug(
                                "Config table not found. Assuming database needs "
                                "initialization."
                            )
                        else:
                            LOGGER.warning(
                                "Failed to verify default profile or schema in %s: %s",
                                target_db,
                                str(e),
                            )
                    finally:
                        if target_conn:
                            await target_pool.putconn(target_conn)
                        await target_pool.close()

                elif db_exists and recreate:
                    schema_config = self.schema_config
                    schema_release_number = release_number
                    schema_release_type = "postgresql"
                    default_profile_db = None

                    target_pool = PostgresConnectionPool(
                        conn_str=self.conn_str,
                        min_size=1,
                        max_size=1,
                        timeout=self.timeout,
                        max_idle=self.max_idle,
                        max_lifetime=self.max_lifetime,
                    )
                    await target_pool.initialize()
                    target_conn = None
                    try:
                        target_conn = await target_pool.getconn()
                        if (
                            target_conn.pgconn.transaction_status
                            != pq.TransactionStatus.IDLE
                        ):
                            await target_conn.rollback()
                        await target_conn.set_autocommit(True)
                        (
                            schema_config,
                            schema_release_number,
                            schema_release_type,
                            default_profile_db,
                        ) = await self._read_config_values_from_conn(
                            target_conn, schema_name, release_number
                        )
                        if default_profile_db:
                            profile_name = profile or default_profile_db
                            if profile_name != default_profile_db:
                                raise DatabaseError(
                                    code=DatabaseErrorCode.PROFILE_NOT_FOUND,
                                    message=(
                                        f"Profile '{profile_name}' does not match "
                                        f"default profile '{default_profile_db}'"
                                    ),
                                )
                    except Exception as e:
                        error_message = str(e).lower()
                        if (
                            "does not exist" in error_message
                            and "config" in error_message
                        ):
                            LOGGER.debug(
                                "Config table not found. Skipping default profile check."
                            )
                        else:
                            LOGGER.warning(
                                "Failed to verify default profile in %s: %s",
                                target_db,
                                str(e),
                            )
                    finally:
                        if target_conn:
                            await target_pool.putconn(target_conn)
                        await target_pool.close()

                    await conn.set_autocommit(True)
                    try:
                        await self._drop_tables(
                            target_db,
                            schema_config,
                            schema_release_number,
                            schema_release_type,
                        )
                    except Exception as e:
                        LOGGER.error("Failed to drop tables in %s: %s", target_db, str(e))
                        raise DatabaseError(
                            code=DatabaseErrorCode.PROVISION_ERROR,
                            message=f"Failed to drop tables in {target_db}",
                            actual_error=str(e),
                        )

                if not db_exists:
                    # Create new database
                    await cursor.execute(
                        SQL("CREATE DATABASE {}").format(Identifier(target_db))
                    )
                    await conn.commit()

                    max_retries = 5
                    retry_delay = 0.5
                    for attempt in range(max_retries):
                        await cursor.execute(SQL_SELECT_DB_EXISTS, (target_db,))
                        verify_db_exists = await cursor.fetchone()
                        if verify_db_exists:
                            break
                        if attempt < max_retries - 1:
                            LOGGER.debug(
                                "Database %s not yet visible, retrying after %s seconds",
                                target_db,
                                retry_delay,
                            )
                            await asyncio.sleep(retry_delay)
                    else:
                        raise DatabaseError(
                            code=DatabaseErrorCode.PROVISION_ERROR,
                            message=(
                                f"Database {target_db} creation failed or not visible "
                                f"after {max_retries} attempts"
                            ),
                        )

                    schema_pool = PostgresConnectionPool(
                        conn_str=self.conn_str,
                        min_size=1,
                        max_size=1,
                        timeout=self.timeout,
                        max_idle=self.max_idle,
                        max_lifetime=self.max_lifetime,
                    )
                    try:
                        await schema_pool.initialize()
                        new_conn = await schema_pool.getconn()
                        try:
                            if (
                                new_conn.pgconn.transaction_status
                                != pq.TransactionStatus.IDLE
                            ):
                                await new_conn.rollback()
                            await new_conn.set_autocommit(True)
                            async with new_conn.cursor() as cursor:
                                schema_name = str(self.schema_context)
                                await cursor.execute(
                                    f"CREATE SCHEMA IF NOT EXISTS {schema_name}"
                                )
                                await cursor.execute(
                                    f"GRANT ALL ON SCHEMA {schema_name} TO {schema_name}"
                                )
                                await new_conn.commit()
                        finally:
                            await schema_pool.putconn(new_conn)
                    finally:
                        await schema_pool.close()

        except Exception as e:
            LOGGER.error("Failed to check or create database %s: %s", target_db, str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.PROVISION_ERROR,
                message=f"Failed to check or create database {target_db}",
                actual_error=str(e),
            )
        finally:
            if conn:
                await pool_temp.putconn(conn)
            if pool_temp:
                await pool_temp.close()

        return default_profile, schema_release_number, skip_create_tables

    async def _create_tables(
        self,
        pool: AsyncConnectionPool,
        default_profile: str,
        effective_release_number: str,
    ) -> None:
        conn = await pool.getconn()
        try:
            async with conn.cursor() as cursor:
                await self._setup_schema(cursor)
                await self._create_core_tables(cursor)
                await self._apply_release_schemas(cursor, effective_release_number)
                await self._insert_configuration_data(
                    cursor, default_profile, effective_release_number
                )
                await conn.commit()
        except Exception as e:
            await conn.rollback()
            LOGGER.error("Failed to provision database: %s", str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.PROVISION_ERROR,
                message="Failed to provision database",
                actual_error=str(e),
            )
        finally:
            await pool.putconn(conn)

    async def _setup_schema(self, cursor) -> None:
        """Set up the database schema and permissions."""
        await cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema_context}")
        await cursor.execute(
            f"GRANT ALL ON SCHEMA {self.schema_context} TO {self.schema_context}"
        )
        LOGGER.debug("Created and granted permissions on schema %s", self.schema_context)
        await cursor.execute(f"SET search_path TO {self.schema_context}, public")

    async def _create_core_tables(self, cursor) -> None:
        """Create the core database tables."""
        await cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.schema_context.qualify_table("config")} (
                name TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.schema_context.qualify_table("profiles")} (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE,
                reference TEXT,
                profile_key TEXT
            )
        """)
        await cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.schema_context.qualify_table("items")} (
                id SERIAL PRIMARY KEY,
                profile_id INTEGER,
                kind INTEGER,
                category TEXT,
                name TEXT,
                value TEXT,
                expiry TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (profile_id) REFERENCES {
            self.schema_context.qualify_table("profiles")
        } (id) ON DELETE CASCADE ON UPDATE CASCADE
            )
        """)
        await cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.schema_context.qualify_table("items_tags")} (
                id SERIAL PRIMARY KEY,
                item_id INTEGER,
                name TEXT,
                value TEXT,
                FOREIGN KEY (item_id) REFERENCES {
            self.schema_context.qualify_table("items")
        } (id) ON DELETE CASCADE ON UPDATE CASCADE
            )
        """)

    async def _apply_release_schemas(self, cursor, effective_release_number: str) -> None:
        """Apply schemas for the specified release number."""
        LOGGER.debug(
            "_create_tables called with effective_release_number=%s",
            effective_release_number,
        )

        if effective_release_number == "release_0":
            return

        _, schemas, _ = get_release(effective_release_number, "postgresql")
        for category, schema in schemas.items():
            await self._process_category_schema(cursor, category, schema)

    async def _process_category_schema(self, cursor, category: str, schema) -> None:
        """Process and apply schema for a specific category."""
        LOGGER.debug("Processing category=%s with schema=%s", category, schema)

        if schema is None:
            LOGGER.warning("Skipping category %s: schema is None", category)
            return

        if not isinstance(schema, dict):
            LOGGER.error(
                "Invalid schema type for category %s: expected dict, got %s",
                category,
                type(schema),
            )
            return

        if "postgresql" not in schema:
            LOGGER.warning(
                "Skipping category %s: no postgresql schema found in %s",
                category,
                schema,
            )
            return

        LOGGER.debug(
            "Applying PostgreSQL schema for category %s: %s",
            category,
            schema["postgresql"],
        )

        for sql in schema["postgresql"]:
            await self._execute_schema_sql(cursor, category, sql)

    async def _execute_schema_sql(self, cursor, category: str, sql: str) -> None:
        """Execute a single schema SQL statement."""
        modified_sql = self._qualify_create_statement(sql)
        try:
            LOGGER.debug("Executing create statement for category %s", category)
            await cursor.execute(modified_sql)
        except Exception as e:
            LOGGER.error(
                "Failed to execute SQL for category %s: %s, SQL: %s",
                category,
                str(e),
                modified_sql,
            )
            raise DatabaseError(
                code=DatabaseErrorCode.PROVISION_ERROR,
                message=f"Failed to apply schema for category {category}",
                actual_error=str(e),
            )

    async def _insert_configuration_data(
        self, cursor, default_profile: str, effective_release_number: str
    ) -> None:
        """Insert configuration data and create indexes."""
        await self._ensure_core_indexes(cursor)

        config_data = [
            ("default_profile", default_profile),
            ("key", None),
            ("schema_release_number", effective_release_number),
            ("schema_release_type", "postgresql"),
            ("schema_config", self.schema_config),
        ]

        for name, value in config_data:
            await cursor.execute(
                (
                    f"INSERT INTO {self.schema_context.qualify_table('config')} "
                    f"(name, value) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING"
                ),
                (name, value),
            )

        await cursor.execute(
            (
                f"INSERT INTO {self.schema_context.qualify_table('profiles')} "
                f"(name, profile_key) VALUES (%s, NULL) "
                f"ON CONFLICT (name) DO NOTHING"
            ),
            (default_profile,),
        )
        await cursor.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS ix_profile_name "
            f"ON {self.schema_context.qualify_table('profiles')} (name)"
        )

    def _qualify_create_statement(self, sql: str) -> str:
        """Qualify CREATE statements (TABLE/INDEX/TRIGGER/FUNCTION) with schema."""
        up = sql.upper()
        if up.startswith("CREATE TABLE"):
            table_name = (
                sql.split("CREATE TABLE IF NOT EXISTS ")[-1].split("(")[0].strip()
            )
            modified = sql.replace(
                f"CREATE TABLE IF NOT EXISTS {table_name}",
                (
                    f"CREATE TABLE IF NOT EXISTS "
                    f"{self.schema_context.qualify_table(table_name)}"
                ),
            )
            if "REFERENCES " in modified:
                modified = modified.replace(
                    "REFERENCES items(",
                    f"REFERENCES {self.schema_context.qualify_table('items')}(",
                )
                modified = modified.replace(
                    "REFERENCES profiles(",
                    f"REFERENCES {self.schema_context.qualify_table('profiles')}(",
                )
            return modified
        if up.startswith("CREATE INDEX"):
            parts = sql.split(" ON ")
            if len(parts) > 1:
                table_name = parts[1].split("(")[0].strip()
                return (
                    parts[0]
                    + " ON "
                    + f"{self.schema_context.qualify_table(table_name)} ("
                    + "(".join(parts[1].split("(")[1:])
                )
            return sql
        if up.startswith("CREATE TRIGGER"):
            return sql.replace(" ON ", f" ON {self.schema_context}.")
        if up.startswith("CREATE FUNCTION"):
            function_name = (
                sql.split("CREATE OR REPLACE FUNCTION ")[-1].split("(")[0].strip()
            )
            return sql.replace(
                f"CREATE OR REPLACE FUNCTION {function_name}",
                f"CREATE OR REPLACE FUNCTION {self.schema_context}.{function_name}",
            )
        return sql

    async def _ensure_core_indexes(self, cursor):
        """Create core indexes required for performance and integrity."""
        await cursor.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS ix_items_profile_category_name "
            f"ON {self.schema_context.qualify_table('items')} "
            f"(profile_id, category, name)"
        )
        await cursor.execute(
            f"CREATE INDEX IF NOT EXISTS ix_items_tags_item_id "
            f"ON {self.schema_context.qualify_table('items_tags')} (item_id)"
        )
        await cursor.execute(
            f"CREATE INDEX IF NOT EXISTS ix_items_expiry "
            f"ON {self.schema_context.qualify_table('items')} (expiry)"
        )
        await cursor.execute(
            f"CREATE INDEX IF NOT EXISTS ix_items_tags_thread_id "
            f"ON {self.schema_context.qualify_table('items_tags')} "
            f"(name, value) WHERE name = 'thread_id'"
        )

    async def provision(
        self,
        profile: Optional[str] = None,
        recreate: bool = False,
        release_number: str = None,
    ) -> Tuple[AsyncConnectionPool, str, str, str]:
        """Provision a new PostgreSQL database."""
        LOGGER.debug(
            "Entering provision with profile=%s, recreate=%s, release_number=%s",
            profile,
            recreate,
            release_number,
        )

        parsed = urllib.parse.urlparse(self.conn_str)
        target_db = parsed.path.lstrip("/")
        if not target_db:
            raise ValueError(ERR_NO_DB_IN_CONN_STR)

        if not release_number:
            LOGGER.error("No release number provided for provisioning")
            raise DatabaseError(
                code=DatabaseErrorCode.PROVISION_ERROR,
                message="No release number provided for provisioning",
            )

        (
            default_profile,
            schema_release_number,
            skip_create_tables,
        ) = await self._check_and_create_database(
            target_db, recreate, profile, release_number
        )

        effective_release_number = (
            "release_0" if self.schema_config == "generic" else schema_release_number
        )

        pool = PostgresConnectionPool(
            conn_str=self.conn_str,
            min_size=self.min_size,
            max_size=self.max_size,
            timeout=self.timeout,
            max_idle=self.max_idle,
            max_lifetime=self.max_lifetime,
        )
        try:
            await pool.initialize()
        except Exception as e:
            LOGGER.error(
                "Failed to initialize connection pool for %s: %s", target_db, str(e)
            )
            raise DatabaseError(
                code=DatabaseErrorCode.CONNECTION_ERROR,
                message=f"Failed to initialize connection pool for {target_db}",
                actual_error=str(e),
            )

        if not skip_create_tables:
            await self._create_tables(pool, default_profile, effective_release_number)

        return pool, default_profile, self.conn_str, effective_release_number

    async def open(
        self,
        profile: Optional[str] = None,
        schema_migration: Optional[bool] = None,
        target_schema_release_number: Optional[str] = None,
    ) -> Tuple[AsyncConnectionPool, str, str, str]:
        """Open an existing PostgreSQL database."""
        LOGGER.debug(
            (
                "Starting PostgresConfig.open with uri=%s, profile=%s, "
                "schema_migration=%s, target_schema_release_number=%s"
            ),
            self.conn_str,
            profile,
            schema_migration,
            target_schema_release_number,
        )

        parsed = urllib.parse.urlparse(self.conn_str)
        target_db = parsed.path.lstrip("/")
        LOGGER.debug(
            "Parsed connection string: target_db=%s, query_params=%s",
            target_db,
            parsed.query,
        )
        if not target_db:
            LOGGER.error(ERR_NO_DB_IN_CONN_STR)
            raise ValueError(ERR_NO_DB_IN_CONN_STR)

        query_params = urllib.parse.parse_qs(parsed.query)
        valid_params = {
            "connect_timeout",
            "sslmode",
            "sslcert",
            "sslkey",
            "sslrootcert",
            "admin_account",
            "admin_password",
        }
        for param in query_params:
            if param not in valid_params:
                LOGGER.warning(
                    "Invalid URI query parameter '%s' in conn_str, will be ignored", param
                )

        default_conn_str = self._get_default_conn_str()
        LOGGER.debug("Generated default connection string: %s", default_conn_str)

        default_parsed = urllib.parse.urlparse(default_conn_str)
        default_query_params = urllib.parse.parse_qs(default_parsed.query)
        for param in default_query_params:
            if param not in valid_params:
                LOGGER.warning(
                    (
                        "Invalid URI query parameter '%s' in default_conn_str, "
                        "will be ignored"
                    ),
                    param,
                )

        pool_temp = None
        conn = None
        try:
            pool_temp = PostgresConnectionPool(
                conn_str=default_conn_str,
                min_size=1,
                max_size=1,
                timeout=self.timeout,
                max_idle=self.max_idle,
                max_lifetime=self.max_lifetime,
            )
            LOGGER.debug(
                (
                    "Created temporary PostgresConnectionPool with min_size=1, "
                    "max_size=1, timeout=%s"
                ),
                self.timeout,
            )
            LOGGER.debug("Attempting to initialize temporary connection pool")
            await pool_temp.initialize()
            LOGGER.debug("Temporary connection pool initialized successfully")

            LOGGER.debug("Attempting to get connection from temporary pool")
            conn = await pool_temp.getconn()
            LOGGER.debug(
                "Connection obtained from temporary pool, transaction_status=%s",
                conn.pgconn.transaction_status,
            )
            if conn.pgconn.transaction_status != pq.TransactionStatus.IDLE:
                LOGGER.debug(
                    "Connection in non-IDLE state: %s, attempting rollback",
                    conn.pgconn.transaction_status,
                )
                await conn.rollback()
                LOGGER.debug(
                    "Rollback completed, new transaction status=%s",
                    conn.pgconn.transaction_status,
                )
            if conn.pgconn.transaction_status != pq.TransactionStatus.IDLE:
                LOGGER.error(
                    "Connection still in non-IDLE state after rollback: %s",
                    conn.pgconn.transaction_status,
                )
                raise DatabaseError(
                    code=DatabaseErrorCode.CONNECTION_ERROR,
                    message=(
                        f"Connection in invalid transaction state: "
                        f"{conn.pgconn.transaction_status}"
                    ),
                )
            LOGGER.debug("Setting autocommit to True")
            await conn.set_autocommit(True)
            async with conn.cursor() as cursor:
                LOGGER.debug(
                    (
                        "Executing query to check database existence: "
                        f"{SQL_SELECT_DB_EXISTS}"
                    ),
                    target_db,
                )
                await cursor.execute(SQL_SELECT_DB_EXISTS, (target_db,))
                db_exists = await cursor.fetchone()
                LOGGER.debug("Database existence query result: db_exists=%s", db_exists)
                if not db_exists:
                    LOGGER.error("Database '%s' not found", target_db)
                    raise DatabaseError(
                        code=DatabaseErrorCode.DATABASE_NOT_FOUND,
                        message=f"Database '{target_db}' does not exist",
                    )
        except Exception as e:
            LOGGER.error("Failed to check database existence: %s", str(e))
            if (
                isinstance(e, DatabaseError)
                and e.code == DatabaseErrorCode.DATABASE_NOT_FOUND
            ):
                raise
            raise DatabaseError(
                code=DatabaseErrorCode.CONNECTION_ERROR,
                message=f"Failed to query database existence for '{target_db}'",
                actual_error=str(e),
            )
        finally:
            if conn:
                LOGGER.debug(
                    "Returning connection to temporary pool, transaction_status=%s",
                    conn.pgconn.transaction_status if conn else "None",
                )
                await pool_temp.putconn(conn)
            if pool_temp:
                LOGGER.debug("Closing temporary connection pool")
                await pool_temp.close()

        LOGGER.debug(
            (
                "Creating connection pool for target database with "
                "conn_str=%s, min_size=%s, max_size=%s"
            ),
            self.conn_str,
            self.min_size,
            self.max_size,
        )
        pool = PostgresConnectionPool(
            conn_str=self.conn_str,
            min_size=self.min_size,
            max_size=self.max_size,
            timeout=self.timeout,
            max_idle=self.max_idle,
            max_lifetime=self.max_lifetime,
        )
        try:
            LOGGER.debug("Attempting to initialize target connection pool")
            await pool.initialize()
            LOGGER.debug("Target connection pool initialized successfully")
        except Exception as e:
            LOGGER.error(
                "Failed to initialize connection pool for target database: %s", str(e)
            )
            raise DatabaseError(
                code=DatabaseErrorCode.CONNECTION_ERROR,
                message=f"Failed to initialize connection pool for '{target_db}'",
                actual_error=str(e),
            )

        LOGGER.debug("Attempting to get connection from target pool")
        conn = await pool.getconn()
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(f"SET search_path TO {self.schema_context}, public")
                LOGGER.debug("Querying schema_release_number from config table")
                await cursor.execute(
                    (
                        f"SELECT value FROM {self.schema_context.qualify_table('config')}"
                        f" WHERE name = %s"
                    ),
                    ("schema_release_number",),
                )
                release_row = await cursor.fetchone()
                current_release = release_row[0] if release_row else None
                LOGGER.debug("Schema release number: %s", current_release)
                if not current_release:
                    LOGGER.error("Release number not found in config table")
                    raise DatabaseError(
                        code=DatabaseErrorCode.UNSUPPORTED_VERSION,
                        message="Release number not found in config table",
                    )
                effective_release_number = current_release

                LOGGER.debug("Querying schema_config from config table")
                await cursor.execute(
                    (
                        f"SELECT value FROM {self.schema_context.qualify_table('config')}"
                        f" WHERE name = %s"
                    ),
                    ("schema_config",),
                )
                schema_config_row = await cursor.fetchone()
                if not schema_config_row:
                    LOGGER.error("Schema config not found in config table")
                    raise DatabaseError(
                        code=DatabaseErrorCode.QUERY_ERROR,
                        message="Schema config not found in config table",
                    )
                self.schema_config = schema_config_row[0]
                LOGGER.debug("Schema config: %s", self.schema_config)

                # Enforce generic schema uses release_0
                if self.schema_config == "generic" and current_release != "release_0":
                    LOGGER.error(
                        (
                            "Invalid configuration: schema_config='generic' but "
                            "schema_release_number='%s'"
                        ),
                        current_release,
                    )
                    raise DatabaseError(
                        code=DatabaseErrorCode.QUERY_ERROR,
                        message=(
                            f"Invalid configuration: schema_config='generic' requires "
                            f"schema_release_number='release_0', found "
                            f"'{current_release}'"
                        ),
                    )

                # Enforce normalize schema matches target_schema_release_number
                if (
                    self.schema_config == "normalize"
                    and target_schema_release_number
                    and current_release != target_schema_release_number
                ):
                    LOGGER.error(
                        (
                            "Schema release number mismatch: database has '%s', "
                            "but target is '%s'"
                        ),
                        current_release,
                        target_schema_release_number,
                    )
                    raise DatabaseError(
                        code=DatabaseErrorCode.UNSUPPORTED_VERSION,
                        message=(
                            f"Schema release number mismatch: database has "
                            f"'{current_release}', but target is "
                            f"'{target_schema_release_number}'. "
                            f"Please perform an upgrade."
                        ),
                    )

                LOGGER.debug("Querying default_profile from config table")
                await cursor.execute(
                    (
                        f"SELECT value FROM {self.schema_context.qualify_table('config')}"
                        f" WHERE name = %s"
                    ),
                    ("default_profile",),
                )
                default_profile_row = await cursor.fetchone()
                if not default_profile_row:
                    LOGGER.error("Default profile not found")
                    raise DatabaseError(
                        code=DatabaseErrorCode.DEFAULT_PROFILE_NOT_FOUND,
                        message="Default profile not found in the database",
                    )
                default_profile = default_profile_row[0]
                profile_name = profile or default_profile
                LOGGER.debug(
                    "Default profile: %s, selected profile: %s",
                    default_profile,
                    profile_name,
                )
                LOGGER.debug("Querying profile ID for %s", profile_name)
                await cursor.execute(
                    (
                        f"SELECT id FROM {self.schema_context.qualify_table('profiles')} "
                        f"WHERE name = %s"
                    ),
                    (profile_name,),
                )
                if not await cursor.fetchone():
                    LOGGER.error("Profile '%s' not found", profile_name)
                    raise DatabaseError(
                        code=DatabaseErrorCode.PROFILE_NOT_FOUND,
                        message=f"Profile '{profile_name}' not found",
                    )
            await conn.commit()
            LOGGER.debug("Committed configuration queries")
        except Exception as e:
            await conn.rollback()
            LOGGER.error("Failed to query database configuration: %s", str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message="Failed to query database configuration",
                actual_error=str(e),
            )
        finally:
            await pool.putconn(conn)

        LOGGER.debug(
            "Returning pool, profile_name=%s, conn_str=%s, effective_release_number=%s",
            profile_name,
            self.conn_str,
            effective_release_number,
        )
        return pool, profile_name, self.conn_str, effective_release_number

    async def remove(self) -> bool:
        """Remove the PostgreSQL database."""
        parsed = urllib.parse.urlparse(self.conn_str)
        target_db = parsed.path.lstrip("/")
        if not target_db:
            return False
        default_conn_str = self._get_default_conn_str()
        pool = PostgresConnectionPool(
            conn_str=default_conn_str,
            min_size=self.min_size,
            max_size=self.max_size,
            timeout=self.timeout,
            max_idle=self.max_idle,
            max_lifetime=self.max_lifetime,
        )
        try:
            await pool.initialize()
            conn = await pool.getconn()
            try:
                await conn.rollback()
                await conn.set_autocommit(True)
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        (
                            "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM "
                            "pg_stat_activity WHERE pg_stat_activity.datname = %s AND "
                            "pid <> pg_backend_pid()"
                        ),
                        (target_db,),
                    )
                    await cursor.execute(f"DROP DATABASE IF EXISTS {target_db}")
                return True
            except Exception as e:
                LOGGER.error("Failed to remove database %s: %s", target_db, str(e))
                raise DatabaseError(
                    code=DatabaseErrorCode.CONNECTION_ERROR,
                    message=f"Failed to remove database {target_db}",
                    actual_error=str(e),
                )
            finally:
                await pool.putconn(conn)
        finally:
            await pool.close()
