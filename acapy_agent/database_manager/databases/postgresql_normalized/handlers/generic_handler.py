"""Module docstring."""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, List, Optional, Sequence, Tuple

from psycopg import AsyncCursor

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
LOG_RAW_VALUE = "[%s] Raw value type: %s, value: %r"
LOG_DECODED_VALUE = "[%s] Decoded value from bytes: %s"
LOG_VALUE_NONE = "[%s] value is None for item_id=%d"
LOG_PARSED_TAG_FILTER = "[%s] Parsed tag_filter JSON: %s"
LOG_GEN_SQL_PARAMS = "[%s] Generated SQL clause: %s, params: %s"
LOG_EXEC_SQL_PARAMS = "[%s] Executing query: %s with params: %s"


class GenericHandler(BaseHandler):
    """Handler for generic categories using items and a configurable tags table."""

    ALLOWED_ORDER_BY_COLUMNS = {"id", "name", "value"}
    EXPIRY_CLAUSE = "(i.expiry IS NULL OR i.expiry > CURRENT_TIMESTAMP)"

    def __init__(
        self,
        category: str = "default",
        tags_table_name: Optional[str] = None,
        schema_context: Optional[SchemaContext] = None,
    ):
        """Initialize GenericHandler with category and database configuration."""
        super().__init__(category)
        self.schema_context = schema_context or SchemaContext()
        self._tags_table_name = tags_table_name or "items_tags"  # Store unqualified name
        self.tags_table = self.schema_context.qualify_table(self._tags_table_name)
        self.encoder = encoder_factory.get_encoder(
            "postgresql",
            lambda x: x,
            lambda x: x,
            normalized=False,
            tags_table=self.tags_table,
        )
        LOGGER.debug(
            (
                "Initialized GenericHandler for category=%s, tags_table=%s "
                "[Version 2025-07-04]"
            ),
            category,
            self.tags_table,
        )

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
            self.tags_table = self.schema_context.qualify_table(self._tags_table_name)
            # Recreate encoder with updated tags_table
            self.encoder = encoder_factory.get_encoder(
                "postgresql",
                lambda x: x,
                lambda x: x,
                normalized=False,
                tags_table=self.tags_table,
            )
            LOGGER.debug(
                "[set_schema_context] Updated schema_context to %s, tags_table=%s",
                self.schema_context,
                self.tags_table,
            )

    def _validate_order_by(self, order_by: Optional[str]) -> None:
        if order_by and order_by not in self.ALLOWED_ORDER_BY_COLUMNS:
            LOGGER.error("[order_by] Invalid column: %s", order_by)
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=(
                    f"Invalid order_by column: {order_by}. Allowed columns: "
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
        expiry_ms: int,
    ) -> None:
        """Insert a new item into the database."""
        operation_name = "insert"
        LOGGER.debug(
            (
                "[%s] Starting with profile_id=%d, category=%s, name=%s, "
                "tags=%s, expiry_ms=%s, tags_table=%s"
            ),
            operation_name,
            profile_id,
            category,
            name,
            tags,
            expiry_ms,
            self.tags_table,
        )

        expiry = None
        if expiry_ms:
            expiry = datetime.now(timezone.utc) + timedelta(milliseconds=expiry_ms)
            LOGGER.debug("[%s] Calculated expiry: %s", operation_name, expiry)

        # Convert bytes to string if necessary, as items.value is TEXT
        LOGGER.debug(LOG_RAW_VALUE, operation_name, type(value), value)
        if isinstance(value, bytes):
            value = value.decode("utf-8")
            LOGGER.debug(LOG_DECODED_VALUE, operation_name, value)

        await cursor.execute(
            f"""
            INSERT INTO {self.schema_context.qualify_table("items")}
            (profile_id, kind, category, name, value, expiry)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (profile_id, category, name) DO NOTHING
            RETURNING id
        """,
            (profile_id, 0, category, name, value, expiry),
        )
        row = await cursor.fetchone()
        if not row:
            LOGGER.error(
                "[%s] Duplicate entry detected for category=%s, name=%s",
                operation_name,
                category,
                name,
            )
            raise DatabaseError(
                code=DatabaseErrorCode.DUPLICATE_ITEM_ENTRY_ERROR,
                message=(f"Duplicate entry for category '{category}' and name '{name}'"),
            )
        item_id = row[0]
        LOGGER.debug("[%s] Inserted item with item_id=%d", operation_name, item_id)

        for tag_name, tag_value in tags.items():
            if isinstance(tag_value, set):
                tag_value = json.dumps(list(tag_value))
                LOGGER.debug(
                    "[%s] Serialized tag %s (set) to JSON: %s",
                    operation_name,
                    tag_name,
                    tag_value,
                )
            elif isinstance(tag_value, (list, dict)):
                tag_value = json.dumps(tag_value)
                LOGGER.debug(
                    "[%s] Serialized tag %s to JSON: %s",
                    operation_name,
                    tag_name,
                    tag_value,
                )
            await cursor.execute(
                f"""
                INSERT INTO {self.tags_table} (item_id, name, value)
                VALUES (%s, %s, %s)
            """,
                (item_id, tag_name, tag_value),
            )
            LOGGER.debug(
                "[%s] Inserted tag %s=%s for item_id=%d",
                operation_name,
                tag_name,
                tag_value,
                item_id,
            )

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
        """Replace an existing item in the database."""
        operation_name = "replace"
        LOGGER.debug(
            (
                "[%s] Starting with profile_id=%d, category=%s, name=%s, "
                "value=%r, tags=%s, expiry_ms=%s, tags_table=%s"
            ),
            operation_name,
            profile_id,
            category,
            name,
            value,
            tags,
            expiry_ms,
            self.tags_table,
        )

        expiry = None
        if expiry_ms is not None:
            expiry = datetime.now(timezone.utc) + timedelta(milliseconds=expiry_ms)
            LOGGER.debug("[%s] Calculated expiry: %s", operation_name, expiry)

        # Convert bytes to string if necessary, as items.value is TEXT
        LOGGER.debug(LOG_RAW_VALUE, operation_name, type(value), value)
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
        if row:
            item_id = row[0]
            LOGGER.debug("[%s] Found item with item_id=%d", operation_name, item_id)

            await cursor.execute(
                f"""
                UPDATE {self.schema_context.qualify_table("items")}
                SET value = %s, expiry = %s
                WHERE id = %s
            """,
                (value, expiry, item_id),
            )
            LOGGER.debug(
                "[%s] Updated item value and expiry for item_id=%d",
                operation_name,
                item_id,
            )

            await cursor.execute(
                f"DELETE FROM {self.tags_table} WHERE item_id = %s", (item_id,)
            )
            LOGGER.debug(
                "[%s] Deleted existing tags for item_id=%d", operation_name, item_id
            )

            for tag_name, tag_value in tags.items():
                if isinstance(tag_value, set):
                    tag_value = json.dumps(list(tag_value))
                    LOGGER.debug(
                        "[%s] Serialized tag %s (set) to JSON: %s",
                        operation_name,
                        tag_name,
                        tag_value,
                    )
                elif isinstance(tag_value, (list, dict)):
                    tag_value = json.dumps(tag_value)
                    LOGGER.debug(
                        "[%s] Serialized tag %s to JSON: %s",
                        operation_name,
                        tag_name,
                        tag_value,
                    )
                await cursor.execute(
                    f"""
                    INSERT INTO {self.tags_table} (item_id, name, value)
                    VALUES (%s, %s, %s)
                """,
                    (item_id, tag_name, tag_value),
                )
                LOGGER.debug(
                    "[%s] Inserted tag %s=%s for item_id=%d",
                    operation_name,
                    tag_name,
                    tag_value,
                    item_id,
                )
        else:
            LOGGER.error(
                "[%s] Record not found for category=%s, name=%s",
                operation_name,
                category,
                name,
            )
            raise DatabaseError(
                code=DatabaseErrorCode.RECORD_NOT_FOUND,
                message=(f"Record not found for category '{category}' and name '{name}'"),
            )

    async def fetch(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        name: str,
        tag_filter: str | dict,
        for_update: bool,
    ) -> Optional[Entry]:
        """Fetch a single item from the database."""
        operation_name = "fetch"
        LOGGER.debug(
            (
                "[%s] Starting with profile_id=%d, category=%s, name=%s, "
                "tag_filter=%s, for_update=%s, tags_table=%s"
            ),
            operation_name,
            profile_id,
            category,
            name,
            tag_filter,
            for_update,
            self.tags_table,
        )

        params = [profile_id, category, name]
        query = f"""
            SELECT id, value FROM {self.schema_context.qualify_table("items")}
            WHERE profile_id = %s AND category = %s AND name = %s
            AND (expiry IS NULL OR expiry > CURRENT_TIMESTAMP)
        """
        if for_update:
            query += " FOR UPDATE"

        await cursor.execute(query, params)
        row = await cursor.fetchone()
        if not row:
            LOGGER.debug(
                "[%s] No item found for category=%s, name=%s",
                operation_name,
                category,
                name,
            )
            return None
        item_id, item_value = row
        # Explicitly decode item_value if it is bytes
        LOGGER.debug(
            "[%s] Raw item_value type: %s, value: %r",
            operation_name,
            type(item_value),
            item_value,
        )
        if isinstance(item_value, bytes):
            item_value = item_value.decode("utf-8")
            LOGGER.debug(
                "[%s] Decoded item_value from bytes: %s", operation_name, item_value
            )
        elif item_value is None:
            LOGGER.warning(
                "[%s] item_value is None for item_id=%d", operation_name, item_id
            )
            item_value = ""
        LOGGER.debug("[%s] Found item with item_id=%d", operation_name, item_id)

        if tag_filter:
            LOGGER.debug(
                "[%s] Processing tag_filter: %s, type: %s",
                operation_name,
                tag_filter,
                type(tag_filter),
            )
            if isinstance(tag_filter, str):
                tag_filter = json.loads(tag_filter)
                LOGGER.debug(LOG_PARSED_TAG_FILTER, operation_name, tag_filter)
            wql_query = query_from_json(tag_filter)
            tag_query = query_to_tagquery(wql_query)
            sql_clause, clause_params = self.get_sql_clause(tag_query)
            LOGGER.debug(LOG_GEN_SQL_PARAMS, operation_name, sql_clause, clause_params)

            query = f"""
                SELECT i.id, i.value
                FROM {self.schema_context.qualify_table("items")} i
                WHERE i.id = %s AND {sql_clause}
            """
            await cursor.execute(query, [item_id] + clause_params)
            row = await cursor.fetchone()
            if not row:
                LOGGER.debug(
                    "[%s] No item matches tag_filter for item_id=%d",
                    operation_name,
                    item_id,
                )
                return None
            item_id, item_value = row
            # Explicitly decode item_value if it is bytes
            LOGGER.debug(
                "[%s] Raw item_value (tag_filter) type: %s, value: %r",
                operation_name,
                type(item_value),
                item_value,
            )
            if isinstance(item_value, bytes):
                item_value = item_value.decode("utf-8")
                LOGGER.debug(
                    "[%s] Decoded item_value (tag_filter) from bytes: %s",
                    operation_name,
                    item_value,
                )
            elif item_value is None:
                LOGGER.warning(
                    "[%s] item_value (tag_filter) is None for item_id=%d",
                    operation_name,
                    item_id,
                )
                item_value = ""
            LOGGER.debug(
                "[%s] Item matches tag_filter for item_id=%d", operation_name, item_id
            )

            await cursor.execute(
                f"SELECT name, value FROM {self.tags_table} WHERE item_id = %s",
                (item_id,),
            )
            tag_rows = await cursor.fetchall()
            tags = {}
            for tag_name, tag_value in tag_rows:
                if isinstance(tag_value, str) and (
                    tag_value.startswith("[") or tag_value.startswith("{")
                ):
                    try:
                        tag_value = json.loads(tag_value)
                    except json.JSONDecodeError:
                        pass
                tags[tag_name] = tag_value
            LOGGER.debug(
                "[%s] Fetched %d tags for item_id=%d: %s",
                operation_name,
                len(tags),
                item_id,
                tags,
            )

            entry = Entry(category=category, name=name, value=item_value, tags=tags)
            LOGGER.debug("[%s] Returning entry: %s", operation_name, entry)
            return entry
        else:
            # No tag_filter - return entry with empty tags
            entry = Entry(category=category, name=name, value=item_value, tags={})
            LOGGER.debug(
                "[%s] Returning entry (no tag_filter): %s", operation_name, entry
            )
            return entry

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
        """Fetch all items matching the given criteria."""
        operation_name = "fetch_all"
        LOGGER.debug(
            (
                "[%s] Starting with profile_id=%d, category=%s, tag_filter=%s, "
                "limit=%s, for_update=%s, order_by=%s, descending=%s, tags_table=%s"
            ),
            operation_name,
            profile_id,
            category,
            tag_filter,
            limit,
            for_update,
            order_by,
            descending,
            self.tags_table,
        )

        self._validate_order_by(order_by)

        sql_clause = "TRUE"
        params = [profile_id, category]
        if tag_filter:
            if isinstance(tag_filter, str):
                tag_filter = json.loads(tag_filter)
                LOGGER.debug(LOG_PARSED_TAG_FILTER, operation_name, tag_filter)
            wql_query = query_from_json(tag_filter)
            tag_query = query_to_tagquery(wql_query)
            sql_clause, clause_params = self.get_sql_clause(tag_query)
            LOGGER.debug(LOG_GEN_SQL_PARAMS, operation_name, sql_clause, clause_params)
            params.extend(clause_params)

        order_column = order_by if order_by else "id"
        order_direction = "DESC" if descending else "ASC"
        subquery = f"""
            SELECT i.id, i.category, i.name, i.value
            FROM {self.schema_context.qualify_table("items")} i
            WHERE i.profile_id = %s AND i.category = %s
            AND {self.EXPIRY_CLAUSE}
            AND {sql_clause}
            ORDER BY i.{order_column} {order_direction}
        """
        subquery_params = params
        if limit is not None:
            subquery += " LIMIT %s"
            subquery_params.append(limit)

        query = f"""
            SELECT sub.id, sub.category, sub.name, sub.value, t.name, t.value
            FROM ({subquery}) sub
            LEFT JOIN {self.tags_table} t ON sub.id = t.item_id
            ORDER BY sub.{order_column} {order_direction}
        """
        await cursor.execute(query, subquery_params)
        LOGGER.debug("[%s] Query executed successfully", operation_name)

        entries = []
        current_item_id = None
        current_entry = None
        async for row in cursor:
            item_id, category, name, value, tag_name, tag_value = row
            # Explicitly decode value if it is bytes
            LOGGER.debug(
                LOG_RAW_VALUE,
                operation_name,
                type(value),
                value,
            )
            if isinstance(value, bytes):
                value = value.decode("utf-8")
                LOGGER.debug(LOG_DECODED_VALUE, operation_name, value)
            elif value is None:
                LOGGER.warning(LOG_VALUE_NONE, operation_name, item_id)
                value = ""
            if item_id != current_item_id:
                if current_entry:
                    entries.append(current_entry)
                current_item_id = item_id
                current_entry = Entry(category=category, name=name, value=value, tags={})
            if tag_name is not None:
                if isinstance(tag_value, str) and (
                    tag_value.startswith("[") or tag_value.startswith("{")
                ):
                    try:
                        tag_value = json.loads(tag_value)
                    except json.JSONDecodeError:
                        # If tag_value is not valid JSON, leave it as the original string.
                        LOGGER.warning(
                            "[%s] Failed to decode tag_value as JSON: %r",
                            operation_name,
                            tag_value,
                        )
                current_entry.tags[tag_name] = tag_value
        if current_entry:
            entries.append(current_entry)
        LOGGER.debug("[%s] Fetched %d entries", operation_name, len(entries))
        return entries

    async def count(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        tag_filter: str | dict,
    ) -> int:
        """Count items matching the given criteria."""
        operation_name = "count"
        LOGGER.debug(
            "[%s] Starting with profile_id=%d, category=%s, tag_filter=%s, tags_table=%s",
            operation_name,
            profile_id,
            category,
            tag_filter,
            self.tags_table,
        )

        sql_clause = "TRUE"
        params = [profile_id, category]
        if tag_filter:
            if isinstance(tag_filter, str):
                tag_filter = json.loads(tag_filter)
            wql_query = query_from_json(tag_filter)
            tag_query = query_to_tagquery(wql_query)
            sql_clause, clause_params = self.get_sql_clause(tag_query)
            params.extend(clause_params)

        query = f"""
            SELECT COUNT(*) FROM {self.schema_context.qualify_table("items")} i
            WHERE i.profile_id = %s AND i.category = %s
            AND (i.expiry IS NULL OR i.expiry > CURRENT_TIMESTAMP)
            AND {sql_clause}
        """
        await cursor.execute(query, params)
        count = (await cursor.fetchone())[0]
        LOGGER.debug("[%s] Counted %d entries", operation_name, count)
        return count

    async def remove(
        self, cursor: AsyncCursor, profile_id: int, category: str, name: str
    ) -> None:
        """Remove a single item from the database."""
        operation_name = "remove"
        LOGGER.debug(
            "[%s] Starting with profile_id=%d, category=%s, name=%s, tags_table=%s",
            operation_name,
            profile_id,
            category,
            name,
            self.tags_table,
        )

        await cursor.execute(
            f"""
            DELETE FROM {self.schema_context.qualify_table("items")}
            WHERE profile_id = %s AND category = %s AND name = %s
        """,
            (profile_id, category, name),
        )
        if cursor.rowcount == 0:
            raise DatabaseError(
                code=DatabaseErrorCode.RECORD_NOT_FOUND,
                message=(f"Record not found for category '{category}' and name '{name}'"),
            )

    async def remove_all(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        tag_filter: str | dict,
    ) -> int:
        """Remove all items matching the given criteria."""
        operation_name = "remove_all"
        LOGGER.debug(
            "[%s] Starting with profile_id=%d, category=%s, tag_filter=%s, tags_table=%s",
            operation_name,
            profile_id,
            category,
            tag_filter,
            self.tags_table,
        )

        sql_clause = "TRUE"
        params = [profile_id, category]
        if tag_filter:
            if isinstance(tag_filter, str):
                tag_filter = json.loads(tag_filter)
            wql_query = query_from_json(tag_filter)
            tag_query = query_to_tagquery(wql_query)
            sql_clause, clause_params = self.get_sql_clause(tag_query)
            params.extend(clause_params)

        query = f"""
                DELETE FROM {self.schema_context.qualify_table("items")} WHERE id IN (
                    SELECT i.id FROM {self.schema_context.qualify_table("items")} i
                    WHERE i.profile_id = %s AND i.category = %s
                    AND (i.expiry IS NULL OR i.expiry > CURRENT_TIMESTAMP)
                    AND {sql_clause}
                )
        """
        await cursor.execute(query, params)
        rowcount = cursor.rowcount
        LOGGER.debug("[%s] Removed %d entries", operation_name, rowcount)
        return rowcount

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
        """Scan items matching the given criteria."""
        operation_name = "scan"
        LOGGER.debug(
            (
                "[%s] Starting with profile_id=%s, category=%s, tag_query=%s, "
                "offset=%s, limit=%s, order_by=%s, descending=%s, tags_table=%s"
            ),
            operation_name,
            profile_id,
            category,
            tag_query,
            offset,
            limit,
            order_by,
            descending,
            self.tags_table,
        )

        self._validate_order_by(order_by)

        sql_clause = "TRUE"
        params = [profile_id, category]
        if tag_query:
            sql_clause, clause_params = self.get_sql_clause(tag_query)
            LOGGER.debug(
                LOG_GEN_SQL_PARAMS,
                operation_name,
                sql_clause,
                clause_params,
            )
            params.extend(clause_params)

        order_column = order_by if order_by else "id"
        order_direction = "DESC" if descending else "ASC"
        subquery = f"""
                SELECT i.id, i.category, i.name, i.value
                FROM {self.schema_context.qualify_table("items")} i
                WHERE i.profile_id = %s AND i.category = %s
                AND {self.EXPIRY_CLAUSE}
                AND {sql_clause}
        """
        subquery_params = params
        if limit is not None:
            subquery += f" ORDER BY i.{order_column} {order_direction} LIMIT %s"
            subquery_params.append(limit)
        elif offset is not None:
            subquery += f" ORDER BY i.{order_column} {order_direction} OFFSET %s"
            subquery_params.append(offset)

        query = f"""
            SELECT sub.id, sub.category, sub.name, sub.value, t.name, t.value
            FROM ({subquery}) sub
            LEFT JOIN {self.tags_table} t ON sub.id = t.item_id
            ORDER BY sub.{order_column} {order_direction}
        """
        LOGGER.debug(LOG_EXEC_SQL_PARAMS, operation_name, query, subquery_params)
        await cursor.execute(query, subquery_params)
        current_item_id = None
        current_entry = None
        async for row in cursor:
            item_id, category, name, value, tag_name, tag_value = row
            # Explicitly decode value if it is bytes
            LOGGER.debug(
                LOG_RAW_VALUE,
                operation_name,
                type(value),
                value,
            )
            if isinstance(value, bytes):
                value = value.decode("utf-8")
                LOGGER.debug(LOG_DECODED_VALUE, operation_name, value)
            elif value is None:
                LOGGER.warning(LOG_VALUE_NONE, operation_name, item_id)
                value = ""
            if item_id != current_item_id:
                if current_entry:
                    yield current_entry
                current_item_id = item_id
                current_entry = Entry(category=category, name=name, value=value, tags={})
            if tag_name is not None:
                current_entry.tags[tag_name] = tag_value
        if current_entry:
            yield current_entry

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
        """Scan items using keyset pagination."""
        operation_name = "scan_keyset"
        LOGGER.debug(
            (
                "[%s] Starting with profile_id=%s, category=%s, tag_query=%s, "
                "last_id=%s, limit=%s, order_by=%s, descending=%s, tags_table=%s"
            ),
            operation_name,
            profile_id,
            category,
            tag_query,
            last_id,
            limit,
            order_by,
            descending,
            self.tags_table,
        )

        if order_by and order_by not in self.ALLOWED_ORDER_BY_COLUMNS:
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=(
                    f"Invalid order_by column: {order_by}. Allowed columns: "
                    f"{', '.join(self.ALLOWED_ORDER_BY_COLUMNS)}"
                ),
            )

        sql_clause = "TRUE"
        params = [profile_id, category]
        if tag_query:
            sql_clause, clause_params = self.get_sql_clause(tag_query)
            LOGGER.debug(
                LOG_GEN_SQL_PARAMS,
                operation_name,
                sql_clause,
                clause_params,
            )
            params.extend(clause_params)
        if last_id is not None:
            sql_clause += f" AND i.id {'<' if descending else '>'} %s"
            params.append(last_id)

        order_column = order_by if order_by else "id"
        order_direction = "DESC" if descending else "ASC"
        subquery = f"""
                SELECT i.id, i.category, i.name, i.value
                FROM {self.schema_context.qualify_table("items")} i
                WHERE i.profile_id = %s AND i.category = %s
                AND (i.expiry IS NULL OR i.expiry > CURRENT_TIMESTAMP)
                AND {sql_clause}
                ORDER BY i.{order_column} {order_direction}, i.id {order_direction}
                LIMIT %s
        """
        subquery_params = params + [limit]

        query = f"""
            SELECT sub.id, sub.category, sub.name, sub.value, t.name, t.value
            FROM ({subquery}) sub
            LEFT JOIN {self.tags_table} t ON sub.id = t.item_id
            ORDER BY sub.{order_column} {order_direction}, sub.id {order_direction}
        """
        LOGGER.debug(
            "[%s] Executing query: %s with params: %s",
            operation_name,
            query,
            subquery_params,
        )
        await cursor.execute(query, subquery_params)
        current_item_id = None
        current_entry = None
        async for row in cursor:
            item_id, category, name, value, tag_name, tag_value = row
            # Explicitly decode value if it is bytes
            LOGGER.debug(
                LOG_RAW_VALUE,
                operation_name,
                type(value),
                value,
            )
            if isinstance(value, bytes):
                value = value.decode("utf-8")
                LOGGER.debug(LOG_DECODED_VALUE, operation_name, value)
            if item_id != current_item_id:
                if current_entry:
                    yield current_entry
                current_item_id = item_id
                current_entry = Entry(category=category, name=name, value=value, tags={})
            if tag_name is not None:
                current_entry.tags[tag_name] = tag_value
        if current_entry:
            yield current_entry

    def get_sql_clause(self, tag_query: TagQuery) -> Tuple[str, List[Any]]:
        """Generate SQL clause for tag queries."""
        operation_name = "get_sql_clause"
        LOGGER.debug(
            "[%s] Starting with tag_query=%s, tags_table=%s",
            operation_name,
            tag_query,
            self.tags_table,
        )

        try:
            sql_clause, arguments = self.encoder.encode_query(tag_query)
            LOGGER.debug(
                "[%s] Generated SQL clause: %s, arguments: %s",
                operation_name,
                sql_clause,
                arguments,
            )
            return sql_clause, arguments
        except Exception as e:
            LOGGER.error(LOG_FAILED, operation_name, str(e))
            raise
