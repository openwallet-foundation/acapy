"""Module docstring."""

import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from ....errors import DatabaseError, DatabaseErrorCode
from ..normalized_handler import (
    NormalizedHandler,
    is_valid_json,
    serialize_json_with_bool_strings,
)

LOGGER = logging.getLogger(__name__)


class ConnectionMetadataCustomHandler(NormalizedHandler):
    """Handler for normalized categories with custom data extraction logic."""

    def __init__(
        self, category: str, columns: List[str], table_name: Optional[str] = None
    ):
        """Initialize the ConnectionMetadataCustomHandler.

        Args:
            category: Category name
            columns: List of column names
            table_name: Optional table name override

        """
        super().__init__(category, columns, table_name)
        LOGGER.debug(
            f"Initialized ConnectionMetadataCustomHandler for "
            f"category={category}, table={table_name or category}, "
            f"columns={columns}"
        )

    def _extract_metadata(self, json_data: dict) -> Optional[str]:
        """Extract key-value pairs from JSON data and serialize as JSON string.

        Extract key-value pairs from JSON data and serialize them as a JSON string
        for the metadata field.

        Args:
            json_data: The parsed JSON data from the value field

        Returns:
            The serialized JSON string of key-value pairs or None if not found

        """
        try:
            if not json_data or not isinstance(json_data, dict):
                LOGGER.debug("No valid JSON data provided for metadata extraction")
                return None

            # Ensure all values are properly serialized (handle booleans, dicts, lists)
            serialized_data = serialize_json_with_bool_strings(json_data)
            LOGGER.debug(f"Extracted and serialized metadata: {serialized_data}")
            return serialized_data
        except Exception as e:
            LOGGER.error(f"Error extracting metadata: {str(e)}")
            return None

    def insert(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        name: str,
        value: str | bytes,
        tags: dict,
        expiry_ms: Optional[int] = None,
    ) -> None:
        """Insert a connection metadata record.

        Args:
            cursor: Database cursor
            profile_id: Profile identifier
            category: Record category
            name: Record name
            value: Record value data
            tags: Associated tags
            expiry_ms: Expiry time in milliseconds

        """
        # insert a new entry with custom metadata extraction.
        LOGGER.debug(
            f"Inserting record with category={category}, name={name}, "
            f"value={value}, tags={tags}"
        )

        expiry = None
        if expiry_ms:
            expiry = (
                datetime.now(timezone.utc) + timedelta(milliseconds=expiry_ms)
            ).isoformat()

        if isinstance(value, bytes):
            value = value.decode("utf-8")
        json_data = {}
        if value and isinstance(value, str) and is_valid_json(value):
            try:
                json_data = json.loads(value)
                LOGGER.debug(f"Parsed json_data: {json_data}")
            except json.JSONDecodeError as e:
                LOGGER.error(f"Invalid JSON value: {str(e)}, raw value: {value}")
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=f"Invalid JSON value: {str(e)}",
                )

        LOGGER.debug(
            f"Inserting into items table with profile_id={profile_id}, "
            f"category={category}, name={name}, value={value}, expiry={expiry}"
        )
        cursor.execute(
            """
            INSERT OR IGNORE INTO items (profile_id, kind, category, name, value, expiry)
            VALUES (?, 0, ?, ?, ?, ?)
        """,
            (profile_id, category, name, value, expiry),
        )
        if cursor.rowcount == 0:
            raise DatabaseError(
                code=DatabaseErrorCode.DUPLICATE_ITEM_ENTRY_ERROR,
                message=f"Duplicate entry for category '{category}' and name '{name}'",
            )
        item_id = cursor.lastrowid
        LOGGER.debug(f"Inserted into items table, item_id={item_id}")

        # Custom metadata extraction
        metadata = self._extract_metadata(json_data)

        data = {"item_id": item_id, "item_name": name}
        LOGGER.debug(f"Processing columns: {self.columns}")
        for col in self.columns:
            if col == "metadata" and metadata:
                data[col] = metadata
                LOGGER.debug(f"Added column {col} from custom extraction: {metadata}")
            elif col in json_data:
                val = json_data[col]
                LOGGER.debug(
                    f"Column {col} found in json_data with value {val} "
                    f"(type: {type(val)})"
                )
                if isinstance(val, (dict, list)):
                    try:
                        val = serialize_json_with_bool_strings(val)
                        LOGGER.debug(f"Serialized {col} to JSON: {val}")
                    except DatabaseError as e:
                        LOGGER.error(f"Serialization failed for column {col}: {str(e)}")
                        raise
                elif val is True:
                    val = "true"
                elif val is False:
                    val = "false"
                elif val is None:
                    val = None
                data[col] = val
                LOGGER.debug(f"Added column {col} from json_data: {val}")
            elif col in tags:
                val = tags[col]
                LOGGER.debug(
                    f"Column {col} found in tags with value {val} (type: {type(val)})"
                )
                if isinstance(val, (dict, list)):
                    try:
                        val = serialize_json_with_bool_strings(val)
                        LOGGER.debug(f"Serialized {col} to JSON: {val}")
                    except DatabaseError as e:
                        LOGGER.error(f"Serialization failed for column {col}: {str(e)}")
                        raise
                elif val is True:
                    val = "true"
                elif val is False:
                    val = "false"
                elif val is None:
                    val = None
                data[col] = val
                LOGGER.debug(f"Added column {col} from tags: {val}")
            else:
                LOGGER.debug(f"Column {col} not found in json_data or tags")

        LOGGER.debug(f"Final data for normalized table: {data}")

        columns = list(data.keys())
        placeholders = ", ".join(["?" for _ in columns])
        sql = f"INSERT INTO {self.table} ({', '.join(columns)}) VALUES ({placeholders})"
        LOGGER.debug(f"Executing SQL: {sql} with values: {list(data.values())}")
        try:
            cursor.execute(sql, list(data.values()))
        except sqlite3.OperationalError as e:
            LOGGER.error(f"SQLite error during insert: {str(e)}")
            LOGGER.error(f"Failed data: {data}")
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=f"SQLite error during insert: {str(e)}",
            )

    def replace(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        name: str,
        value: str | bytes,
        tags: dict,
        expiry_ms: Optional[int] = None,
    ) -> None:
        """Replace a connection metadata record.

        Args:
            cursor: Database cursor
            profile_id: Profile identifier
            category: Record category
            name: Record name
            value: Record value data
            tags: Associated tags
            expiry_ms: Expiry time in milliseconds

        """
        # replace an existing entry with custom metadata extraction."""
        LOGGER.debug(
            f"Replacing record with category={category}, name={name}, "
            f"value={value}, tags={tags}"
        )

        expiry = None
        if expiry_ms:
            expiry = (
                datetime.now(timezone.utc) + timedelta(milliseconds=expiry_ms)
            ).isoformat()

        cursor.execute(
            """
            SELECT id FROM items
            WHERE profile_id = ? AND category = ? AND name = ?
        """,
            (profile_id, category, name),
        )
        row = cursor.fetchone()
        if not row:
            raise DatabaseError(
                code=DatabaseErrorCode.RECORD_NOT_FOUND,
                message=f"Record not found for category '{category}' and name '{name}'",
            )
        item_id = row[0]
        LOGGER.debug(f"Found item_id={item_id} for replacement")

        LOGGER.debug(
            f"Updating items table with value={value}, expiry={expiry}, item_id={item_id}"
        )
        cursor.execute(
            """
            UPDATE items SET value = ?, expiry = ?
            WHERE id = ?
        """,
            (value, expiry, item_id),
        )

        if isinstance(value, bytes):
            value = value.decode("utf-8")
        json_data = {}
        if value and isinstance(value, str) and is_valid_json(value):
            try:
                json_data = json.loads(value)
                LOGGER.debug(f"Parsed json_data: {json_data}")
            except json.JSONDecodeError as e:
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=f"Invalid JSON value: {str(e)}",
                )

        LOGGER.debug(f"Deleting existing entry from {self.table} for item_id={item_id}")
        cursor.execute(f"DELETE FROM {self.table} WHERE item_id = ?", (item_id,))

        # Custom metadata extraction
        metadata = self._extract_metadata(json_data)

        data = {"item_id": item_id, "item_name": name}
        LOGGER.debug(f"Processing columns: {self.columns}")
        for col in self.columns:
            if col == "metadata" and metadata:
                data[col] = metadata
                LOGGER.debug(f"Added column {col} from custom extraction: {metadata}")
            elif col in json_data:
                val = json_data[col]
                LOGGER.debug(
                    f"Column {col} found in json_data with value {val} "
                    f"(type: {type(val)})"
                )
                if isinstance(val, (dict, list)):
                    try:
                        val = serialize_json_with_bool_strings(val)
                        LOGGER.debug(f"Serialized {col} to JSON: {val}")
                    except DatabaseError as e:
                        LOGGER.error(f"Serialization failed for column {col}: {str(e)}")
                        raise
                elif val is True:
                    val = "true"
                elif val is False:
                    val = "false"
                elif val is None:
                    val = None
                data[col] = val
                LOGGER.debug(f"Added column {col} from json_data: {val}")
            elif col in tags:
                val = tags[col]
                LOGGER.debug(
                    f"Column {col} found in tags with value {val} (type: {type(val)})"
                )
                if isinstance(val, (dict, list)):
                    try:
                        val = serialize_json_with_bool_strings(val)
                        LOGGER.debug(f"Serialized {col} to JSON: {val}")
                    except DatabaseError as e:
                        LOGGER.error(f"Serialization failed for column {col}: {str(e)}")
                        raise
                elif val is True:
                    val = "true"
                elif val is False:
                    val = "false"
                elif val is None:
                    val = None
                data[col] = val
                LOGGER.debug(f"Added column {col} from tags: {val}")
            else:
                LOGGER.debug(f"Column {col} not found in json_data or tags")

        columns = list(data.keys())
        placeholders = ", ".join(["?" for _ in columns])
        sql = f"INSERT INTO {self.table} ({', '.join(columns)}) VALUES ({placeholders})"
        LOGGER.debug(f"Executing SQL: {sql} with values: {list(data.values())}")
        try:
            cursor.execute(sql, list(data.values()))
        except sqlite3.OperationalError as e:
            LOGGER.error(f"SQLite error during replace: {str(e)}")
            LOGGER.error(f"Failed data: {data}")
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=f"SQLite error during replace: {str(e)}",
            )
