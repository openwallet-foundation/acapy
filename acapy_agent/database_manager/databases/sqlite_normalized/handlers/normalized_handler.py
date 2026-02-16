"""Module docstring."""

import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Generator, List, Optional, Sequence, Tuple

from ....db_types import Entry
from ....wql_normalized.encoders import encoder_factory
from ....wql_normalized.query import query_from_json
from ....wql_normalized.tags import TagQuery, query_to_tagquery
from ...errors import DatabaseError, DatabaseErrorCode
from .base_handler import BaseHandler

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.CRITICAL + 1)


def is_valid_json(value: str) -> bool:
    """Check if a string is valid JSON."""
    try:
        json.loads(value)
        return True
    except json.JSONDecodeError:
        return False


def serialize_json_with_bool_strings(data: Any) -> str:
    """Serialize data to JSON, converting booleans to string 'true'/'false' and '~'."""

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
        LOGGER.error(f"Failed to serialize JSON: {str(e)}")
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
        self, category: str, columns: List[str], table_name: Optional[str] = None
    ):
        """Initialize the normalized handler."""
        super().__init__(category)
        self.table = table_name or category
        self.columns = columns
        self.ALLOWED_ORDER_BY_COLUMNS = set(columns) | {"id", "name", "value"}
        self.encoder = encoder_factory.get_encoder(
            "sqlite", lambda x: x, lambda x: x, normalized=True
        )
        LOGGER.debug(
            f"[init] Initialized NormalizedHandler for category={category}, "
            f"table={self.table}, columns={columns}"
        )

    def insert(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        name: str,
        value: str | bytes,
        tags: dict,
        expiry_ms: int,
    ) -> None:
        """Insert an entry into the database."""
        LOGGER.debug(
            f"[insert] Starting with category={category}, name={name}, "
            f"value={value}, tags={tags}, expiry_ms={expiry_ms}"
        )

        expiry = None
        if expiry_ms is not None:
            expiry_dt = datetime.now(timezone.utc) + timedelta(milliseconds=expiry_ms)
            expiry = expiry_dt.strftime("%Y-%m-%d %H:%M:%S")
            LOGGER.debug(f"[insert] Computed expiry: {expiry}")

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

        LOGGER.debug(
            f"[insert] Inserting into items table with profile_id={profile_id}, "
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
            LOGGER.error(f"[insert] Duplicate entry for category={category}, name={name}")
            raise DatabaseError(
                code=DatabaseErrorCode.DUPLICATE_ITEM_ENTRY_ERROR,
                message=f"Duplicate entry for category '{category}' and name '{name}'",
            )
        item_id = cursor.lastrowid
        LOGGER.debug(f"[insert] Inserted into items table, item_id={item_id}")

        data = {"item_id": item_id, "item_name": name}
        LOGGER.debug(f"[insert] Processing columns: {self.columns}")
        for col in self.columns:
            if col in json_data:
                val = json_data[col]
                LOGGER.debug(
                    f"[insert] Column {col} found in json_data with value {val} "
                    f"(type: {type(val)})"
                )
                if col == "pres_request":
                    LOGGER.debug(f"[insert] Raw pres_request value: {val}")
                    if isinstance(val, str) and is_valid_json(val):
                        try:
                            val = json.loads(val)
                            val = serialize_json_with_bool_strings(val)
                            LOGGER.debug(
                                f"[insert] Force serialized {col} to JSON: {val}"
                            )
                        except json.JSONDecodeError as e:
                            LOGGER.error(
                                f"[insert] Failed to re-serialize pres_request: "
                                f"{str(e)}, raw value: {val}"
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
                                f"[insert] Serialization failed for column {col}: "
                                f"{str(e)}"
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
                LOGGER.warning(
                    f"[insert] Column {col} not found in json_data or tags, "
                    f"setting to NULL"
                )
                data[col] = None

        LOGGER.debug(f"[insert] Final data for normalized table: {data}")

        columns = list(data.keys())
        placeholders = ", ".join(["?" for _ in columns])
        sql = f"INSERT INTO {self.table} ({', '.join(columns)}) VALUES ({placeholders})"
        LOGGER.debug(f"[insert] Executing SQL: {sql} with values: {list(data.values())}")
        try:
            cursor.execute(sql, list(data.values()))
            LOGGER.debug(
                f"[insert] Successfully inserted into {self.table} for item_id={item_id}"
            )
        except sqlite3.OperationalError as e:
            LOGGER.error(
                f"[insert] SQLite error during insert into {self.table}: {str(e)}"
            )
            LOGGER.error(f"[insert] Failed data: {data}")
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
        expiry_ms: int,
    ) -> None:
        """Replace an existing entry in the database."""
        LOGGER.debug(
            f"[replace] Replacing record with category={category}, name={name}, "
            f"value={value}, tags={tags}"
        )

        expiry = None
        if expiry_ms is not None:
            expiry_dt = datetime.now(timezone.utc) + timedelta(milliseconds=expiry_ms)
            expiry = expiry_dt.strftime("%Y-%m-%d %H:%M:%S")
            LOGGER.debug(f"[replace] Computed expiry: {expiry}")

        cursor.execute(
            """
            SELECT id FROM items
            WHERE profile_id = ? AND category = ? AND name = ?
        """,
            (profile_id, category, name),
        )
        row = cursor.fetchone()
        if not row:
            LOGGER.error(
                f"[replace] Record not found for category={category}, name={name}"
            )
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
                LOGGER.debug(f"[replace] Parsed json_data: {json_data}")
            except json.JSONDecodeError as e:
                LOGGER.error(f"[replace] Invalid JSON value: {str(e)}")
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=f"Invalid JSON value: {str(e)}",
                )

        LOGGER.debug(
            f"[replace] Deleting existing entry from {self.table} for item_id={item_id}"
        )
        cursor.execute(f"DELETE FROM {self.table} WHERE item_id = ?", (item_id,))

        data = {"item_id": item_id, "item_name": name}
        LOGGER.debug(f"[replace] Processing columns: {self.columns}")
        for col in self.columns:
            if col in json_data:
                val = json_data[col]
                LOGGER.debug(
                    f"[replace] Column {col} found in json_data with value {val} "
                    f"(type: {type(val)})"
                )
                if col == "pres_request":
                    LOGGER.debug(f"[replace] Raw pres_request value: {val}")
                    if isinstance(val, str) and is_valid_json(val):
                        try:
                            val = json.loads(val)
                            val = serialize_json_with_bool_strings(val)
                            LOGGER.debug(
                                f"[replace] Force serialized {col} to JSON: {val}"
                            )
                        except json.JSONDecodeError as e:
                            LOGGER.error(
                                f"[replace] Failed to re-serialize pres_request: "
                                f"{str(e)}, raw value: {val}"
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
                                f"[replace] Serialization failed for column {col}: "
                                f"{str(e)}"
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
                LOGGER.warning(
                    f"[replace] Column {col} not found in json_data or tags, "
                    f"setting to NULL"
                )
                data[col] = None

        columns = list(data.keys())
        placeholders = ", ".join(["?" for _ in columns])
        sql = f"INSERT INTO {self.table} ({', '.join(columns)}) VALUES ({placeholders})"
        LOGGER.debug(f"[replace] Executing SQL: {sql} with values: {list(data.values())}")
        try:
            cursor.execute(sql, list(data.values()))
            LOGGER.debug(
                f"[replace] Successfully inserted into {self.table} for item_id={item_id}"
            )
        except sqlite3.OperationalError as e:
            LOGGER.error(
                f"[replace] SQLite error during insert into {self.table}: {str(e)}"
            )
            LOGGER.error(f"[replace] Failed data: {data}")
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=f"SQLite error during insert: {str(e)}",
            )

    def fetch(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        name: str,
        tag_filter: str | dict,
        for_update: bool,
    ) -> Optional[Entry]:
        """Fetch a single entry by its name."""
        base_query = """
            SELECT id, value FROM items
            WHERE profile_id = ? AND category = ? AND name = ?
            AND (expiry IS NULL OR datetime(expiry) > CURRENT_TIMESTAMP)
        """
        base_params = (profile_id, category, name)
        LOGGER.debug(
            f"[fetch] Executing SQL: {base_query.strip()} | Params: {base_params}"
        )
        cursor.execute(base_query, base_params)
        row = cursor.fetchone()
        LOGGER.debug(f"[fetch] Fetched row from items: {row}")

        if not row:
            return None
        item_id, item_value = row

        if tag_filter:
            if isinstance(tag_filter, str):
                try:
                    tag_filter = json.loads(tag_filter)
                except json.JSONDecodeError as e:
                    raise DatabaseError(
                        code=DatabaseErrorCode.QUERY_ERROR,
                        message=f"Invalid tag_filter JSON: {str(e)}",
                    )
            wql_query = query_from_json(tag_filter)
            tag_query = query_to_tagquery(wql_query)
            sql_clause, params = self.get_sql_clause(tag_query)
            query = f"SELECT * FROM {self.table} t WHERE t.item_id = ? AND {sql_clause}"
            full_params = [item_id] + params
            LOGGER.debug(f"[fetch] Executing SQL: {query} | Params: {full_params}")
            cursor.execute(query, full_params)
        else:
            query = f"SELECT * FROM {self.table} WHERE item_id = ?"
            LOGGER.debug(f"[fetch] Executing SQL: {query} | Params: ({item_id},)")
            cursor.execute(query, (item_id,))

        row = cursor.fetchone()
        LOGGER.debug(f"[fetch] Fetched row from tags table: {row}")
        if not row:
            return None

        columns = [desc[0] for desc in cursor.description]
        row_dict = dict(zip(columns, row))
        tags = {
            k: v for k, v in row_dict.items() if k not in ["id", "item_id", "item_name"]
        }
        tags = deserialize_tags(tags)
        LOGGER.debug(f"[fetch] Row parsed: name={name}, value={item_value}, tags={tags}")

        return Entry(category=category, name=name, value=item_value, tags=tags)

    def fetch_all(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        tag_filter: str | dict,
        limit: int,
        for_update: bool,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> Sequence[Entry]:
        """Fetch all entries matching the specified criteria with ordering."""
        operation_name = "fetch_all"
        LOGGER.debug(
            "[%s] Starting with profile_id=%d, category=%s, tag_filter=%s, "
            "limit=%s, for_update=%s, order_by=%s, descending=%s",
            operation_name,
            profile_id,
            category,
            tag_filter,
            limit,
            for_update,
            order_by,
            descending,
        )

        if order_by and order_by not in self.ALLOWED_ORDER_BY_COLUMNS:
            LOGGER.error("[%s] Invalid order_by column: %s", operation_name, order_by)
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=(
                    f"Invalid order_by column: {order_by}. Allowed columns: "
                    f"{', '.join(self.ALLOWED_ORDER_BY_COLUMNS)}"
                ),
            )

        sql_clause = "1=1"
        params = []
        if tag_filter:
            if isinstance(tag_filter, str):
                try:
                    tag_filter = json.loads(tag_filter)
                except json.JSONDecodeError as e:
                    raise DatabaseError(
                        code=DatabaseErrorCode.QUERY_ERROR,
                        message=f"Invalid tag_filter JSON: {str(e)}",
                    )
            wql_query = query_from_json(tag_filter)
            tag_query = query_to_tagquery(wql_query)
            sql_clause, params = self.get_sql_clause(tag_query)

        order_column = order_by if order_by else "id"
        table_prefix = "t" if order_by in self.columns else "i"
        order_direction = "DESC" if descending else "ASC"

        query = f"""
            SELECT i.id AS i_id, i.name AS i_name, i.value AS i_value, t.*
            FROM items i
            JOIN {self.table} t ON i.id = t.item_id
            WHERE i.profile_id = ? AND i.category = ?
            AND (i.expiry IS NULL OR datetime(i.expiry) > CURRENT_TIMESTAMP)
            AND {sql_clause}
            ORDER BY {table_prefix}.{order_column} {order_direction}
        """
        full_params = [profile_id, category] + params
        if limit is not None:
            query += " LIMIT ?"
            full_params.append(limit)

        LOGGER.debug(
            f"[fetch_all] Executing SQL: {query.strip()} | Params: {full_params}"
        )
        cursor.execute(query, full_params)
        columns = [desc[0] for desc in cursor.description]
        entries = []

        for row in cursor:
            LOGGER.debug(f"[fetch_all] Fetched row: {row}")
            row_dict = dict(zip(columns, row))
            name = row_dict["i_name"]
            value = row_dict["i_value"]
            tags = {
                k: v
                for k, v in row_dict.items()
                if k not in ["i_id", "i_name", "i_value", "item_id", "item_name"]
            }
            tags = deserialize_tags(tags)
            entries.append(Entry(category=category, name=name, value=value, tags=tags))

        LOGGER.debug(f"[fetch_all] Total entries fetched: {len(entries)}")
        return entries

    def count(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        tag_filter: str | dict,
    ) -> int:
        """Count the number of entries matching the specified criteria."""
        sql_clause = "1=1"
        params = []
        if tag_filter:
            if isinstance(tag_filter, str):
                try:
                    tag_filter = json.loads(tag_filter)
                except json.JSONDecodeError as e:
                    raise DatabaseError(
                        code=DatabaseErrorCode.QUERY_ERROR,
                        message=f"Invalid tag_filter JSON: {str(e)}",
                    )
            wql_query = query_from_json(tag_filter)
            tag_query = query_to_tagquery(wql_query)
            sql_clause, params = self.get_sql_clause(tag_query)

        query = f"""
            SELECT COUNT(*)
            FROM items i
            JOIN {self.table} t ON i.id = t.item_id
            WHERE i.profile_id = ? AND i.category = ?
            AND (i.expiry IS NULL OR datetime(i.expiry) > CURRENT_TIMESTAMP)
            AND {sql_clause}
        """
        LOGGER.debug(
            f"[count] Executing SQL: {query.strip()} | "
            f"Params: {[profile_id, category] + params}"
        )
        cursor.execute(query, [profile_id, category] + params)
        count = cursor.fetchone()[0]
        LOGGER.debug(f"[count] Counted {count} entries")
        return count

    def remove(
        self, cursor: sqlite3.Cursor, profile_id: int, category: str, name: str
    ) -> None:
        """Remove an entry identified by its name."""
        LOGGER.debug(f"[remove] Removing record with category={category}, name={name}")
        cursor.execute(
            """
            SELECT id FROM items
            WHERE profile_id = ? AND category = ? AND name = ?
        """,
            (profile_id, category, name),
        )
        row = cursor.fetchone()
        if not row:
            LOGGER.error(
                f"[remove] Record not found for category={category}, name={name}"
            )
            raise DatabaseError(
                code=DatabaseErrorCode.RECORD_NOT_FOUND,
                message=f"Record not found for category '{category}' and name '{name}'",
            )
        item_id = row[0]
        LOGGER.debug(f"[remove] Found item_id={item_id} for removal")

        cursor.execute(f"DELETE FROM {self.table} WHERE item_id = ?", (item_id,))
        cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
        LOGGER.debug(f"[remove] Removed record with item_id={item_id}")

    def remove_all(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        tag_filter: str | dict,
    ) -> int:
        """Remove all entries matching the specified criteria."""
        LOGGER.debug(
            f"[remove_all] Removing all records with category={category}, "
            f"tag_filter={tag_filter}"
        )
        sql_clause = "1=1"
        params = []
        if tag_filter:
            if isinstance(tag_filter, str):
                try:
                    tag_filter = json.loads(tag_filter)
                except json.JSONDecodeError as e:
                    raise DatabaseError(
                        code=DatabaseErrorCode.QUERY_ERROR,
                        message=f"Invalid tag_filter JSON: {str(e)}",
                    )
            wql_query = query_from_json(tag_filter)
            tag_query = query_to_tagquery(wql_query)
            sql_clause, params = self.get_sql_clause(tag_query)

        query = f"""
            DELETE FROM items WHERE id IN (
                SELECT i.id FROM items i
                JOIN {self.table} t ON i.id = t.item_id
                WHERE i.profile_id = ? AND i.category = ?
                AND (i.expiry IS NULL OR datetime(i.expiry) > CURRENT_TIMESTAMP)
                AND {sql_clause}
            )
        """
        LOGGER.debug(
            f"[remove_all] Executing SQL: {query.strip()} | "
            f"Params: {[profile_id, category] + params}"
        )
        cursor.execute(query, [profile_id, category] + params)
        rowcount = cursor.rowcount
        LOGGER.debug(f"[remove_all] Removed {rowcount} entries")
        return rowcount

    def scan(
        self,
        cursor: sqlite3.Cursor,
        profile_id: int,
        category: str,
        tag_query: Optional[TagQuery],
        offset: int,
        limit: int,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> Generator[Entry, None, None]:
        """Scan the database for entries matching the criteria."""
        operation_name = "scan"
        LOGGER.debug(
            f"[{operation_name}] Scanning records with category={category}, "
            f"offset={offset}, limit={limit}, order_by={order_by}, "
            f"descending={descending}"
        )
        if order_by and order_by not in self.ALLOWED_ORDER_BY_COLUMNS:
            LOGGER.error(f"[{operation_name}] Invalid order_by column: {order_by}")
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=(
                    f"Invalid order_by column: {order_by}. Allowed columns: "
                    f"{', '.join(self.ALLOWED_ORDER_BY_COLUMNS)}"
                ),
            )

        try:
            sql_clause = "1=1"
            params = []
            if tag_query:
                sql_clause, params = self.get_sql_clause(tag_query)

            order_column = order_by if order_by else "id"
            table_prefix = "t" if order_by in self.columns else "i"
            order_direction = "DESC" if descending else "ASC"
            LOGGER.debug(
                f"[{operation_name}] Using ORDER BY {table_prefix}.{order_column} "
                f"{order_direction}"
            )

            subquery = f"""
                SELECT i.id
                FROM items i
                JOIN {self.table} t ON i.id = t.item_id
                WHERE i.profile_id = ? AND i.category = ?
                AND (i.expiry IS NULL OR datetime(i.expiry) > CURRENT_TIMESTAMP)
                AND {sql_clause}
                ORDER BY {table_prefix}.{order_column} {order_direction}
            """
            if limit is not None or offset is not None:
                subquery += " LIMIT ?"
                params.append(
                    limit if limit is not None else -1
                )  #  just use -1 for no limit
                if offset is not None:
                    subquery += " OFFSET ?"
                    params.append(offset)

            query = f"""
                SELECT i.id AS i_id, i.name AS i_name, i.value AS i_value, t.*
                FROM ({subquery}) AS sub
                JOIN items i ON sub.id = i.id
                JOIN {self.table} t ON i.id = t.item_id
                ORDER BY {table_prefix}.{order_column} {order_direction}
            """
            cursor.execute(query, [profile_id, category] + params)

            cursor.execute(query, [profile_id, category] + params)

            columns = [desc[0] for desc in cursor.description]
            for row in cursor:
                row_dict = dict(zip(columns, row))
                name = row_dict["i_name"]
                value = row_dict["i_value"]
                tags = {
                    k: v
                    for k, v in row_dict.items()
                    if k not in ["i_id", "i_name", "i_value", "item_id", "item_name"]
                }
                tags = deserialize_tags(tags)
                yield Entry(category=category, name=name, value=value, tags=tags)
        except Exception as e:
            LOGGER.error(f"[{operation_name}] Failed: {str(e)}")
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
        """Scan the database using keyset pagination based on the last seen item ID."""
        operation_name = "scan_keyset"
        LOGGER.debug(
            f"[{operation_name}] Starting with profile_id={profile_id}, "
            f"category={category}, tag_query={tag_query}, last_id={last_id}, "
            f"limit={limit}, order_by={order_by}, descending={descending}, "
            f"table={self.table}"
        )

        try:
            if order_by and order_by not in self.ALLOWED_ORDER_BY_COLUMNS:
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=(
                        f"Invalid order_by column: {order_by}. Allowed columns: "
                        f"{', '.join(self.ALLOWED_ORDER_BY_COLUMNS)}"
                    ),
                )

            sql_clause = "1=1"
            params = []
            if tag_query:
                sql_clause, params = self.get_sql_clause(tag_query)

            order_column = order_by if order_by else "id"
            table_prefix = "t" if order_by in self.columns else "i"
            order_direction = "DESC" if descending else "ASC"
            keyset_clause = (
                f"AND {table_prefix}.{order_column} > ?" if last_id is not None else ""
            )
            if last_id is not None:
                params.append(last_id)

            subquery = f"""
                SELECT i.id
                FROM items i
                JOIN {self.table} t ON i.id = t.item_id
                WHERE i.profile_id = ? AND i.category = ?
                AND (i.expiry IS NULL OR datetime(i.expiry) > CURRENT_TIMESTAMP)
                AND {sql_clause}
                {keyset_clause}
                ORDER BY {table_prefix}.{order_column} {order_direction}
                LIMIT ?
            """
            subquery_params = [profile_id, category] + params + [limit]

            query = f"""
                SELECT i.id AS i_id, i.category, i.name AS i_name, i.value AS i_value, t.*
                FROM ({subquery}) AS sub
                JOIN items i ON sub.id = i.id
                JOIN {self.table} t ON i.id = t.item_id
                ORDER BY {table_prefix}.{order_column} {order_direction}
            """
            cursor.execute(query, subquery_params)

            columns = [desc[0] for desc in cursor.description]
            for row in cursor:
                row_dict = dict(zip(columns, row))
                name = row_dict["i_name"]
                value = row_dict["i_value"]
                tags = {
                    k: v
                    for k, v in row_dict.items()
                    if k not in ["i_id", "i_name", "i_value", "item_id", "item_name"]
                }
                tags = deserialize_tags(tags)
                yield Entry(category=category, name=name, value=value, tags=tags)
        except Exception as e:
            LOGGER.error(f"[{operation_name}] Failed: {str(e)}")
            raise

    def get_sql_clause(self, tag_query: TagQuery) -> Tuple[str, List[Any]]:
        """Translate a TagQuery into an SQL clause for the normalized table."""
        LOGGER.debug(f"[get_sql_clause] Generating SQL clause for tag_query={tag_query}")
        sql_clause = self.encoder.encode_query(tag_query)
        arguments = self.encoder.arguments
        LOGGER.debug(
            f"[get_sql_clause] Generated SQL clause: {sql_clause} with "
            f"arguments: {arguments}"
        )
        return sql_clause, arguments
