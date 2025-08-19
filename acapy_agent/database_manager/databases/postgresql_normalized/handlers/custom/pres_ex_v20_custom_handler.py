from ..normalized_handler import (
    NormalizedHandler,
    is_valid_json,
    serialize_json_with_bool_strings,
)
from ....errors import DatabaseError, DatabaseErrorCode
from psycopg import AsyncCursor
from typing import Union, List, Optional
import json
import base64
import logging
from datetime import datetime, timedelta, timezone
from ...schema_context import SchemaContext

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)  # Adjusted for debugging


class PresExV20CustomHandler(NormalizedHandler):
    """Handler for normalized presentation exchange with custom data extraction logic."""

    def __init__(
        self,
        category: str,
        columns: List[str],
        table_name: Optional[str] = None,
        schema_context: Optional[SchemaContext] = None,
    ):
        super().__init__(category, columns, table_name, schema_context)
        LOGGER.debug(
            f"Initialized PresExV20CustomHandler for category={category}, table={self.table}, columns={columns}, schema_context={schema_context}"
        )

    def _extract_revealed_attrs(self, json_data: dict) -> str:
        try:
            if "pres" not in json_data or not json_data["pres"]:
                return json.dumps([])

            pres = json_data["pres"]
            if isinstance(pres, str) and is_valid_json(pres):
                pres = json.loads(pres)

            presentations_attach = pres.get("presentations_attach", []) or pres.get(
                "presentations~attach", []
            )
            if not presentations_attach or not isinstance(presentations_attach, list):
                return json.dumps([])

            attrs = []
            for attachment in presentations_attach:
                if attachment.get("mime-type") == "application/json" and attachment.get(
                    "data", {}
                ).get("base64"):
                    data = attachment["data"]["base64"]
                    try:
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

    async def insert(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        name: str,
        value: Union[str, bytes],
        tags: dict,
        expiry_ms: int,
    ) -> None:
        LOGGER.debug(
            f"[insert] Inserting record with category={category}, name={name}, value={value}, tags={tags}"
        )

        expiry = None
        if expiry_ms:
            expiry = datetime.now(timezone.utc) + timedelta(milliseconds=expiry_ms)

        if isinstance(value, bytes):
            value = value.decode("utf-8")
        json_data = {}
        if value and isinstance(value, str) and is_valid_json(value):
            try:
                json_data = json.loads(value)
                LOGGER.debug(f"[insert] Parsed json_data: {json_data}")
            except json.JSONDecodeError as e:
                LOGGER.error(f"[insert] Invalid JSON value: {str(e)}, raw value: {value}")
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=f"Invalid JSON value: {str(e)}",
                )

        json_data["revealed_attr_groups"] = self._extract_revealed_attrs(json_data)
        LOGGER.debug(
            f"[insert] Added revealed_attr_groups to json_data: {json_data['revealed_attr_groups']}"
        )

        LOGGER.debug(
            f"[insert] Inserting into items table with profile_id={profile_id}, category={category}, name={name}, value={value}, expiry={expiry}"
        )
        await cursor.execute(
            f"""
            INSERT INTO {self.schema_context.qualify_table("items")} (profile_id, kind, category, name, value, expiry)
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

        data = {"item_id": item_id, "item_name": name}
        LOGGER.debug(f"[insert] Processing columns: {self.columns}")
        for col in self.columns:
            if col in json_data:
                val = json_data[col]
                LOGGER.debug(
                    f"[insert] Column {col} found in json_data with value {val} (type: {type(val)})"
                )
                if col == "pres_request":
                    if isinstance(val, str) and is_valid_json(val):
                        try:
                            val = json.loads(val)
                            val = serialize_json_with_bool_strings(val)
                            LOGGER.debug(
                                f"[insert] Force serialized {col} to JSON: {val}"
                            )
                        except json.JSONDecodeError as e:
                            LOGGER.error(
                                f"[insert] Failed to re-serialize pres_request: {str(e)}, raw value: {val}"
                            )
                            raise DatabaseError(
                                code=DatabaseErrorCode.QUERY_ERROR,
                                message=f"Failed to re-serialize pres_request: {str(e)}",
                            )
                    elif isinstance(val, dict):
                        try:
                            val = serialize_json_with_bool_strings(val)
                            LOGGER.debug(f"[insert] Serialized {col} to JSON: {val}")
                        except DatabaseError as e:
                            LOGGER.error(
                                f"[insert] Serialization failed for column {col}: {str(e)}"
                            )
                            raise
                elif isinstance(val, (dict, list)):
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
                    f"[insert] Column {col} found in tags with value {val} (type: {type(val)})"
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
                LOGGER.debug(
                    f"[insert] Column {col} not found in json_data or tags, setting to NULL"
                )
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
            LOGGER.error(f"[insert] Failed data: {data}")
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
        expiry_ms: int,
    ) -> None:
        LOGGER.debug(
            f"[replace] Replacing record with category={category}, name={name}, value={value}, tags={tags}"
        )

        expiry = None
        if expiry_ms:
            expiry = datetime.now(timezone.utc) + timedelta(milliseconds=expiry_ms)

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
            f"[replace] Updating items table with value={value}, expiry={expiry}, item_id={item_id}"
        )
        await cursor.execute(
            f"""
            UPDATE {self.schema_context.qualify_table("items")} SET value = %s, expiry = %s
            WHERE id = %s
        """,
            (value, expiry, item_id),
        )

        if isinstance(value, bytes):
            value = value.decode("utf-8")
        json_data = {}
        if value and isinstance(value, str) and is_valid_json(value):
            try:
                json_data = json.loads(value)
                LOGGER.debug(f"[replace] Parsed json_data: {json_data}")
            except json.JSONDecodeError as e:
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=f"Invalid JSON value: {str(e)}",
                )

        json_data["revealed_attr_groups"] = self._extract_revealed_attrs(json_data)
        LOGGER.debug(
            f"[replace] Added revealed_attr_groups to json_data: {json_data['revealed_attr_groups']}"
        )

        LOGGER.debug(
            f"[replace] Deleting existing entry from {self.table} for item_id={item_id}"
        )
        await cursor.execute(f"DELETE FROM {self.table} WHERE item_id = %s", (item_id,))

        data = {"item_id": item_id, "item_name": name}
        LOGGER.debug(f"[replace] Processing columns: {self.columns}")
        for col in self.columns:
            if col in json_data:
                val = json_data[col]
                LOGGER.debug(
                    f"[replace] Column {col} found in json_data with value {val} (type: {type(val)})"
                )
                if col == "pres_request":
                    if isinstance(val, str) and is_valid_json(val):
                        try:
                            val = json.loads(val)
                            val = serialize_json_with_bool_strings(val)
                            LOGGER.debug(
                                f"[replace] Force serialized {col} to JSON: {val}"
                            )
                        except json.JSONDecodeError as e:
                            LOGGER.error(
                                f"[replace] Failed to re-serialize pres_request: {str(e)}, raw value: {val}"
                            )
                            raise DatabaseError(
                                code=DatabaseErrorCode.QUERY_ERROR,
                                message=f"Failed to re-serialize pres_request: {str(e)}",
                            )
                    elif isinstance(val, dict):
                        try:
                            val = serialize_json_with_bool_strings(val)
                            LOGGER.debug(f"[replace] Serialized {col} to JSON: {val}")
                        except DatabaseError as e:
                            LOGGER.error(
                                f"[replace] Serialization failed for column {col}: {str(e)}"
                            )
                            raise
                elif isinstance(val, (dict, list)):
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
                    f"[replace] Column {col} found in tags with value {val} (type: {type(val)})"
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
                LOGGER.debug(
                    f"[replace] Column {col} not found in json_data or tags, setting to NULL"
                )
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
            LOGGER.error(f"[replace] Failed data: {data}")
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=f"Database error during replace: {str(e)}",
            )
