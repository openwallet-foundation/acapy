"""Module docstring."""

import base64
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


class PresExV20CustomHandler(NormalizedHandler):
    """Handler for normalized presentation exchange with  data extraction logic."""

    def __init__(
        self, category: str, columns: List[str], table_name: Optional[str] = None
    ):
        """Initialize the PresExV20CustomHandler.

        Args:
            category: Category name
            columns: List of column names
            table_name: Optional table name override

        """
        super().__init__(category, columns, table_name)
        LOGGER.debug(
            f"Initialized PresExV20CustomHandler for category={category}, "
            f"table={table_name or category}, columns={columns}"
        )

    def _extract_revealed_attrs(self, json_data: dict) -> str:
        """Extract revealed attribute groups from presentations~attach base64 data.

        Extract revealed attribute groups from the presentations~attach base64 data
        in pres and return as JSON string.

        Args:
            json_data: The parsed JSON data from the value field

        Returns:
            JSON string containing list of attr_name and attr_value pairs

        """
        try:
            if "pres" not in json_data or not json_data["pres"]:
                return json.dumps([])

            # Parse pres if it's a string
            pres = json_data["pres"]
            if isinstance(pres, str) and is_valid_json(pres):
                pres = json.loads(pres)

            # Navigate to presentations~attach
            presentations_attach = pres.get("presentations_attach", []) or pres.get(
                "presentations~attach", []
            )
            if not presentations_attach or not isinstance(presentations_attach, list):
                return json.dumps([])

            # Look for anoncreds attachment
            attrs = []
            for attachment in presentations_attach:
                if attachment.get("mime-type") == "application/json" and attachment.get(
                    "data", {}
                ).get("base64"):
                    data = attachment["data"]["base64"]
                    try:
                        # Decode base64
                        decoded_data = base64.b64decode(data).decode("utf-8")
                        if is_valid_json(decoded_data):
                            decoded_json = json.loads(decoded_data)
                            revealed_attr_groups = decoded_json.get(
                                "requested_proof", {}
                            ).get("revealed_attr_groups", {})
                            for group in revealed_attr_groups.values():
                                for attr_name, attr_data in group.get(
                                    "values", {}
                                ).items():
                                    if "raw" in attr_data:
                                        attrs.append(
                                            {
                                                "attr_name": attr_name,
                                                "attr_value": attr_data["raw"],
                                            }
                                        )
                    except (
                        base64.binascii.Error,
                        UnicodeDecodeError,
                        json.JSONDecodeError,
                    ) as e:
                        LOGGER.warning(f"Failed to decode or parse base64 data: {str(e)}")
                        return json.dumps([])

            LOGGER.debug(f"Extracted revealed attributes: {attrs}")
            return json.dumps(attrs)
        except Exception as e:
            LOGGER.error(f"Error extracting revealed attributes: {str(e)}")
            return json.dumps([])

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
        """Insert a new entry with custom data extraction."""
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

        # Extract revealed attributes and add to json_data
        json_data["revealed_attr_groups"] = self._extract_revealed_attrs(json_data)
        LOGGER.debug(
            f"Added revealed_attr_groups to json_data: "
            f"{json_data['revealed_attr_groups']}"
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

        data = {"item_id": item_id, "item_name": name}
        LOGGER.debug(f"Processing columns: {self.columns}")
        for col in self.columns:
            if col in json_data:
                val = json_data[col]
                LOGGER.debug(
                    f"Column {col} found in json_data with value {val} "
                    f"(type: {type(val)})"
                )
                if col == "pres_request":
                    if isinstance(val, str) and is_valid_json(val):
                        try:
                            val = json.loads(val)
                            val = serialize_json_with_bool_strings(val)
                            LOGGER.debug(f"Force serialized {col} to JSON: {val}")
                        except json.JSONDecodeError as e:
                            LOGGER.error(
                                f"Failed to re-serialize pres_request: {str(e)}, "
                                f"raw value: {val}"
                            )
                            raise DatabaseError(
                                code=DatabaseErrorCode.QUERY_ERROR,
                                message=f"Failed to re-serialize pres_request: {str(e)}",
                            )
                    elif isinstance(val, dict):
                        try:
                            val = serialize_json_with_bool_strings(val)
                            LOGGER.debug(f"Serialized {col} to JSON: {val}")
                        except DatabaseError as e:
                            LOGGER.error(
                                f"Serialization failed for column {col}: {str(e)}"
                            )
                            raise
                elif isinstance(val, (dict, list)):
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
        """Replace an existing entry with custom data extraction."""
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

        # Extract revealed attributes and add to json_data
        json_data["revealed_attr_groups"] = self._extract_revealed_attrs(json_data)
        LOGGER.debug(
            f"Added revealed_attr_groups to json_data: "
            f"{json_data['revealed_attr_groups']}"
        )

        LOGGER.debug(f"Deleting existing entry from {self.table} for item_id={item_id}")
        cursor.execute(f"DELETE FROM {self.table} WHERE item_id = ?", (item_id,))

        data = {"item_id": item_id, "item_name": name}
        LOGGER.debug(f"Processing columns: {self.columns}")
        for col in self.columns:
            if col in json_data:
                val = json_data[col]
                LOGGER.debug(
                    f"Column {col} found in json_data with value {val} "
                    f"(type: {type(val)})"
                )
                if col == "pres_request":
                    if isinstance(val, str) and is_valid_json(val):
                        try:
                            val = json.loads(val)
                            val = serialize_json_with_bool_strings(val)
                            LOGGER.debug(f"Force serialized {col} to JSON: {val}")
                        except json.JSONDecodeError as e:
                            LOGGER.error(
                                f"Failed to re-serialize pres_request: {str(e)}, "
                                f"raw value: {val}"
                            )
                            raise DatabaseError(
                                code=DatabaseErrorCode.QUERY_ERROR,
                                message=f"Failed to re-serialize pres_request: {str(e)}",
                            )
                    elif isinstance(val, dict):
                        try:
                            val = serialize_json_with_bool_strings(val)
                            LOGGER.debug(f"Serialized {col} to JSON: {val}")
                        except DatabaseError as e:
                            LOGGER.error(
                                f"Serialization failed for column {col}: {str(e)}"
                            )
                            raise
                elif isinstance(val, (dict, list)):
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
