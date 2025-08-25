"""Module docstring."""

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


class CredExV20CustomHandler(NormalizedHandler):
    """Handler for normalized categories with custom data extraction logic."""

    def __init__(
        self,
        category: str,
        columns: List[str],
        table_name: Optional[str] = None,
        schema_context: Optional[SchemaContext] = None,
    ):
        """Initialize the CredExV20CustomHandler.

        Args:
            category: The category of credentials to handle
            columns: List of columns for the credential exchange table
            table_name: Optional table name override
            schema_context: Optional schema context for table naming
        """
        super().__init__(category, columns, table_name, schema_context)
        self.version = self._get_version()
        LOGGER.debug(
            f"Initialized CredExV20CustomHandler for category={category}, "
            f"table={self.table}, columns={columns}, version={self.version}, "
            f"schema_context={schema_context}"
        )

    def _get_version(self) -> str:
        try:
            table_suffix = self.table[len(f"{self.schema_context}.cred_ex_v20_v") :]
            if table_suffix:
                LOGGER.debug(
                    f"Extracted version {table_suffix} from table name {self.table}"
                )
                return table_suffix
            LOGGER.warning(
                f"Table name {self.table} does not match expected format, "
                f"defaulting to version 1"
            )
            return "1"
        except Exception as e:
            LOGGER.error(f"Failed to extract version from table {self.table}: {str(e)}")
            return "1"

    def _extract_cred_def_id(self, json_data: dict) -> str:
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

    async def _extract_attributes_and_formats(
        self, json_data: dict, cred_ex_id: int, cursor: AsyncCursor
    ):
        """Extract attributes and formats from JSON data and insert into subtables."""
        attributes = []
        formats = []

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
                except json.JSONDecodeError as e:
                    LOGGER.warning(f"[extract] Invalid {field} JSON: {str(e)}")
                except Exception as e:
                    LOGGER.warning(
                        f"[extract] Error extracting attributes from {field}: {str(e)}"
                    )

        attributes_table = self.schema_context.qualify_table(
            f"cred_ex_v20_attributes_v{self.version}"
        )
        try:
            await cursor.execute(
                (
                    "SELECT EXISTS (SELECT FROM information_schema.tables "
                    "WHERE table_name = %s AND table_schema = %s)"
                ),
                (f"cred_ex_v20_attributes_v{self.version}", str(self.schema_context)),
            )
            if not (await cursor.fetchone())[0]:
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=f"Attributes table {attributes_table} does not exist",
                )
            for attr in attributes:
                if "name" in attr and "value" in attr:
                    await cursor.execute(
                        f"""
                        INSERT INTO {attributes_table} 
                        (cred_ex_v20_id, attr_name, attr_value)
                        VALUES (%s, %s, %s)
                    """,
                        (cred_ex_id, attr["name"], attr["value"]),
                    )
                    LOGGER.debug(
                        f"[extract] Inserted attribute: name={attr['name']}, "
                        f"value={attr['value']} for cred_ex_v20_id={cred_ex_id}"
                    )
        except Exception as e:
            LOGGER.error(
                f"[extract] Database error inserting into {attributes_table}: {str(e)}"
            )
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=f"Database error inserting into {attributes_table}: {str(e)}",
            )

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
                except json.JSONDecodeError as e:
                    LOGGER.warning(
                        f"[extract] Invalid {field} JSON for formats: {str(e)}"
                    )
                except Exception as e:
                    LOGGER.warning(
                        f"[extract] Error extracting formats from {field}: {str(e)}"
                    )

        formats_table = self.schema_context.qualify_table(
            f"cred_ex_v20_formats_v{self.version}"
        )
        try:
            await cursor.execute(
                (
                    "SELECT EXISTS (SELECT FROM information_schema.tables "
                    "WHERE table_name = %s AND table_schema = %s)"
                ),
                (f"cred_ex_v20_formats_v{self.version}", str(self.schema_context)),
            )
            if not (await cursor.fetchone())[0]:
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=f"Formats table {formats_table} does not exist",
                )
            for fmt in formats:
                if "attach_id" in fmt:
                    await cursor.execute(
                        f"""
                        INSERT INTO {formats_table}
                        (cred_ex_v20_id, format_id, format_type)
                        VALUES (%s, %s, %s)
                    """,
                        (cred_ex_id, fmt["attach_id"], fmt.get("format")),
                    )
                    LOGGER.debug(
                        f"[extract] Inserted format: attach_id={fmt['attach_id']}, "
                        f"format_type={fmt.get('format')} for cred_ex_v20_id={cred_ex_id}"
                    )
        except Exception as e:
            LOGGER.error(
                f"[extract] Database error inserting into {formats_table}: {str(e)}"
            )
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=f"Database error inserting into {formats_table}: {str(e)}",
            )

    async def insert(
        self,
        cursor: AsyncCursor,
        profile_id: int,
        category: str,
        name: str,
        value: Union[str, bytes, dict],
        tags: dict,
        expiry_ms: int,
    ) -> None:
        """Insert a credential exchange record with custom data extraction.

        Args:
            cursor: Database cursor for executing queries
            profile_id: Profile ID for the credential exchange
            category: Category of the credential exchange
            name: Name/identifier of the credential exchange
            value: JSON data containing credential exchange details
            tags: Additional tags for the credential exchange
            expiry_ms: Expiration time in milliseconds
        """
        LOGGER.debug(
            (
                f"[insert] Starting with category={category}, name={name}, "
                f"value={value}, tags={tags}"
            )
        )

        expiry = None
        if expiry_ms:
            expiry = datetime.now(timezone.utc) + timedelta(milliseconds=expiry_ms)

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

            await cursor.execute(
                f"""
                SELECT id FROM {self.schema_context.qualify_table("items")}
                WHERE profile_id = %s AND category = %s AND name = %s
            """,
                (profile_id, category, name),
            )
            existing_item = await cursor.fetchone()
            if existing_item:
                item_id = existing_item[0]
                LOGGER.debug(
                    f"[insert] Found existing item_id={item_id} for "
                    f"category={category}, name={name}"
                )
                await cursor.execute(
                    f"SELECT id, thread_id FROM {self.table} WHERE item_id = %s",
                    (item_id,),
                )
                existing_cred = await cursor.fetchone()
                if existing_cred:
                    LOGGER.error(
                        f"[insert] Duplicate cred_ex_v20 record for item_id={item_id}, "
                        f"thread_id={existing_cred[1]}"
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

            if tags.get("thread_id"):
                await cursor.execute(
                    f"SELECT id, item_id FROM {self.table} WHERE thread_id = %s",
                    (tags.get("thread_id"),),
                )
                duplicates = await cursor.fetchall()
                if duplicates:
                    LOGGER.error(
                        (
                            f"[insert] Duplicate thread_id found in {self.table}: "
                            f"{duplicates}"
                        )
                    )
                    raise DatabaseError(
                        code=DatabaseErrorCode.DUPLICATE_ITEM_ENTRY_ERROR,
                        message=f"Duplicate thread_id {tags.get('thread_id')} found",
                    )

            await cursor.execute(
                f"""
                INSERT INTO {self.schema_context.qualify_table("items")}
                (profile_id, kind, category, name, value, expiry)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (profile_id, 0, category, name, value_to_store, expiry),
            )
            item_id = (await cursor.fetchone())[0]
            LOGGER.debug(f"[insert] Inserted into items table, item_id={item_id}")

            cred_def_id = self._extract_cred_def_id(json_data)
            data = {"item_id": item_id, "item_name": name}
            for col in self.columns:
                if col == "cred_def_id" and cred_def_id:
                    data[col] = cred_def_id
                    LOGGER.debug(
                        (
                            f"[insert] Added column {col} from custom extraction: "
                            f"{cred_def_id}"
                        )
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
            placeholders = ", ".join(["%s" for _ in columns])
            sql = (
                f"INSERT INTO {self.table} ({', '.join(columns)}) "
                f"VALUES ({placeholders}) RETURNING id"
            )
            await cursor.execute(sql, list(data.values()))
            cred_ex_id = (await cursor.fetchone())[0]
            LOGGER.debug(
                f"[insert] Inserted cred_ex_v20 record with id={cred_ex_id}, "
                f"item_id={item_id}, thread_id={tags.get('thread_id')}"
            )

            await self._extract_attributes_and_formats(json_data, cred_ex_id, cursor)

        except Exception as e:
            LOGGER.error(
                f"[insert] Database error during insert for item_id={item_id}, "
                f"thread_id={tags.get('thread_id')}: {str(e)}"
            )
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
        value: Union[str, bytes, dict],
        tags: dict,
        expiry_ms: int,
    ) -> None:
        """Replace an existing credential exchange record."""
        LOGGER.debug(
            f"[replace] Starting with category={category}, name={name}, "
            f"thread_id={tags.get('thread_id')}"
        )

        expiry = None
        if expiry_ms:
            expiry = datetime.now(timezone.utc) + timedelta(milliseconds=expiry_ms)

        try:
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
                    message=(
                        f"Record not found for category '{category}' and name '{name}'"
                    ),
                )
            item_id = row[0]
            LOGGER.debug(f"[replace] Found item_id={item_id} for replacement")

            if tags.get("thread_id"):
                await cursor.execute(
                    f"SELECT id, item_id FROM {self.table} "
                    f"WHERE thread_id = %s AND item_id != %s",
                    (tags.get("thread_id"), item_id),
                )
                duplicates = await cursor.fetchall()
                if duplicates:
                    LOGGER.warning(
                        f"[replace] Duplicate thread_id found in {self.table}: "
                        f"{duplicates}"
                    )
                    for dup_id, dup_item_id in duplicates:
                        await cursor.execute(
                            f"DELETE FROM {self.table} WHERE id = %s", (dup_id,)
                        )
                        LOGGER.debug(
                            (
                                f"[replace] Deleted duplicate record id={dup_id}, "
                                f"thread_id={tags.get('thread_id')}"
                            )
                        )

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
                        (
                            "[replace] cred_issue is already a dict, "
                            "no further validation needed"
                        )
                    )
                else:
                    raise DatabaseError(
                        code=DatabaseErrorCode.QUERY_ERROR,
                        message=(
                            f"Invalid cred_issue type: expected str or dict, "
                            f"got {type(cred_issue)}"
                        ),
                    )

            await cursor.execute(
                f"""
                UPDATE {self.schema_context.qualify_table("items")}
                SET value = %s, expiry = %s
                WHERE id = %s
            """,
                (value_to_store, expiry, item_id),
            )

            await cursor.execute(
                f"DELETE FROM {self.table} WHERE item_id = %s", (item_id,)
            )
            cred_def_id = self._extract_cred_def_id(json_data)
            data = {"item_id": item_id, "item_name": name}
            for col in self.columns:
                if col == "cred_def_id" and cred_def_id:
                    data[col] = cred_def_id
                    LOGGER.debug(
                        (
                            f"[replace] Added column {col} from custom extraction: "
                            f"{cred_def_id}"
                        )
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
                        (
                            f"[replace] Column {col} not found in json_data or tags, "
                            "setting to NULL"
                        )
                    )

            columns = list(data.keys())
            placeholders = ", ".join(["%s" for _ in columns])
            sql = (
                f"INSERT INTO {self.table} ({', '.join(columns)}) "
                f"VALUES ({placeholders}) RETURNING id"
            )
            await cursor.execute(sql, list(data.values()))
            cred_ex_id = (await cursor.fetchone())[0]
            LOGGER.debug(
                (
                    f"[replace] Inserted cred_ex_v20 record with id={cred_ex_id}, "
                    f"item_id={item_id}, thread_id={tags.get('thread_id')}"
                )
            )

            await self._extract_attributes_and_formats(json_data, cred_ex_id, cursor)

        except Exception as e:
            LOGGER.error(
                (
                    f"[replace] Database error during replace for item_id={item_id}, "
                    f"thread_id={tags.get('thread_id')}: {str(e)}"
                )
            )
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=f"Database error during replace: {str(e)}",
            )
