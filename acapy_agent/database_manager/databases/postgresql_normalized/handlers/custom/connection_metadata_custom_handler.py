"""Module docstring."""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Union

from psycopg import AsyncCursor

from acapy_agent.database_manager.databases.errors import DatabaseError, DatabaseErrorCode
from acapy_agent.database_manager.databases.postgresql_normalized.schema_context import (
    SchemaContext,
)

from ..normalized_handler import (
    NormalizedHandler,
    is_valid_json,
    serialize_json_with_bool_strings,
)

LOGGER = logging.getLogger(__name__)


class ConnectionMetadataCustomHandler(NormalizedHandler):
    """Handler for normalized categories with custom data extraction logic."""

    def __init__(
        self,
        category: str,
        columns: List[str],
        table_name: Optional[str] = None,
        schema_context: Optional[SchemaContext] = None,
    ):
        """Initialize ConnectionMetadataCustomHandler."""
        super().__init__(category, columns, table_name, schema_context)
        LOGGER.debug(
            f"Initialized ConnectionMetadataCustomHandler for category={category}, "
            f"table={self.table}, columns={columns}, schema_context={schema_context}"
        )

    def _extract_metadata(self, json_data: dict) -> Optional[str]:
        try:
            if not json_data or not isinstance(json_data, dict):
                LOGGER.debug("No valid JSON data provided for metadata extraction")
                return None

            serialized_data = serialize_json_with_bool_strings(json_data)
            LOGGER.debug(f"Extracted and serialized metadata: {serialized_data}")
            return serialized_data
        except Exception as e:
            LOGGER.error(f"Error extracting metadata: {str(e)}")
            return None

    def _compute_expiry(self, expiry_ms: Optional[int]) -> Optional[datetime]:
        return (
            datetime.now(timezone.utc) + timedelta(milliseconds=expiry_ms)
            if expiry_ms
            else None
        )

    def _parse_value(self, value: str | bytes) -> dict:
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        if value and isinstance(value, str) and is_valid_json(value):
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=f"Invalid JSON value: {str(e)}",
                )
        return {}

    async def insert(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        name: str,
        value: Union[str, bytes],
        tags: dict,
        expiry_ms: Optional[int] = None,
    ) -> None:
        """Insert a new connection metadata entry."""
        LOGGER.debug(
            f"[insert] Inserting record with category={category}, name={name}, "
            f"value={value}, tags={tags}"
        )

        expiry = self._compute_expiry(expiry_ms)

        json_data = self._parse_value(value)
        if json_data:
            LOGGER.debug(f"[insert] Parsed json_data: {json_data}")

        LOGGER.debug(
            f"[insert] Inserting into items table with profile_id={profile_id}, "
            f"category={category}, name={name}, value={value}, expiry={expiry}"
        )
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
            raise DatabaseError(
                code=DatabaseErrorCode.DUPLICATE_ITEM_ENTRY_ERROR,
                message=f"Duplicate entry for category '{category}' and name '{name}'",
            )
        item_id = row[0]
        LOGGER.debug(f"[insert] Inserted into items table, item_id={item_id}")

        metadata = self._extract_metadata(json_data)
        data = {"item_id": item_id, "item_name": name}
        LOGGER.debug(f"[insert] Processing columns: {self.columns}")
        for col in self.columns:
            if col == "metadata" and metadata:
                data[col] = metadata
                LOGGER.debug(
                    f"[insert] Added column {col} from custom extraction: {metadata}"
                )
            elif col in json_data:
                val = json_data[col]
                LOGGER.debug(
                    f"[insert] Column {col} found in json_data with value {val} "
                    f"(type: {type(val)})"
                )
                if isinstance(val, (dict, list)):
                    try:
                        val = serialize_json_with_bool_strings(val)
                        LOGGER.debug(f"[insert] Serialized {col} to JSON: {val}")
                    except DatabaseError as e:
                        LOGGER.error(
                            f"[insert] Serialization failed for column {col}: {str(e)}"
                        )
                        raise
                elif val is True:
                    val = "true"
                elif val is False:
                    val = "false"
                elif val is None:
                    val = None
                data[col] = val
                LOGGER.debug(f"[insert] Added column {col} from json_data: {val}")
            elif col in tags:
                val = tags[col]
                LOGGER.debug(
                    f"[insert] Column {col} found in tags with value {val} "
                    f"(type: {type(val)})"
                )
                if isinstance(val, (dict, list)):
                    try:
                        val = serialize_json_with_bool_strings(val)
                        LOGGER.debug(f"[insert] Serialized {col} to JSON: {val}")
                    except DatabaseError as e:
                        LOGGER.error(
                            f"[insert] Serialization failed for column {col}: {str(e)}"
                        )
                        raise
                elif val is True:
                    val = "true"
                elif val is False:
                    val = "false"
                elif val is None:
                    val = None
                data[col] = val
                LOGGER.debug(f"[insert] Added column {col} from tags: {val}")
            else:
                LOGGER.debug(f"[insert] Column {col} not found in json_data or tags")
                data[col] = None

        LOGGER.debug(f"[insert] Final data for normalized table: {data}")

        columns = list(data.keys())
        placeholders = ", ".join(["%s" for _ in columns])
        sql = f"INSERT INTO {self.table} ({', '.join(columns)}) VALUES ({placeholders})"
        LOGGER.debug(f"[insert] Executing SQL: {sql} with values: {list(data.values())}")
        try:
            await cursor.execute(sql, list(data.values()))
            LOGGER.debug(f"[insert] Successfully inserted into {self.table}")
        except Exception as e:
            LOGGER.error(f"[insert] Database error during insert: {str(e)}")
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=f"Database error during insert: {str(e)}",
            )

    async def replace(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        name: str,
        value: Union[str, bytes],
        tags: dict,
        expiry_ms: Optional[int] = None,
    ) -> None:
        """Replace an existing connection metadata entry."""
        LOGGER.debug(
            f"[replace] Replacing record with category={category}, name={name}, "
            f"value={value}, tags={tags}"
        )

        expiry = self._compute_expiry(expiry_ms)

        await cursor.execute(
            f"""
            SELECT id FROM {self.schema_context.qualify_table("items")}
            WHERE profile_id = %s AND category = %s AND name = %s
        """,
            (profile_id, category, name),
        )
        row = await cursor.fetchone()
        if not row:
            raise DatabaseError(
                code=DatabaseErrorCode.RECORD_NOT_FOUND,
                message=f"Record not found for category '{category}' and name '{name}'",
            )
        item_id = row[0]
        LOGGER.debug(f"[replace] Found item_id={item_id} for replacement")

        LOGGER.debug(
            f"[replace] Updating items table with value={value}, expiry={expiry}, "
            f"item_id={item_id}"
        )
        await cursor.execute(
            f"""
            UPDATE {self.schema_context.qualify_table("items")} 
            SET value = %s, expiry = %s
            WHERE id = %s
        """,
            (value, expiry, item_id),
        )

        json_data = self._parse_value(value)
        if json_data:
            LOGGER.debug(f"[replace] Parsed json_data: {json_data}")

        LOGGER.debug(
            f"[replace] Deleting existing entry from {self.table} for item_id={item_id}"
        )
        await cursor.execute(f"DELETE FROM {self.table} WHERE item_id = %s", (item_id,))

        metadata = self._extract_metadata(json_data)
        data = {"item_id": item_id, "item_name": name}
        LOGGER.debug(f"[replace] Processing columns: {self.columns}")
        for col in self.columns:
            if col == "metadata" and metadata:
                data[col] = metadata
                LOGGER.debug(
                    f"[replace] Added column {col} from custom extraction: {metadata}"
                )
            elif col in json_data:
                val = json_data[col]
                LOGGER.debug(
                    f"[replace] Column {col} found in json_data with value {val} "
                    f"(type: {type(val)})"
                )
                if isinstance(val, (dict, list)):
                    try:
                        val = serialize_json_with_bool_strings(val)
                        LOGGER.debug(f"[replace] Serialized {col} to JSON: {val}")
                    except DatabaseError as e:
                        LOGGER.error(
                            f"[replace] Serialization failed for column {col}: {str(e)}"
                        )
                        raise
                elif val is True:
                    val = "true"
                elif val is False:
                    val = "false"
                elif val is None:
                    val = None
                data[col] = val
                LOGGER.debug(f"[replace] Added column {col} from json_data: {val}")
            elif col in tags:
                val = tags[col]
                LOGGER.debug(
                    f"[replace] Column {col} found in tags with value {val} "
                    f"(type: {type(val)})"
                )
                if isinstance(val, (dict, list)):
                    try:
                        val = serialize_json_with_bool_strings(val)
                        LOGGER.debug(f"[replace] Serialized {col} to JSON: {val}")
                    except DatabaseError as e:
                        LOGGER.error(
                            f"[replace] Serialization failed for column {col}: {str(e)}"
                        )
                        raise
                elif val is True:
                    val = "true"
                elif val is False:
                    val = "false"
                elif val is None:
                    val = None
                data[col] = val
                LOGGER.debug(f"[replace] Added column {col} from tags: {val}")
            else:
                LOGGER.debug(f"[replace] Column {col} not found in json_data or tags")
                data[col] = None

        columns = list(data.keys())
        placeholders = ", ".join(["%s" for _ in columns])
        sql = f"INSERT INTO {self.table} ({', '.join(columns)}) VALUES ({placeholders})"
        LOGGER.debug(f"[replace] Executing SQL: {sql} with values: {list(data.values())}")
        try:
            await cursor.execute(sql, list(data.values()))
            LOGGER.debug(f"[replace] Successfully inserted into {self.table}")
        except Exception as e:
            LOGGER.error(f"[replace] Database error during replace: {str(e)}")
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=f"Database error during replace: {str(e)}",
            )
