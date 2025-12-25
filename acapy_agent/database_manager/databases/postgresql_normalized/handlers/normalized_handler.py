"""Module docstring."""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, List, Optional, Sequence, Tuple

from psycopg import AsyncCursor, pq

from acapy_agent.database_manager.databases.errors import DatabaseError, DatabaseErrorCode
from acapy_agent.database_manager.databases.postgresql_normalized.schema_context import (
    SchemaContext,
)
from acapy_agent.database_manager.db_types import Entry
from acapy_agent.database_manager.wql_normalized.encoders import encoder_factory
from acapy_agent.database_manager.wql_normalized.query import query_from_json
from acapy_agent.database_manager.wql_normalized.tags import TagQuery, query_to_tagquery

from .base_handler import BaseHandler

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)  # Enable debug logging for troubleshooting

LOG_FAILED = "[%s] Failed: %s"
LOG_DECODED_VALUE = "[%s] Decoded value from bytes: %s"
LOG_VALUE_NONE_ID = "[%s] value is None for item_id=%s"
LOG_EXEC_SQL_PARAMS = "[%s] Executing SQL: %s | Params: %s"
LOG_EXEC_SQL_SINGLE_PARAM = "[%s] Executing SQL: %s | Params: (%s,)"
LOG_PARSED_TAG_FILTER = "[%s] Parsed tag_filter JSON: %s"
LOG_GENERATED_SQL_CLAUSE = "[%s] Generated SQL clause: %s, params: %s"
LOG_GENERATED_SQL_CLAUSE_ARGS = "[%s] Generated SQL clause: %s, arguments: %s"
LOG_INVALID_ORDER_BY = "[%s] Invalid order_by column: %s"
LOG_FETCHED_ROW = "[%s] Fetched row: %s"
SQL_SET_UTF8 = "SET client_encoding = 'UTF8'"


def is_valid_json(value: str) -> bool:
    """Check if a string is valid JSON."""
    try:
        json.loads(value)
        return True
    except json.JSONDecodeError:
        return False


