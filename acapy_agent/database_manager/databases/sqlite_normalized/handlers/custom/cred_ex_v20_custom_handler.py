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


class CredExV20CustomHandler(NormalizedHandler):
    """Handler for normalized categories with custom data extraction logic."""

    def __init__(
        self,
        category: str,
        columns: List[str],
        table_name: Optional[str] = None,
        release_number: str = "release_0",
        db_type: str = "sqlite",
    ):
        """Initialize the CredExV20CustomHandler.

        Args:
            category: Category name
            columns: List of column names
            table_name: Optional table name override
            release_number: Schema release number
            db_type: Database type

        """
        super().__init__(category, columns, table_name)
        self.version = self._get_version()
        LOGGER.debug(
            f"Initialized CredExV20CustomHandler for category={category}, "
            f"table={self.table}, columns={columns}, "
            f"release_number={release_number}, db_type={db_type}, "
            f"version={self.version}"
        )

    def _get_version(self) -> str:
        """Extract the schema version from self.table."""
        try:
            # Assume table name format is cred_ex_v20_vX (e.g., cred_ex_v20_v1)
            if self.table.startswith("cred_ex_v20_v"):
                version = self.table[len("cred_ex_v20_v") :]
                LOGGER.debug(f"Extracted version {version} from table name {self.table}")
                return version
            # Fallback to default version if table name doesn't match expected format
            LOGGER.warning(
                f"Table name {self.table} does not match expected format, "
                f"defaulting to version 1"
            )
            return "1"
        except Exception as e:
            LOGGER.error(f"Failed to extract version from table {self.table}: {str(e)}")
            return "1"  # Fallback to default version

    def _extract_cred_def_id(self, json_data: dict) -> Optional[str]:
        """Extract credential definition ID from JSON data.

        Args:
            json_data: Dictionary containing credential data

        Returns:
            Credential definition ID if found, None otherwise

        """
        try:
            if "cred_offer" not in json_data or not json_data["cred_offer"]:
                return None
            cred_offer = json_data["cred_offer"]
            if isinstance(cred_offer, str) and is_valid_json(cred_offer):
                cred_offer = json.loads(cred_offer)
            offers_attach = cred_offer.get("offers_attach", []) or cred_offer.get(
                "offers~attach", []
            )
            if not offers_attach or not isinstance(offers_attach, list):
                return None
            for attachment in offers_attach:
                if (
                    attachment.get("@id") == "anoncreds"
                    and attachment.get("mime-type") == "application/json"
                ):
                    data = attachment.get("data", {}).get("base64")
                    if data:
                        try:
                            decoded_data = base64.b64decode(data).decode("utf-8")
                            if is_valid_json(decoded_data):
                                decoded_json = json.loads(decoded_data)
                                cred_def_id = decoded_json.get("cred_def_id")
                                if cred_def_id:
                                    return cred_def_id
                        except (
                            base64.binascii.Error,
                            UnicodeDecodeError,
                            json.JSONDecodeError,
                        ) as e:
                            LOGGER.warning(
                                f"Failed to decode or parse base64 data: {str(e)}"
                            )
                            return None
            return None
        except Exception as e:
            LOGGER.error(f"Error extracting cred_def_id: {str(e)}")
            return None

    def _extract_attributes_and_formats(
        self, json_data: dict, cred_ex_id: int, cursor: sqlite3.Cursor
    ):
        """Extract attributes and formats from JSON data and insert into subtables."""
        attributes = []
        formats = []

        # Prioritize cred_proposal, then cred_offer, then cred_issue for attributes
        for field in ["cred_proposal", "cred_offer", "cred_issue"]:
            if field in json_data and json_data[field] and not attributes:
                try:
                    data = json_data[field]
                    if isinstance(data, str) and is_valid_json(data):
                        data = json.loads(data)
                    if (
                        "credential_preview" in data
                        and "attributes" in data["credential_preview"]
                    ):
                        attributes = data["credential_preview"]["attributes"]
                        LOGGER.debug(
                            f"[extract] Extracted attributes from {field}: {attributes}"
                        )
                        break
                except Exception as e:
                    LOGGER.warning(
                        f"[extract] Error extracting attributes from {field}: {str(e)}"
                    )

        # Insert attributes into dynamic attributes subtable
        attributes_table = f"cred_ex_v20_attributes_v{self.version}"
        try:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (attributes_table,),
            )
            if not cursor.fetchone():
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=f"Attributes table {attributes_table} does not exist",
                )
            for attr in attributes:
                if "name" in attr and "value" in attr:
                    cursor.execute(
                        f"""
                        INSERT INTO {attributes_table} 
                        (cred_ex_v20_id, attr_name, attr_value)
                        VALUES (?, ?, ?)
                    """,
                        (cred_ex_id, attr["name"], attr["value"]),
                    )
                    LOGGER.debug(
                        f"[extract] Inserted attribute: name={attr['name']}, "
                        f"value={attr['value']} for cred_ex_v20_id={cred_ex_id}"
                    )
        except sqlite3.OperationalError as e:
            LOGGER.error(
                f"[extract] SQLite error inserting into {attributes_table}: {str(e)}"
            )
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=f"SQLite error inserting into {attributes_table}: {str(e)}",
            )

        # Extract formats from cred_offer or cred_issue
        for field in ["cred_offer", "cred_issue"]:
            if field in json_data and json_data[field]:
                try:
                    data = json_data[field]
                    if isinstance(data, str) and is_valid_json(data):
                        data = json.loads(data)
                    if "formats" in data:
                        formats.extend(data["formats"])
                        LOGGER.debug(
                            f"[extract] Extracted formats from {field}: {formats}"
                        )
                except Exception as e:
                    LOGGER.warning(
                        f"[extract] Error extracting formats from {field}: {str(e)}"
                    )

        # Insert formats into dynamic formats subtable
        formats_table = f"cred_ex_v20_formats_v{self.version}"
        try:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (formats_table,),
            )
            if not cursor.fetchone():
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=f"Formats table {formats_table} does not exist",
                )
            for fmt in formats:
                if "attach_id" in fmt:
                    cursor.execute(
                        f"""
                        INSERT INTO {formats_table} 
                        (cred_ex_v20_id, format_id, format_type)
                        VALUES (?, ?, ?)
                    """,
                        (cred_ex_id, fmt["attach_id"], fmt.get("format")),
                    )
                    LOGGER.debug(
                        f"[extract] Inserted format: attach_id={fmt['attach_id']}, "
                        f"format_type={fmt.get('format')} for cred_ex_v20_id={cred_ex_id}"
                    )
        except sqlite3.OperationalError as e:
            LOGGER.error(
                f"[extract] SQLite error inserting into {formats_table}: {str(e)}"
            )
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=f"SQLite error inserting into {formats_table}: {str(e)}",
            )

    def insert(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        name: str,
        value: str | bytes | dict,
        tags: dict,
        expiry_ms: Optional[int] = None,
    ) -> None:
        """Insert a new credential exchange record.

        Args:
            cursor: Database cursor
            profile_id: Profile identifier
            category: Record category
            name: Record name
            value: Record value data
            tags: Associated tags
            expiry_ms: Expiry time in milliseconds

        """
        import traceback

        LOGGER.setLevel(logging.DEBUG)
        LOGGER.debug(
            f"[insert] Starting with category={category}, name={name}, "
            f"thread_id={tags.get('thread_id')}, "
            f"stack={''.join(traceback.format_stack(limit=5))}"
        )

        expiry = None
        if expiry_ms:
            expiry = (
                datetime.now(timezone.utc) + timedelta(milliseconds=expiry_ms)
            ).isoformat()

        cursor.execute("PRAGMA busy_timeout = 10000")
        try:
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            json_data = {}
            if isinstance(value, dict):
                json_data = value
                value_to_store = json.dumps(json_data)
                LOGGER.debug(f"[insert] Value is already a dict: {json_data}")
            elif value and isinstance(value, str) and is_valid_json(value):
                try:
                    json_data = json.loads(value)
                    value_to_store = value
                    LOGGER.debug(f"[insert] Parsed json_data: {json_data}")
                except json.JSONDecodeError as e:
                    LOGGER.error(
                        f"[insert] Invalid JSON value: {str(e)}, raw value: {value}"
                    )
                    raise DatabaseError(
                        code=DatabaseErrorCode.QUERY_ERROR,
                        message=f"Invalid JSON value: {str(e)}",
                    )
            else:
                value_to_store = value

            # Check for existing items record
            cursor.execute(
                """
                SELECT id FROM items
                WHERE profile_id = ? AND category = ? AND name = ?
            """,
                (profile_id, category, name),
            )
            existing_item = cursor.fetchone()
            if existing_item:
                item_id = existing_item[0]
                LOGGER.debug(
                    f"[insert] Found existing item_id={item_id} for "
                    f"category={category}, name={name}"
                )
                cursor.execute(
                    f"SELECT id, thread_id FROM {self.table} WHERE item_id = ?",
                    (item_id,),
                )
                existing_cred = cursor.fetchone()
                if existing_cred:
                    LOGGER.error(
                        f"[insert] Duplicate cred_ex_v20 record for "
                        f"item_id={item_id}, thread_id={existing_cred[1]}"
                    )
                    raise DatabaseError(
                        code=DatabaseErrorCode.DUPLICATE_ITEM_ENTRY_ERROR,
                        message=(
                            f"Duplicate cred_ex_v20 record for item_id={item_id}, "
                            f"existing thread_id={existing_cred[1]}"
                        ),
                    )
                raise DatabaseError(
                    code=DatabaseErrorCode.DUPLICATE_ITEM_ENTRY_ERROR,
                    message=(
                        f"Duplicate entry for category '{category}' and name '{name}'"
                    ),
                )

            # Check for duplicate thread_id
            if tags.get("thread_id"):
                cursor.execute(
                    f"SELECT id, item_id FROM {self.table} WHERE thread_id = ?",
                    (tags.get("thread_id"),),
                )
                duplicates = cursor.fetchall()
                if duplicates:
                    LOGGER.error(
                        f"[insert] Duplicate thread_id found in {self.table}: "
                        f"{duplicates}"
                    )
                    raise DatabaseError(
                        code=DatabaseErrorCode.DUPLICATE_ITEM_ENTRY_ERROR,
                        message=f"Duplicate thread_id {tags.get('thread_id')} found",
                    )

            # Insert into items table
            cursor.execute(
                """
                INSERT INTO items (profile_id, kind, category, name, value, expiry)
                VALUES (?, 0, ?, ?, ?, ?)
            """,
                (profile_id, category, name, value_to_store, expiry),
            )
            item_id = cursor.lastrowid
            LOGGER.debug(f"[insert] Inserted into items table, item_id={item_id}")

            # Custom data extraction
            cred_def_id = self._extract_cred_def_id(json_data)
            data = {"item_id": item_id, "item_name": name}
            for col in self.columns:
                if col == "cred_def_id" and cred_def_id:
                    data[col] = cred_def_id
                    LOGGER.debug(
                        f"[insert] Added column {col} from custom extraction: "
                        f"{cred_def_id}"
                    )
                elif col in json_data:
                    val = json_data[col]
                    if isinstance(val, (dict, list)):
                        val = serialize_json_with_bool_strings(val)
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
                    if isinstance(val, (dict, list)):
                        val = serialize_json_with_bool_strings(val)
                    elif val is True:
                        val = "true"
                    elif val is False:
                        val = "false"
                    elif val is None:
                        val = None
                    data[col] = val
                    LOGGER.debug(f"[insert] Added column {col} from tags: {val}")
                else:
                    data[col] = None
                    LOGGER.debug(
                        f"[insert] Column {col} not found in json_data or tags, "
                        f"setting to NULL"
                    )

            columns = list(data.keys())
            placeholders = ", ".join(["?" for _ in columns])
            sql = (
                f"INSERT INTO {self.table} ({', '.join(columns)}) VALUES ({placeholders})"
            )
            cursor.execute(sql, list(data.values()))
            cred_ex_id = cursor.lastrowid
            LOGGER.debug(
                f"[insert] Inserted cred_ex_v20 record with id={cred_ex_id}, "
                f"item_id={item_id}, thread_id={tags.get('thread_id')}"
            )

            # Extract and insert attributes and formats
            self._extract_attributes_and_formats(json_data, cred_ex_id, cursor)

        except (
            sqlite3.OperationalError,
            sqlite3.IntegrityError,
            sqlite3.DatabaseError,
        ) as e:
            LOGGER.error(
                f"[insert] SQLite error during insert for item_id={item_id}, "
                f"thread_id={tags.get('thread_id')}: {str(e)}"
            )
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=f"SQLite error during insert: {str(e)}",
            )
        except Exception as e:
            LOGGER.error(
                f"[insert] Unexpected error during insert for item_id={item_id}, "
                f"thread_id={tags.get('thread_id')}: {str(e)}"
            )
            raise

    def replace(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        name: str,
        value: str | bytes | dict,
        tags: dict,
        expiry_ms: Optional[int] = None,
    ) -> None:
        """Replace an existing credential exchange record.

        Args:
            cursor: Database cursor
            profile_id: Profile identifier
            category: Record category
            name: Record name
            value: Record value data
            tags: Associated tags
            expiry_ms: Expiry time in milliseconds

        """
        import traceback

        LOGGER.setLevel(logging.DEBUG)
        LOGGER.debug(
            f"[replace] Starting with category={category}, name={name}, "
            f"thread_id={tags.get('thread_id')}, "
            f"stack={''.join(traceback.format_stack(limit=5))}"
        )

        expiry = None
        if expiry_ms:
            expiry = (
                datetime.now(timezone.utc) + timedelta(milliseconds=expiry_ms)
            ).isoformat()

        cursor.execute("PRAGMA busy_timeout = 10000")
        try:
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
                    message=(
                        f"Record not found for category '{category}' and name '{name}'"
                    ),
                )
            item_id = row[0]
            LOGGER.debug(f"[replace] Found item_id={item_id} for replacement")

            # Check for duplicate thread_id, excluding current item_id
            if tags.get("thread_id"):
                cursor.execute(
                    f"SELECT id, item_id FROM {self.table} "
                    f"WHERE thread_id = ? AND item_id != ?",
                    (tags.get("thread_id"), item_id),
                )
                duplicates = cursor.fetchall()
                if duplicates:
                    LOGGER.warning(
                        f"[replace] Duplicate thread_id found in {self.table}: "
                        f"{duplicates}"
                    )
                    for dup_id, dup_item_id in duplicates:
                        cursor.execute(
                            f"DELETE FROM {self.table} WHERE id = ?", (dup_id,)
                        )
                        LOGGER.debug(
                            f"[replace] Deleted duplicate record id={dup_id}, "
                            f"thread_id={tags.get('thread_id')}"
                        )

            # Handle value as either a dict or a JSON string
            json_data = {}
            if isinstance(value, dict):
                json_data = value
                value_to_store = json.dumps(json_data)
                LOGGER.debug(f"[replace] Value is already a dict: {json_data}")
            elif isinstance(value, bytes):
                value = value.decode("utf-8")
                value_to_store = value
                if value and is_valid_json(value):
                    try:
                        json_data = json.loads(value)
                        LOGGER.debug(f"[replace] Parsed json_data: {json_data}")
                    except json.JSONDecodeError as e:
                        raise DatabaseError(
                            code=DatabaseErrorCode.QUERY_ERROR,
                            message=f"Invalid JSON value: {str(e)}",
                        )
            else:
                value_to_store = value
                if value and is_valid_json(value):
                    try:
                        json_data = json.loads(value)
                        LOGGER.debug(f"[replace] Parsed json_data: {json_data}")
                    except json.JSONDecodeError as e:
                        raise DatabaseError(
                            code=DatabaseErrorCode.QUERY_ERROR,
                            message=f"Invalid JSON value: {str(e)}",
                        )

            # Validate cred_issue if present
            if "cred_issue" in json_data and json_data["cred_issue"]:
                cred_issue = json_data["cred_issue"]
                if isinstance(cred_issue, str) and is_valid_json(cred_issue):
                    try:
                        json.loads(cred_issue)
                        LOGGER.debug("[replace] Validated cred_issue JSON string")
                    except json.JSONDecodeError as e:
                        raise DatabaseError(
                            code=DatabaseErrorCode.QUERY_ERROR,
                            message=f"Invalid cred_issue JSON: {str(e)}",
                        )
                elif isinstance(cred_issue, dict):
                    LOGGER.debug(
                        "[replace] cred_issue is already a dict, no further "
                        "validation needed"
                    )
                else:
                    raise DatabaseError(
                        code=DatabaseErrorCode.QUERY_ERROR,
                        message=(
                            f"Invalid cred_issue type: expected str or dict, "
                            f"got {type(cred_issue)}"
                        ),
                    )

            cursor.execute(
                """
                UPDATE items SET value = ?, expiry = ?
                WHERE id = ?
            """,
                (value_to_store, expiry, item_id),
            )

            cursor.execute(f"DELETE FROM {self.table} WHERE item_id = ?", (item_id,))
            cred_def_id = self._extract_cred_def_id(json_data)
            data = {"item_id": item_id, "item_name": name}
            for col in self.columns:
                if col == "cred_def_id" and cred_def_id:
                    data[col] = cred_def_id
                    LOGGER.debug(
                        f"[replace] Added column {col} from custom extraction: "
                        f"{cred_def_id}"
                    )
                elif col in json_data:
                    val = json_data[col]
                    if isinstance(val, (dict, list)):
                        val = serialize_json_with_bool_strings(val)
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
                    if isinstance(val, (dict, list)):
                        val = serialize_json_with_bool_strings(val)
                    elif val is True:
                        val = "true"
                    elif val is False:
                        val = "false"
                    elif val is None:
                        val = None
                    data[col] = val
                    LOGGER.debug(f"[replace] Added column {col} from tags: {val}")
                else:
                    data[col] = None
                    LOGGER.debug(
                        f"[replace] Column {col} not found in json_data or tags, "
                        f"setting to NULL"
                    )

            columns = list(data.keys())
            placeholders = ", ".join(["?" for _ in columns])
            sql = (
                f"INSERT INTO {self.table} ({', '.join(columns)}) VALUES ({placeholders})"
            )
            cursor.execute(sql, list(data.values()))
            cred_ex_id = cursor.lastrowid
            LOGGER.debug(
                f"[replace] Inserted cred_ex_v20 record with id={cred_ex_id}, "
                f"item_id={item_id}, thread_id={tags.get('thread_id')}"
            )

            # Extract and insert attributes and formats
            self._extract_attributes_and_formats(json_data, cred_ex_id, cursor)

        except (
            sqlite3.OperationalError,
            sqlite3.IntegrityError,
            sqlite3.DatabaseError,
        ) as e:
            LOGGER.error(
                f"[replace] SQLite error during replace for item_id={item_id}, "
                f"thread_id={tags.get('thread_id')}: {str(e)}"
            )
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=f"SQLite error during replace: {str(e)}",
            )
        except Exception as e:
            LOGGER.error(
                f"[replace] Unexpected error during replace for item_id={item_id}, "
                f"thread_id={tags.get('thread_id')}: {str(e)}"
            )
            raise
