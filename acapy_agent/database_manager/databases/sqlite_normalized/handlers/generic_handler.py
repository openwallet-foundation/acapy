from .base_handler import BaseHandler
from ....db_types import Entry
from ....wql_normalized.tags import TagQuery, query_to_tagquery
from ....wql_normalized.query import query_from_json
from ....wql_normalized.encoders import encoder_factory
from ...errors import DatabaseError, DatabaseErrorCode
import sqlite3
from typing import Optional, Sequence, Union, List, Tuple, Any, Generator
import json
import logging
from datetime import datetime, timedelta, timezone

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.CRITICAL + 1)


class GenericHandler(BaseHandler):
    """Handler for generic categories using items and a configurable tags table."""

    ALLOWED_ORDER_BY_COLUMNS = {"id", "name", "value"}

    def __init__(self, category: str = "default", tags_table_name: Optional[str] = None):
        super().__init__(category)
        self.tags_table = tags_table_name or "items_tags"
        self.encoder = encoder_factory.get_encoder(
            "sqlite",
            lambda x: x,
            lambda x: x,
            normalized=False,
            tags_table=self.tags_table,
        )
        LOGGER.debug(
            "Initialized GenericHandler for category=%s, tags_table=%s",
            category,
            self.tags_table,
        )

    def insert(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        name: str,
        value: Union[str, bytes],
        tags: dict,
        expiry_ms: int,
    ) -> None:
        operation_name = "insert"
        LOGGER.debug(
            "[%s] Starting with profile_id=%d, category=%s, name=%s, tags=%s, expiry_ms=%s, tags_table=%s",
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
            expiry = (
                datetime.now(timezone.utc) + timedelta(milliseconds=expiry_ms)
            ).isoformat()
            LOGGER.debug("[%s] Calculated expiry: %s", operation_name, expiry)

        try:
            cursor.execute(
                """
                INSERT OR IGNORE INTO items (profile_id, kind, category, name, value, expiry)
                VALUES (?, 0, ?, ?, ?, ?)
            """,
                (profile_id, category, name, value, expiry),
            )
            if cursor.rowcount == 0:
                LOGGER.error(
                    "[%s] Duplicate entry detected for category=%s, name=%s",
                    operation_name,
                    category,
                    name,
                )
                raise DatabaseError(
                    code=DatabaseErrorCode.DUPLICATE_ITEM_ENTRY_ERROR,
                    message=f"Duplicate entry for category '{category}' and name '{name}'",
                )
            item_id = cursor.lastrowid
            LOGGER.debug("[%s] Inserted item with item_id=%d", operation_name, item_id)

            for tag_name, tag_value in tags.items():
                if isinstance(tag_value, (list, dict)):
                    tag_value = json.dumps(tag_value)
                    LOGGER.debug(
                        "[%s] Serialized tag %s to JSON: %s",
                        operation_name,
                        tag_name,
                        tag_value,
                    )
                cursor.execute(
                    f"""
                    INSERT INTO {self.tags_table} (item_id, name, value)
                    VALUES (?, ?, ?)
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
        except Exception as e:
            LOGGER.error("[%s] Failed: %s", operation_name, str(e))
            raise

        LOGGER.debug("[%s] Completed", operation_name)

    def replace(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        name: str,
        value: Union[str, bytes],
        tags: dict,
        expiry_ms: int,
    ) -> None:
        operation_name = "replace"
        LOGGER.debug(
            "[%s] Starting with profile_id=%d, category=%s, name=%s, tags=%s, expiry_ms=%s, tags_table=%s",
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
            expiry = (
                datetime.now(timezone.utc) + timedelta(milliseconds=expiry_ms)
            ).isoformat()
            LOGGER.debug("[%s] Calculated expiry: %s", operation_name, expiry)

        try:
            cursor.execute(
                """
                SELECT id FROM items
                WHERE profile_id = ? AND category = ? AND name = ?
            """,
                (profile_id, category, name),
            )
            row = cursor.fetchone()
            if row:
                item_id = row[0]
                LOGGER.debug("[%s] Found item with item_id=%d", operation_name, item_id)

                cursor.execute(
                    """
                    UPDATE items SET value = ?, expiry = ?
                    WHERE id = ?
                """,
                    (value, expiry, item_id),
                )
                LOGGER.debug(
                    "[%s] Updated item value and expiry for item_id=%d",
                    operation_name,
                    item_id,
                )

                cursor.execute(
                    f"DELETE FROM {self.tags_table} WHERE item_id = ?", (item_id,)
                )
                LOGGER.debug(
                    "[%s] Deleted existing tags for item_id=%d", operation_name, item_id
                )

                for tag_name, tag_value in tags.items():
                    if isinstance(tag_value, (list, dict)):
                        tag_value = json.dumps(tag_value)
                        LOGGER.debug(
                            "[%s] Serialized tag %s to JSON: %s",
                            operation_name,
                            tag_name,
                            tag_value,
                        )
                    cursor.execute(
                        f"""
                        INSERT INTO {self.tags_table} (item_id, name, value)
                        VALUES (?, ?, ?)
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
                    message=f"Record not found for category '{category}' and name '{name}'",
                )
        except Exception as e:
            LOGGER.error("[%s] Failed: %s", operation_name, str(e))
            raise

        LOGGER.debug("[%s] Completed", operation_name)

    def fetch(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        name: str,
        tag_filter: Union[str, dict],
        for_update: bool,
    ) -> Optional[Entry]:
        operation_name = "fetch"
        LOGGER.debug(
            "[%s] Starting with profile_id=%d, category=%s, name=%s, tag_filter=%s, for_update=%s, tags_table=%s",
            operation_name,
            profile_id,
            category,
            name,
            tag_filter,
            for_update,
            self.tags_table,
        )

        try:
            cursor.execute(
                """
                SELECT id, value FROM items
                WHERE profile_id = ? AND category = ? AND name = ?
                AND (expiry IS NULL OR datetime(expiry) > CURRENT_TIMESTAMP)
            """,
                (profile_id, category, name),
            )
            row = cursor.fetchone()
            if not row:
                LOGGER.debug(
                    "[%s] No item found for category=%s, name=%s",
                    operation_name,
                    category,
                    name,
                )
                return None
            item_id, item_value = row
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
                    LOGGER.debug(
                        "[%s] Parsed tag_filter JSON: %s", operation_name, tag_filter
                    )
                wql_query = query_from_json(tag_filter)
                tag_query = query_to_tagquery(wql_query)
                sql_clause, params = self.get_sql_clause(tag_query)
                LOGGER.debug(
                    "[%s] Generated SQL clause for tag_query: %s, params: %s",
                    operation_name,
                    sql_clause,
                    params,
                )

                query = f"""
                    SELECT i.id, i.value
                    FROM items i
                    WHERE i.id = ? AND {sql_clause}
                """
                cursor.execute(query, [item_id] + params)
                row = cursor.fetchone()
                if not row:
                    LOGGER.debug(
                        "[%s] No item matches tag_filter for item_id=%d",
                        operation_name,
                        item_id,
                    )
                    return None
                item_id, item_value = row
                LOGGER.debug(
                    "[%s] Item matches tag_filter for item_id=%d", operation_name, item_id
                )

            cursor.execute(
                f"SELECT name, value FROM {self.tags_table} WHERE item_id = ?", (item_id,)
            )
            tags = {name: value for name, value in cursor.fetchall()}
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
        except Exception as e:
            LOGGER.error("[%s] Failed: %s", operation_name, str(e))
            raise

        LOGGER.debug("[%s] Completed", operation_name)

    def fetch_all(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        tag_filter: Union[str, dict],
        limit: int,
        for_update: bool,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> Sequence[Entry]:
        operation_name = "fetch_all"
        LOGGER.debug(
            "[%s] Starting with profile_id=%d, category=%s, tag_filter=%s, limit=%s, for_update=%s, order_by=%s, descending=%s, tags_table=%s",
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

        try:
            if order_by and order_by not in self.ALLOWED_ORDER_BY_COLUMNS:
                LOGGER.error("[%s] Invalid order_by column: %s", operation_name, order_by)
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=f"Invalid order_by column: {order_by}. Allowed columns: {', '.join(self.ALLOWED_ORDER_BY_COLUMNS)}",
                )

            if tag_filter:
                LOGGER.debug(
                    "[%s] Processing tag_filter: %s, type: %s",
                    operation_name,
                    tag_filter,
                    type(tag_filter),
                )
                if isinstance(tag_filter, str):
                    tag_filter = json.loads(tag_filter)
                    LOGGER.debug(
                        "[%s] Parsed tag_filter JSON: %s", operation_name, tag_filter
                    )
                wql_query = query_from_json(tag_filter)
                tag_query = query_to_tagquery(wql_query)
                sql_clause, params = self.get_sql_clause(tag_query)
                LOGGER.debug(
                    "[%s] Generated SQL clause: %s, params: %s",
                    operation_name,
                    sql_clause,
                    params,
                )
            else:
                sql_clause = "1=1"
                params = []
                LOGGER.debug(
                    "[%s] No tag_filter provided, using default SQL clause: %s",
                    operation_name,
                    sql_clause,
                )

            order_column = order_by if order_by else "id"
            order_direction = "DESC" if descending else "ASC"
            subquery = f"""
                SELECT i.id, i.category, i.name, i.value
                FROM items i
                WHERE i.profile_id = ? AND i.category = ?
                AND (i.expiry IS NULL OR datetime(i.expiry) > CURRENT_TIMESTAMP)
                AND {sql_clause}
                ORDER BY i.{order_column} {order_direction}
            """
            if limit is not None:
                subquery += " LIMIT ?"
                params.append(limit)

            query = f"""
                SELECT sub.id, sub.category, sub.name, sub.value, t.name, t.value
                FROM ({subquery}) sub
                LEFT JOIN {self.tags_table} t ON sub.id = t.item_id
                ORDER BY sub.{order_column} {order_direction}
            """
            cursor.execute(query, [profile_id, category] + params)
            LOGGER.debug("[%s] Query executed successfully", operation_name)

            entries = []
            current_item_id = None
            current_entry = None
            for row in cursor:
                item_id, category, name, value, tag_name, tag_value = row
                if item_id != current_item_id:
                    if current_entry:
                        entries.append(current_entry)
                    current_item_id = item_id
                    current_entry = Entry(
                        category=category, name=name, value=value, tags={}
                    )
                if tag_name is not None:
                    current_entry.tags[tag_name] = tag_value
            if current_entry:
                entries.append(current_entry)
            return entries
        except Exception as e:
            LOGGER.error("[%s] Failed: %s", operation_name, str(e))
            raise

    def count(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        tag_filter: Union[str, dict],
    ) -> int:
        operation_name = "count"
        LOGGER.debug(
            "[%s] Starting with profile_id=%d, category=%s, tag_filter=%s, tags_table=%s",
            operation_name,
            profile_id,
            category,
            tag_filter,
            self.tags_table,
        )

        try:
            if tag_filter:
                if isinstance(tag_filter, str):
                    tag_filter = json.loads(tag_filter)
                wql_query = query_from_json(tag_filter)
                tag_query = query_to_tagquery(wql_query)
                sql_clause, params = self.get_sql_clause(tag_query)
            else:
                sql_clause = "1=1"
                params = []

            query = f"""
                SELECT COUNT(*) FROM items i
                WHERE i.profile_id = ? AND i.category = ?
                AND (i.expiry IS NULL OR datetime(i.expiry) > CURRENT_TIMESTAMP)
                AND {sql_clause}
            """
            cursor.execute(query, [profile_id, category] + params)
            return cursor.fetchone()[0]
        except Exception as e:
            LOGGER.error("[%s] Failed: %s", operation_name, str(e))
            raise

    def remove(
        self, cursor: sqlite3.Cursor, profile_id: int, category: str, name: str
    ) -> None:
        operation_name = "remove"
        LOGGER.debug(
            "[%s] Starting with profile_id=%d, category=%s, name=%s, tags_table=%s",
            operation_name,
            profile_id,
            category,
            name,
            self.tags_table,
        )

        try:
            cursor.execute(
                """
                DELETE FROM items
                WHERE profile_id = ? AND category = ? AND name = ?
            """,
                (profile_id, category, name),
            )
            if cursor.rowcount == 0:
                raise DatabaseError(
                    code=DatabaseErrorCode.RECORD_NOT_FOUND,
                    message=f"Record not found for category '{category}' and name '{name}'",
                )
        except Exception as e:
            LOGGER.error("[%s] Failed: %s", operation_name, str(e))
            raise

    def remove_all(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        tag_filter: Union[str, dict],
    ) -> int:
        operation_name = "remove_all"
        LOGGER.debug(
            "[%s] Starting with profile_id=%d, category=%s, tag_filter=%s, tags_table=%s",
            operation_name,
            profile_id,
            category,
            tag_filter,
            self.tags_table,
        )

        try:
            if tag_filter:
                if isinstance(tag_filter, str):
                    tag_filter = json.loads(tag_filter)
                wql_query = query_from_json(tag_filter)
                tag_query = query_to_tagquery(wql_query)
                sql_clause, params = self.get_sql_clause(tag_query)
            else:
                sql_clause = "1=1"
                params = []

            query = f"""
                DELETE FROM items WHERE id IN (
                    SELECT i.id FROM items i
                    WHERE i.profile_id = ? AND i.category = ?
                    AND (i.expiry IS NULL OR datetime(i.expiry) > CURRENT_TIMESTAMP)
                    AND {sql_clause}
                )
            """
            cursor.execute(query, [profile_id, category] + params)
            return cursor.rowcount
        except Exception as e:
            LOGGER.error("[%s] Failed: %s", operation_name, str(e))
            raise

    def scan(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        tag_query: Optional[TagQuery],
        offset: Optional[int],
        limit: Optional[int],
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> Generator[Entry, None, None]:
        operation_name = "scan"
        LOGGER.debug(
            "[%s] Starting with profile_id=%s, category=%s, tag_query=%s, offset=%s, limit=%s, order_by=%s, descending=%s, tags_table=%s",
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

        try:
            if order_by and order_by not in self.ALLOWED_ORDER_BY_COLUMNS:
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=f"Invalid order_by column: {order_by}. Allowed columns: {', '.join(self.ALLOWED_ORDER_BY_COLUMNS)}",
                )

            sql_clause = "1=1"
            params = []
            if tag_query:
                sql_clause, params = self.get_sql_clause(tag_query)

            order_column = order_by if order_by else "id"
            order_direction = "DESC" if descending else "ASC"
            subquery = f"""
                SELECT i.id, i.category, i.name, i.value
                FROM items i
                WHERE i.profile_id = ? AND i.category = ?
                AND (i.expiry IS NULL OR datetime(i.expiry) > CURRENT_TIMESTAMP)
                AND {sql_clause}
                ORDER BY i.{order_column} {order_direction}
            """
            if limit is not None:
                if offset is not None:
                    subquery += " LIMIT ? OFFSET ?"
                    params.extend([limit, offset])
                else:
                    subquery += " LIMIT ?"
                    params.append(limit)
            elif offset is not None:
                # OFFSET without LIMIT is not standard, so use a large LIMIT
                subquery += " LIMIT -1 OFFSET ?"
                params.append(offset)

            query = f"""
                SELECT sub.id, sub.category, sub.name, sub.value, t.name, t.value
                FROM ({subquery}) sub
                LEFT JOIN {self.tags_table} t ON sub.id = t.item_id
                ORDER BY sub.{order_column} {order_direction}
            """
            cursor.execute(query, [profile_id, category] + params)

            current_item_id = None
            current_entry = None
            for row in cursor:
                item_id, category, name, value, tag_name, tag_value = row
                if item_id != current_item_id:
                    if current_entry:
                        yield current_entry
                    current_item_id = item_id
                    current_entry = Entry(
                        category=category, name=name, value=value, tags={}
                    )
                if tag_name is not None:
                    current_entry.tags[tag_name] = tag_value
            if current_entry:
                yield current_entry
        except Exception as e:
            LOGGER.error("[%s] Failed: %s", operation_name, str(e))
            raise

    def scan_keyset(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        tag_query: Optional[TagQuery],
        last_id: Optional[int],
        limit: int,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> Generator[Entry, None, None]:
        operation_name = "scan_keyset"
        LOGGER.debug(
            "[%s] Starting with profile_id=%s, category=%s, tag_query=%s, last_id=%s, limit=%s, order_by=%s, descending=%s, tags_table=%s",
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

        try:
            if order_by and order_by not in self.ALLOWED_ORDER_BY_COLUMNS:
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=f"Invalid order_by column: {order_by}. Allowed columns: {', '.join(self.ALLOWED_ORDER_BY_COLUMNS)}",
                )

            sql_clause = "1=1"
            params = []
            if tag_query:
                sql_clause, params = self.get_sql_clause(tag_query)

            order_column = order_by if order_by else "id"
            order_direction = "DESC" if descending else "ASC"
            keyset_clause = f"AND i.{order_column} > ?" if last_id is not None else ""
            if last_id is not None:
                params.append(last_id)

            subquery = f"""
                SELECT i.id, i.category, i.name, i.value
                FROM items i
                WHERE i.profile_id = ? AND i.category = ?
                AND (i.expiry IS NULL OR datetime(i.expiry) > CURRENT_TIMESTAMP)
                AND {sql_clause}
                {keyset_clause}
                ORDER BY i.{order_column} {order_direction}
                LIMIT ?
            """
            subquery_params = [profile_id, category] + params + [limit]

            query = f"""
                SELECT sub.id, sub.category, sub.name, sub.value, t.name, t.value
                FROM ({subquery}) sub
                LEFT JOIN {self.tags_table} t ON sub.id = t.item_id
                ORDER BY sub.{order_column} {order_direction}
            """
            cursor.execute(query, subquery_params)

            current_item_id = None
            current_entry = None
            for row in cursor:
                item_id, category, name, value, tag_name, tag_value = row
                if item_id != current_item_id:
                    if current_entry:
                        yield current_entry
                    current_item_id = item_id
                    current_entry = Entry(
                        category=category, name=name, value=value, tags={}
                    )
                if tag_name is not None:
                    current_entry.tags[tag_name] = tag_value
            if current_entry:
                yield current_entry
        except Exception as e:
            LOGGER.error("[%s] Failed: %s", operation_name, str(e))
            raise

    def get_sql_clause(self, tag_query: TagQuery) -> Tuple[str, List[Any]]:
        """Translate a TagQuery into an SQL clause and corresponding parameters."""
        operation_name = "get_sql_clause"
        LOGGER.debug(
            "[%s] Starting with tag_query=%s, tags_table=%s",
            operation_name,
            tag_query,
            self.tags_table,
        )

        try:
            sql_clause = self.encoder.encode_query(tag_query)
            arguments = self.encoder.arguments
            LOGGER.debug(
                "[%s] Generated SQL clause: %s, arguments: %s",
                operation_name,
                sql_clause,
                arguments,
            )
            return sql_clause, arguments
        except Exception as e:
            LOGGER.error("[%s] Failed: %s", operation_name, str(e))
            raise