def serialize_json_with_bool_strings(data: Any) -> str:
    """Serialize data to JSON, converting booleans to strings and replacing '~' with '_'.

    Args:
        data: Data to serialize.

    Returns:
        JSON string representation.

    """

    def convert_bools_and_keys(obj: Any) -> Any:
        if isinstance(obj, bool):
            return str(obj).lower()
        elif isinstance(obj, dict):
            return {
                k.replace("~", "_"): convert_bools_and_keys(v) for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [convert_bools_and_keys(item) for item in obj]
        return obj

    try:
        return json.dumps(convert_bools_and_keys(data))
    except (TypeError, ValueError) as e:
        LOGGER.error("Failed to serialize JSON: %s", str(e))
        raise DatabaseError(
            code=DatabaseErrorCode.QUERY_ERROR,
            message=f"Failed to serialize JSON: {str(e)}",
        )


def deserialize_tags(tags: dict) -> dict:
    """Deserialize tags, converting JSON strings and handling booleans."""
    result = {}
    for k, v in tags.items():
        if isinstance(v, str) and is_valid_json(v):
            try:
                result[k] = json.loads(v)
            except json.JSONDecodeError:
                result[k] = v
        elif v == "true":
            result[k] = True
        elif v == "false":
            result[k] = False
        else:
            result[k] = v
    return result


class NormalizedHandler(BaseHandler):
    """Handler for normalized categories using specific tables."""

    def __init__(
        self,
        category: str,
        columns: List[str],
        table_name: Optional[str] = None,
        schema_context: Optional[SchemaContext] = None,
    ):
        """Initialize NormalizedHandler."""
        super().__init__(category)
        self.schema_context = schema_context or SchemaContext()
        self._table_name = table_name or category  # Store unqualified table name
        self.table = self.schema_context.qualify_table(self._table_name)
        self.columns = columns
        self.ALLOWED_ORDER_BY_COLUMNS = set(columns) | {"id", "name", "value"}
        self.encoder = encoder_factory.get_encoder(
            "postgresql", lambda x: x, lambda x: x, normalized=True
        )
        LOGGER.debug(
            "[init] Initialized NormalizedHandler for category=%s, table=%s, "
            "columns=%s, schema_context=%s",
            category,
            self.table,
            columns,
            self.schema_context,
        )

        self.EXPIRY_CLAUSE = "(i.expiry IS NULL OR i.expiry > CURRENT_TIMESTAMP)"

    def set_schema_context(self, schema_context: SchemaContext) -> None:
        """Update the schema context and re-qualify table names.

        This method should be called when the handler is used with a different
        schema than the one it was initialized with (e.g., when handlers are
        created at module load time with a default schema).
        """
        if (
            schema_context
            and schema_context.schema_name != self.schema_context.schema_name
        ):
            self.schema_context = schema_context
            self.table = self.schema_context.qualify_table(self._table_name)
            LOGGER.debug(
                "[set_schema_context] Updated schema_context to %s, table=%s",
                self.schema_context,
                self.table,
            )

    async def _ensure_utf8(self, _cursor: AsyncCursor) -> None:
        # UTF8 encoding is set via connection pool options (-c client_encoding=UTF8)
        # No need to execute SET here - would add unnecessary latency
        pass

    def _validate_order_by(self, order_by: Optional[str]) -> None:
        if order_by and order_by not in self.ALLOWED_ORDER_BY_COLUMNS:
            LOGGER.error("[order_by] Invalid column: %s", order_by)
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=(
                    LOG_INVALID_ORDER_BY % ("insert", order_by) + f". Allowed columns: "
                    f"{', '.join(self.ALLOWED_ORDER_BY_COLUMNS)}"
                ),
            )

    async def insert(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        name: str,
        value: str | bytes,
        tags: dict,
        expiry_ms: Optional[int] = None,
    ) -> None:
        """Insert a new entry."""
        operation_name = "insert"
        LOGGER.debug(
            "[%s] Starting with category=%s, name=%s, value=%r, tags=%s, "
            "expiry_ms=%s, table=%s",
            operation_name,
            category,
            name,
            value,
            tags,
            expiry_ms,
            self.table,
        )

        try:
            await self._ensure_utf8(cursor)

            # Process and validate input data
            expiry, processed_value, json_data = self._process_insert_data(
                operation_name, value, expiry_ms
            )

            # Insert into items table and get item_id
            item_id = await self._insert_item(
                cursor,
                operation_name,
                profile_id,
                category,
                name,
                processed_value,
                expiry,
            )

            # Process columns and insert into normalized table
            await self._insert_normalized_data(
                cursor, operation_name, item_id, name, json_data, tags
            )

        except Exception as e:
            LOGGER.error(LOG_FAILED, operation_name, str(e))
            await cursor.connection.rollback()
            raise
        finally:
            if cursor.connection.pgconn.transaction_status != pq.TransactionStatus.IDLE:
                await cursor.connection.commit()

    def _process_insert_data(
        self, operation_name: str, value: str | bytes, expiry_ms: Optional[int]
    ) -> tuple:
        """Process and validate insert data."""
        # Handle expiry
        expiry = None
        if expiry_ms is not None:
            expiry = datetime.now(timezone.utc) + timedelta(milliseconds=expiry_ms)
            LOGGER.debug("[%s] Computed expiry: %s", operation_name, expiry)

        # Handle bytes value
        if isinstance(value, bytes):
            value = value.decode("utf-8")
            LOGGER.debug(LOG_DECODED_VALUE, operation_name, value)

        # Parse JSON data
        json_data = {}
        if value and isinstance(value, str) and is_valid_json(value):
            try:
                json_data = json.loads(value)
                LOGGER.debug("[%s] Parsed json_data: %s", operation_name, json_data)
            except json.JSONDecodeError as e:
                LOGGER.error(
                    "[%s] Invalid JSON value: %s, raw value: %s",
                    operation_name,
                    str(e),
                    value,
                )
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=f"Invalid JSON value: {str(e)}",
                )

        return expiry, value, json_data

    async def _insert_item(
        self,
        cursor,
        operation_name: str,
        profile_id: int,
        category: str,
        name: str,
        value: str,
        expiry,
    ) -> int:
        """Insert into items table and return item_id."""
        LOGGER.debug(
            "[%s] Inserting into items table with profile_id=%s, category=%s, "
            "name=%s, value=%s, expiry=%s",
            operation_name,
            profile_id,
            category,
            name,
            value,
            expiry,
        )
        await cursor.execute(
            f"""
            INSERT INTO {self.schema_context.qualify_table("items")} (
                profile_id, kind, category, name, value, expiry
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (profile_id, category, name) DO NOTHING
            RETURNING id
        """,
            (profile_id, 0, category, name, value, expiry),
        )
        row = await cursor.fetchone()
        if not row:
            LOGGER.error(
                "[%s] Duplicate entry for category=%s, name=%s",
                operation_name,
                category,
                name,
            )
            raise DatabaseError(
                code=DatabaseErrorCode.DUPLICATE_ITEM_ENTRY_ERROR,
                message=(f"Duplicate entry for category '{category}' and name '{name}'"),
            )
        item_id = row[0]
        LOGGER.debug(
            "[%s] Inserted into items table, item_id=%s", operation_name, item_id
        )
        return item_id

    async def _insert_normalized_data(
        self,
        cursor,
        operation_name: str,
        item_id: int,
        name: str,
        json_data: dict,
        tags: dict,
    ) -> None:
        """Process columns and insert into normalized table."""
        data = {"item_id": item_id, "item_name": name}
        LOGGER.debug("[%s] Processing columns: %s", operation_name, self.columns)

        for col in self.columns:
            val = self._process_column_value(operation_name, col, json_data, tags)
            data[col] = val

        columns = list(data.keys())
        placeholders = ", ".join(["%s" for _ in columns])
        sql = f"INSERT INTO {self.table} ({', '.join(columns)}) VALUES ({placeholders})"
        LOGGER.debug(
            LOG_EXEC_SQL_PARAMS,
            operation_name,
            sql,
            list(data.values()),
        )
        await cursor.execute(sql, list(data.values()))
        LOGGER.debug(
            "[%s] Successfully inserted into %s for item_id=%s",
            operation_name,
            self.table,
            item_id,
        )

    def _process_column_value(
        self, operation_name: str, col: str, json_data: dict, tags: dict
    ):
        """Process individual column value."""
        val = json_data.get(col, tags.get(col))
        if val is None:
            LOGGER.debug(
                "[%s] Column %s not found in json_data or tags, setting to NULL",
                operation_name,
                col,
            )
            return val
        elif isinstance(val, (dict, list)):
            try:
                val = serialize_json_with_bool_strings(val)
                LOGGER.debug("[%s] Serialized %s to JSON: %s", operation_name, col, val)
            except DatabaseError as e:
                LOGGER.error(
                    "[%s] Serialization failed for column %s: %s",
                    operation_name,
                    col,
                    str(e),
                )
                raise
        elif val is True:
            val = "true"
        elif val is False:
            val = "false"

        LOGGER.debug(
            "[%s] Added column %s: %s (type: %s)",
            operation_name,
            col,
            val,
            type(val),
        )
        return val

    async def replace(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        name: str,
        value: str | bytes,
        tags: dict,
        expiry_ms: Optional[int] = None,
    ) -> None:
        """Replace an existing entry."""
        operation_name = "replace"
        LOGGER.debug(
            "[%s] Starting with profile_id=%s, category=%s, name=%s, value=%r, "
            "tags=%s, expiry_ms=%s, table=%s",
            operation_name,
            profile_id,
            category,
            name,
            value,
            tags,
            expiry_ms,
            self.table,
        )

        try:
            await self._ensure_utf8(cursor)
            expiry = None
            if expiry_ms is not None:
                expiry = datetime.now(timezone.utc) + timedelta(milliseconds=expiry_ms)
                LOGGER.debug("[%s] Computed expiry: %s", operation_name, expiry)

            if isinstance(value, bytes):
                value = value.decode("utf-8")
                LOGGER.debug(LOG_DECODED_VALUE, operation_name, value)

            await cursor.execute(
                f"""
                SELECT id FROM {self.schema_context.qualify_table("items")}
                WHERE profile_id = %s AND category = %s AND name = %s
            """,
                (profile_id, category, name),
            )
            row = await cursor.fetchone()
            if not row:
                LOGGER.error(
                    "[%s] Record not found for category=%s, name=%s",
                    operation_name,
                    category,
                    name,
                )
                raise DatabaseError(
                    code=DatabaseErrorCode.RECORD_NOT_FOUND,
                    message=(
                        f"Record not found for category '{category}' and name '{name}'"
                    ),
                )
            item_id = row[0]
            LOGGER.debug("[%s] Found item_id=%s for replacement", operation_name, item_id)

            await cursor.execute(
                f"""
                UPDATE {self.schema_context.qualify_table("items")} 
                SET value = %s, expiry = %s
                WHERE id = %s
            """,
                (value, expiry, item_id),
            )
            LOGGER.debug(
                "[%s] Updated items table for item_id=%s", operation_name, item_id
            )

            await cursor.execute(
                f"DELETE FROM {self.table} WHERE item_id = %s", (item_id,)
            )
            LOGGER.debug(
                "[%s] Deleted existing entry from %s for item_id=%s",
                operation_name,
                self.table,
                item_id,
            )

            json_data = {}
            if value and isinstance(value, str) and is_valid_json(value):
                try:
                    json_data = json.loads(value)
                    LOGGER.debug("[%s] Parsed json_data: %s", operation_name, json_data)
                except json.JSONDecodeError as e:
                    LOGGER.error("[%s] Invalid JSON value: %s", operation_name, str(e))
                    raise DatabaseError(
                        code=DatabaseErrorCode.QUERY_ERROR,
                        message=f"Invalid JSON value: {str(e)}",
                    )

            data = {"item_id": item_id, "item_name": name}
            LOGGER.debug("[%s] Processing columns: %s", operation_name, self.columns)
            for col in self.columns:
                val = json_data.get(col, tags.get(col))
                if val is None:
                    LOGGER.debug(
                        "[%s] Column %s not found in json_data or tags, setting to NULL",
                        operation_name,
                        col,
                    )
                elif isinstance(val, (dict, list)):
                    try:
                        val = serialize_json_with_bool_strings(val)
                        LOGGER.debug(
                            "[%s] Serialized %s to JSON: %s", operation_name, col, val
                        )
                    except DatabaseError as e:
                        LOGGER.error(
                            "[%s] Serialization failed for column %s: %s",
                            operation_name,
                            col,
                            str(e),
                        )
                        raise
                elif val is True:
                    val = "true"
                elif val is False:
                    val = "false"
                data[col] = val
                LOGGER.debug(
                    "[%s] Added column %s: %s (type: %s)",
                    operation_name,
                    col,
                    val,
                    type(val),
                )

            columns = list(data.keys())
            placeholders = ", ".join(["%s" for _ in columns])
            sql = (
                f"INSERT INTO {self.table} ({', '.join(columns)}) VALUES ({placeholders})"
            )
            LOGGER.debug(
                LOG_EXEC_SQL_PARAMS,
                operation_name,
                sql,
                list(data.values()),
            )
            await cursor.execute(sql, list(data.values()))
            LOGGER.debug(
                "[%s] Successfully inserted into %s for item_id=%s",
                operation_name,
                self.table,
                item_id,
            )
        except Exception as e:
            LOGGER.error(LOG_FAILED, operation_name, str(e))
            await cursor.connection.rollback()
            raise
        finally:
            if cursor.connection.pgconn.transaction_status != pq.TransactionStatus.IDLE:
                await cursor.connection.commit()

    async def fetch(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        name: str,
        tag_filter: str | dict,
        for_update: bool,
    ) -> Optional[Entry]:
        """Fetch a single entry."""
        operation_name = "fetch"
        LOGGER.debug(
            "[%s] Starting with profile_id=%s, category=%s, name=%s, "
            "tag_filter=%s, for_update=%s, table=%s",
            operation_name,
            profile_id,
            category,
            name,
            tag_filter,
            for_update,
            self.table,
        )

        try:
            await self._ensure_utf8(cursor)
            base_query = f"""
                SELECT id, value FROM {self.schema_context.qualify_table("items")}
                WHERE profile_id = %s AND category = %s AND name = %s
                AND (expiry IS NULL OR expiry > CURRENT_TIMESTAMP)
            """
            if for_update:
                base_query += " FOR UPDATE"
            base_params = (profile_id, category, name)
            LOGGER.debug(
                LOG_EXEC_SQL_PARAMS,
                operation_name,
                base_query.strip(),
                base_params,
            )
            await cursor.execute(base_query, base_params)
            row = await cursor.fetchone()
            LOGGER.debug(LOG_FETCHED_ROW, operation_name, row)

            if not row:
                return None
            item_id, item_value = row
            if isinstance(item_value, bytes):
                item_value = item_value.decode("utf-8")
                LOGGER.debug(LOG_DECODED_VALUE, operation_name, item_value)
            elif item_value is None:
                LOGGER.warning(LOG_VALUE_NONE_ID, operation_name, item_id)
                item_value = ""

            if tag_filter:
                if isinstance(tag_filter, str):
                    try:
                        tag_filter = json.loads(tag_filter)
                        LOGGER.debug(LOG_PARSED_TAG_FILTER, operation_name, tag_filter)
                    except json.JSONDecodeError as e:
                        raise DatabaseError(
                            code=DatabaseErrorCode.QUERY_ERROR,
                            message=f"Invalid tag_filter JSON: {str(e)}",
                        )
                wql_query = query_from_json(tag_filter)
                tag_query = query_to_tagquery(wql_query)
                sql_clause, params = self.get_sql_clause(tag_query)
                query = (
                    f"SELECT * FROM {self.table} t WHERE t.item_id = %s AND {sql_clause}"
                )
                full_params = [item_id] + params
                LOGGER.debug(
                    LOG_EXEC_SQL_PARAMS,
                    operation_name,
                    query,
                    full_params,
                )
                await cursor.execute(query, full_params)
            else:
                query = f"SELECT * FROM {self.table} WHERE item_id = %s"
                LOGGER.debug(
                    LOG_EXEC_SQL_SINGLE_PARAM,
                    operation_name,
                    query,
                    item_id,
                )
                await cursor.execute(query, (item_id,))

            row = await cursor.fetchone()
            LOGGER.debug(
                LOG_FETCHED_ROW + " from table %s", operation_name, row, self.table
            )
            if not row:
                return None

            columns = [desc[0] for desc in cursor.description]
            row_dict = dict(zip(columns, row))
            tags = {
                k: v
                for k, v in row_dict.items()
                if k not in ["id", "item_id", "item_name"]
            }
            tags = deserialize_tags(tags)
            LOGGER.debug(
                "[%s] Row parsed: name=%s, value=%s, tags=%s",
                operation_name,
                name,
                item_value,
                tags,
            )
            return Entry(category=category, name=name, value=item_value, tags=tags)
        except Exception as e:
            LOGGER.error(LOG_FAILED, operation_name, str(e))
            await cursor.connection.rollback()
            raise
        finally:
            if cursor.connection.pgconn.transaction_status != pq.TransactionStatus.IDLE:
                await cursor.connection.commit()

    async def fetch_all(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        tag_filter: str | dict,
        limit: int,
        for_update: bool,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> Sequence[Entry]:
        """Fetch all entries matching criteria."""
        operation_name = "fetch_all"
        LOGGER.debug(
            "[%s] Starting with profile_id=%s, category=%s, tag_filter=%s, "
            "limit=%s, for_update=%s, order_by=%s, descending=%s, table=%s",
            operation_name,
            profile_id,
            category,
            tag_filter,
            limit,
            for_update,
            order_by,
            descending,
            self.table,
        )

        try:
            await self._ensure_utf8(cursor)
            if order_by and order_by not in self.ALLOWED_ORDER_BY_COLUMNS:
                LOGGER.error(LOG_INVALID_ORDER_BY, operation_name, order_by)
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=(
                        LOG_INVALID_ORDER_BY % ("scan", order_by) + f". Allowed columns: "
                        f"{', '.join(self.ALLOWED_ORDER_BY_COLUMNS)}"
                    ),
                )

            sql_clause = "TRUE"
            params = []
            if tag_filter:
                if isinstance(tag_filter, str):
                    try:
                        tag_filter = json.loads(tag_filter)
                        LOGGER.debug(LOG_PARSED_TAG_FILTER, operation_name, tag_filter)
                    except json.JSONDecodeError as e:
                        raise DatabaseError(
                            code=DatabaseErrorCode.QUERY_ERROR,
                            message=f"Invalid tag_filter JSON: {str(e)}",
                        )
                wql_query = query_from_json(tag_filter)
                tag_query = query_to_tagquery(wql_query)
                sql_clause, params = self.get_sql_clause(tag_query)
                LOGGER.debug(
                    LOG_GENERATED_SQL_CLAUSE,
                    operation_name,
                    sql_clause,
                    params,
                )

            order_column = order_by if order_by else "id"
            table_prefix = "t" if order_by in self.columns else "i"
            order_direction = "DESC" if descending else "ASC"

            query = f"""
                SELECT i.id AS i_id, i.name AS i_name, i.value AS i_value, t.*
                FROM {self.schema_context.qualify_table("items")} i
                JOIN {self.table} t ON i.id = t.item_id
                WHERE i.profile_id = %s AND i.category = %s
                AND (i.expiry IS NULL OR i.expiry > CURRENT_TIMESTAMP)
                AND {sql_clause}
                ORDER BY {table_prefix}.{order_column} {order_direction}
            """
            full_params = [profile_id, category] + params
            if limit is not None:
                query += " LIMIT %s"
                full_params.append(limit)

            LOGGER.debug(
                LOG_EXEC_SQL_PARAMS,
                operation_name,
                query.strip(),
                full_params,
            )
            await cursor.execute(query, full_params)
            columns = [desc[0] for desc in cursor.description]
            entries = []

            async for row in cursor:
                LOGGER.debug(LOG_FETCHED_ROW, operation_name, row)
                row_dict = dict(zip(columns, row))
                name = row_dict["i_name"]
                value = row_dict["i_value"]
                if isinstance(value, bytes):
                    value = value.decode("utf-8")
                    LOGGER.debug(LOG_DECODED_VALUE, operation_name, value)
                elif value is None:
                    LOGGER.warning(
                        LOG_VALUE_NONE_ID,
                        operation_name,
                        row_dict["i_id"],
                    )
                    value = ""
                tags = {
                    k: v
                    for k, v in row_dict.items()
                    if k not in ["i_id", "i_name", "i_value", "item_id", "item_name"]
                }
                tags = deserialize_tags(tags)
                entries.append(
                    Entry(category=category, name=name, value=value, tags=tags)
                )

            LOGGER.debug("[%s] Total entries fetched: %s", operation_name, len(entries))
            return entries
        except Exception as e:
            LOGGER.error(LOG_FAILED, operation_name, str(e))
            await cursor.connection.rollback()
            raise
        finally:
            if cursor.connection.pgconn.transaction_status != pq.TransactionStatus.IDLE:
                await cursor.connection.commit()

    async def count(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        tag_filter: str | dict,
    ) -> int:
        """Count entries matching criteria."""
        operation_name = "count"
        LOGGER.debug(
            "[%s] Starting with profile_id=%s, category=%s, tag_filter=%s, table=%s",
            operation_name,
            profile_id,
            category,
            tag_filter,
            self.table,
        )

        try:
            await self._ensure_utf8(cursor)
            sql_clause = "TRUE"
            params = []
            if tag_filter:
                if isinstance(tag_filter, str):
                    try:
                        tag_filter = json.loads(tag_filter)
                        LOGGER.debug(LOG_PARSED_TAG_FILTER, operation_name, tag_filter)
                    except json.JSONDecodeError as e:
                        raise DatabaseError(
                            code=DatabaseErrorCode.QUERY_ERROR,
                            message=f"Invalid tag_filter JSON: {str(e)}",
                        )
                wql_query = query_from_json(tag_filter)
                tag_query = query_to_tagquery(wql_query)
                sql_clause, params = self.get_sql_clause(tag_query)
                LOGGER.debug(
                    LOG_GENERATED_SQL_CLAUSE,
                    operation_name,
                    sql_clause,
                    params,
                )

            query = f"""
                SELECT COUNT(*)
                FROM {self.schema_context.qualify_table("items")} i
                JOIN {self.table} t ON i.id = t.item_id
                WHERE i.profile_id = %s AND i.category = %s
                AND (i.expiry IS NULL OR i.expiry > CURRENT_TIMESTAMP)
                AND {sql_clause}
            """
            LOGGER.debug(
                LOG_EXEC_SQL_PARAMS,
                operation_name,
                query.strip(),
                [profile_id, category] + params,
            )
            await cursor.execute(query, [profile_id, category] + params)
            count = (await cursor.fetchone())[0]
            LOGGER.debug("[%s] Counted %s entries", operation_name, count)
            return count
        except Exception as e:
            LOGGER.error(LOG_FAILED, operation_name, str(e))
            await cursor.connection.rollback()
            raise
        finally:
            if cursor.connection.pgconn.transaction_status != pq.TransactionStatus.IDLE:
                await cursor.connection.commit()

    async def remove(
        self, cursor: AsyncCursor, profile_id: int, category: str, name: str
    ) -> None:
        """Remove a single entry."""
        operation_name = "remove"
        LOGGER.debug(
            "[%s] Starting with profile_id=%s, category=%s, name=%s, table=%s",
            operation_name,
            profile_id,
            category,
            name,
            self.table,
        )

        try:
            await self._ensure_utf8(cursor)
            await cursor.execute(
                f"""
                SELECT id FROM {self.schema_context.qualify_table("items")}
                WHERE profile_id = %s AND category = %s AND name = %s
            """,
                (profile_id, category, name),
            )
            row = await cursor.fetchone()
            if not row:
                LOGGER.error(
                    "[%s] Record not found for category=%s, name=%s",
                    operation_name,
                    category,
                    name,
                )
                raise DatabaseError(
                    code=DatabaseErrorCode.RECORD_NOT_FOUND,
                    message=(
                        f"Record not found for category '{category}' and name '{name}'"
                    ),
                )
            item_id = row[0]
            LOGGER.debug("[%s] Found item_id=%s for removal", operation_name, item_id)

            await cursor.execute(
                f"DELETE FROM {self.table} WHERE item_id = %s", (item_id,)
            )
            await cursor.execute(
                f"DELETE FROM {self.schema_context.qualify_table('items')} WHERE id = %s",
                (item_id,),
            )
            LOGGER.debug("[%s] Removed record with item_id=%s", operation_name, item_id)
        except Exception as e:
            LOGGER.error(LOG_FAILED, operation_name, str(e))
            await cursor.connection.rollback()
            raise
        finally:
            if cursor.connection.pgconn.transaction_status != pq.TransactionStatus.IDLE:
                await cursor.connection.commit()

    async def remove_all(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        tag_filter: str | dict,
    ) -> int:
        """Remove all entries matching criteria."""
        operation_name = "remove_all"
        LOGGER.debug(
            "[%s] Starting with profile_id=%s, category=%s, tag_filter=%s, table=%s",
            operation_name,
            profile_id,
            category,
            tag_filter,
            self.table,
        )

        try:
            await self._ensure_utf8(cursor)
            sql_clause = "TRUE"
            params = []
            if tag_filter:
                if isinstance(tag_filter, str):
                    try:
                        tag_filter = json.loads(tag_filter)
                        LOGGER.debug(LOG_PARSED_TAG_FILTER, operation_name, tag_filter)
                    except json.JSONDecodeError as e:
                        raise DatabaseError(
                            code=DatabaseErrorCode.QUERY_ERROR,
                            message=f"Invalid tag_filter JSON: {str(e)}",
                        )
                wql_query = query_from_json(tag_filter)
                tag_query = query_to_tagquery(wql_query)
                sql_clause, params = self.get_sql_clause(tag_query)
                LOGGER.debug(
                    LOG_GENERATED_SQL_CLAUSE,
                    operation_name,
                    sql_clause,
                    params,
                )

            query = f"""
                DELETE FROM {self.schema_context.qualify_table("items")} 
                WHERE id IN (
                    SELECT i.id FROM {self.schema_context.qualify_table("items")} i
                    JOIN {self.table} t ON i.id = t.item_id
                    WHERE i.profile_id = %s AND i.category = %s
                    AND (i.expiry IS NULL OR i.expiry > CURRENT_TIMESTAMP)
                    AND {sql_clause}
                )
            """
            LOGGER.debug(
                LOG_EXEC_SQL_PARAMS,
                operation_name,
                query.strip(),
                [profile_id, category] + params,
            )
            await cursor.execute(query, [profile_id, category] + params)
            rowcount = cursor.rowcount
            LOGGER.debug("[%s] Removed %s entries", operation_name, rowcount)
            return rowcount
        except Exception as e:
            LOGGER.error(LOG_FAILED, operation_name, str(e))
            await cursor.connection.rollback()
            raise
        finally:
            if cursor.connection.pgconn.transaction_status != pq.TransactionStatus.IDLE:
                await cursor.connection.commit()

    async def scan(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        tag_query: Optional[TagQuery],
        offset: Optional[int],
        limit: Optional[int],
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> AsyncGenerator[Entry, None]:
        """Scan entries with pagination."""
        operation_name = "scan"
        LOGGER.debug(
            "[%s] Starting with profile_id=%s, category=%s, tag_query=%s, "
            "offset=%s, limit=%s, order_by=%s, descending=%s, table=%s",
            operation_name,
            profile_id,
            category,
            tag_query,
            offset,
            limit,
            order_by,
            descending,
            self.table,
        )

        try:
            await self._ensure_utf8(cursor)
            if order_by and order_by not in self.ALLOWED_ORDER_BY_COLUMNS:
                LOGGER.error(LOG_INVALID_ORDER_BY, operation_name, order_by)
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=(
                        LOG_INVALID_ORDER_BY % ("scan", order_by) + f". Allowed columns: "
                        f"{', '.join(self.ALLOWED_ORDER_BY_COLUMNS)}"
                    ),
                )

            sql_clause = "TRUE"
            params = []
            if tag_query:
                sql_clause, params = self.get_sql_clause(tag_query)
                LOGGER.debug(
                    LOG_GENERATED_SQL_CLAUSE,
                    operation_name,
                    sql_clause,
                    params,
                )

            order_column = order_by if order_by else "id"
            table_prefix = "t" if order_by in self.columns else "i"
            order_direction = "DESC" if descending else "ASC"
            LOGGER.debug(
                "[%s] Using ORDER BY %s.%s %s",
                operation_name,
                table_prefix,
                order_column,
                order_direction,
            )

            subquery = f"""
                SELECT i.id
                FROM {self.schema_context.qualify_table("items")} i
                JOIN {self.table} t ON i.id = t.item_id
                WHERE i.profile_id = %s AND i.category = %s
                AND (i.expiry IS NULL OR i.expiry > CURRENT_TIMESTAMP)
                AND {sql_clause}
                ORDER BY {table_prefix}.{order_column} {order_direction}
            """
            if limit is not None:
                subquery += " LIMIT %s"
                params.append(limit)
            if offset is not None:
                subquery += " OFFSET %s"
                params.append(offset)

            query = f"""
                SELECT i.id AS i_id, i.name AS i_name, i.value AS i_value, t.*
                FROM ({subquery}) AS sub
                JOIN {self.schema_context.qualify_table("items")} i ON sub.id = i.id
                JOIN {self.table} t ON i.id = t.item_id
                ORDER BY {table_prefix}.{order_column} {order_direction}
            """
            LOGGER.debug(
                "[%s] Executing query: %s with params: %s",
                operation_name,
                query,
                [profile_id, category] + params,
            )
            await cursor.execute(query, [profile_id, category] + params)

            columns = [desc[0] for desc in cursor.description]
            async for row in cursor:
                LOGGER.debug(LOG_FETCHED_ROW, operation_name, row)
                row_dict = dict(zip(columns, row))
                name = row_dict["i_name"]
                value = row_dict["i_value"]
                if isinstance(value, bytes):
                    value = value.decode("utf-8")
                    LOGGER.debug(LOG_DECODED_VALUE, operation_name, value)
                elif value is None:
                    LOGGER.warning(
                        LOG_VALUE_NONE_ID,
                        operation_name,
                        row_dict["i_id"],
                    )
                    value = ""
                tags = {
                    k: v
                    for k, v in row_dict.items()
                    if k not in ["i_id", "i_name", "i_value", "item_id", "item_name"]
                }
                tags = deserialize_tags(tags)
                yield Entry(category=category, name=name, value=value, tags=tags)
        except Exception as e:
            LOGGER.error(LOG_FAILED, operation_name, str(e))
            await cursor.connection.rollback()
            raise
        finally:
            if cursor.connection.pgconn.transaction_status != pq.TransactionStatus.IDLE:
                await cursor.connection.commit()

    async def scan_keyset(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        tag_query: Optional[TagQuery],
        last_id: Optional[int],
        limit: int,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> AsyncGenerator[Entry, None]:
        """Scan entries using keyset pagination."""
        operation_name = "scan_keyset"
        LOGGER.debug(
            "[%s] Starting with profile_id=%s, category=%s, tag_query=%s, "
            "last_id=%s, limit=%s, order_by=%s, descending=%s, table=%s",
            operation_name,
            profile_id,
            category,
            tag_query,
            last_id,
            limit,
            order_by,
            descending,
            self.table,
        )

        try:
            await self._ensure_utf8(cursor)
            if order_by and order_by not in self.ALLOWED_ORDER_BY_COLUMNS:
                LOGGER.error(LOG_INVALID_ORDER_BY, operation_name, order_by)
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=(
                        LOG_INVALID_ORDER_BY % ("scan", order_by) + f". Allowed columns: "
                        f"{', '.join(self.ALLOWED_ORDER_BY_COLUMNS)}"
                    ),
                )

            sql_clause = "TRUE"
            params = []
            if tag_query:
                sql_clause, params = self.get_sql_clause(tag_query)
                LOGGER.debug(
                    LOG_GENERATED_SQL_CLAUSE,
                    operation_name,
                    sql_clause,
                    params,
                )
            if last_id is not None:
                sql_clause += f" AND i.id {'<' if descending else '>'} %s"
                params.append(last_id)

            order_column = order_by if order_by else "id"
            table_prefix = "t" if order_by in self.columns else "i"
            order_direction = "DESC" if descending else "ASC"

            subquery = f"""
                SELECT i.id
                FROM {self.schema_context.qualify_table("items")} i
                JOIN {self.table} t ON i.id = t.item_id
                WHERE i.profile_id = %s AND i.category = %s
                AND (i.expiry IS NULL OR i.expiry > CURRENT_TIMESTAMP)
                AND {sql_clause}
                ORDER BY {table_prefix}.{order_column} {order_direction}
                LIMIT %s
            """
            subquery_params = [profile_id, category] + params + [limit]

            query = f"""
                SELECT i.id AS i_id, i.category, i.name AS i_name, i.value AS i_value, t.*
                FROM ({subquery}) AS sub
                JOIN {self.schema_context.qualify_table("items")} i ON sub.id = i.id
                JOIN {self.table} t ON i.id = t.item_id
                ORDER BY {table_prefix}.{order_column} {order_direction}
            """
            LOGGER.debug(
                "[%s] Executing query: %s with params: %s",
                operation_name,
                query,
                subquery_params,
            )
            await cursor.execute(query, subquery_params)

            columns = [desc[0] for desc in cursor.description]
            async for row in cursor:
                LOGGER.debug(LOG_FETCHED_ROW, operation_name, row)
                row_dict = dict(zip(columns, row))
                name = row_dict["i_name"]
                value = row_dict["i_value"]
                if isinstance(value, bytes):
                    value = value.decode("utf-8")
                    LOGGER.debug(LOG_DECODED_VALUE, operation_name, value)
                elif value is None:
                    LOGGER.warning(
                        LOG_VALUE_NONE_ID,
                        operation_name,
                        row_dict["i_id"],
                    )
                    value = ""
                tags = {
                    k: v
                    for k, v in row_dict.items()
                    if k not in ["i_id", "i_name", "i_value", "item_id", "item_name"]
                }
                tags = deserialize_tags(tags)
                yield Entry(category=category, name=name, value=value, tags=tags)
        except Exception as e:
            LOGGER.error(LOG_FAILED, operation_name, str(e))
            await cursor.connection.rollback()
            raise
        finally:
            if cursor.connection.pgconn.transaction_status != pq.TransactionStatus.IDLE:
                await cursor.connection.commit()

    def get_sql_clause(self, tag_query: TagQuery) -> Tuple[str, List[Any]]:
        """Generate SQL clause from tag query."""
        operation_name = "get_sql_clause"
        LOGGER.debug(
            "[%s] Starting with tag_query=%s, table=%s",
            operation_name,
            tag_query,
            self.table,
        )

        try:
            sql_clause, arguments = self.encoder.encode_query(tag_query)
            LOGGER.debug(
                LOG_GENERATED_SQL_CLAUSE_ARGS,
                operation_name,
                sql_clause,
                arguments,
            )
            return sql_clause, arguments
        except Exception as e:
            LOGGER.error(LOG_FAILED, operation_name, str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=f"Failed to generate SQL clause: {str(e)}",
            )
