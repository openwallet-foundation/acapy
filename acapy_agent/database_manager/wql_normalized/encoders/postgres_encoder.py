"""Module docstring."""

import logging
from typing import List, Tuple, cast

from ..tags import CompareOp, ConjunctionOp, TagName, TagQuery, TagQueryEncoder

LOGGER = logging.getLogger(__name__)


class PostgresTagEncoder(TagQueryEncoder):
    """PostgreSQL tag query encoder."""

    """Encoder for generating PostgreSQL-compatible SQL queries from TagQuery objects.

    Uses '%s' placeholders for parameters, compatible with psycopg 3.2.9.
    Supports both normalized and non-normalized modes with a configurable tags 
    table for non-normalized mode.
    """

    def __init__(
        self,
        enc_name,
        enc_value,
        normalized: bool = False,
        table_alias: str = "t",
        tags_table: str = "items_tags",
    ):
        """Initialize the encoder with functions to encode tag names and values.

        A mode flag, an optional table alias, and an optional tags table name for
        non-normalized mode.

        Args:
            enc_name (callable): Function to encode tag names (str -> str).
            enc_value (callable): Function to encode tag values (str -> str).
            normalized (bool): Flag to indicate if the encoder should use
                normalized mode (default: False).
            table_alias (str): Table alias to use in normalized mode (default: 't').
            tags_table (str): Name of the tags table for non-normalized mode
                (default: 'items_tags').

        """
        self.enc_name = enc_name
        self.enc_value = enc_value
        self.normalized = normalized
        self.table_alias = table_alias if normalized else None
        self.tags_table = tags_table
        self.arguments = []  # List to store parameter values

    def encode_name(self, name: TagName) -> str:
        """Encode the tag name using the provided enc_name function."""
        result = self.enc_name(name.value)
        encoded_name = result if isinstance(result, str) else str(result)
        return encoded_name

    def encode_value(self, value: str) -> str:
        """Encode the tag value using the provided enc_value function."""
        result = self.enc_value(value)
        encoded_value = result if isinstance(result, str) else str(result)
        return encoded_value

    def encode_query(
        self, query: TagQuery, negate: bool = False, top_level: bool = True
    ) -> Tuple[str, List[str]] | str:
        """Encode the query and reset arguments list only at top level.

        Args:
            query (TagQuery): The query to encode.
            negate (bool): Whether to negate the query.
            top_level (bool): Whether this is a top-level query.

        Returns:
            Tuple[str, List[str]] | str: SQL clause and list of parameters for
                top-level queries, or SQL clause string for subqueries.

        """
        if top_level:
            self.arguments = []  # Reset arguments only for top-level query

        try:
            if query.variant == "Not":
                sql_clause = self._encode_not(query)
            else:
                compare_map = {
                    "Eq": CompareOp.Eq,
                    "Neq": CompareOp.Neq,
                    "Gt": CompareOp.Gt,
                    "Gte": CompareOp.Gte,
                    "Lt": CompareOp.Lt,
                    "Lte": CompareOp.Lte,
                    "Like": CompareOp.Like,
                }
                if query.variant in compare_map:
                    sql_clause = self.encode_op(
                        compare_map[query.variant], *query.data, negate
                    )
                elif query.variant == "In":
                    sql_clause = self.encode_in(*query.data, negate)
                elif query.variant == "Exist":
                    sql_clause = self.encode_exist(query.data, negate)
                elif query.variant in ["And", "Or"]:
                    op = ConjunctionOp.And if query.variant == "And" else ConjunctionOp.Or
                    sql_clause = self.encode_conj(op, query.data, negate)
                else:
                    LOGGER.error(
                        "[%s] Unknown query variant: %s",
                        "encode_operation",
                        query.variant,
                    )
                    raise ValueError(f"Unknown query variant: {query.variant}")

            if top_level:
                return sql_clause, self.arguments
            return sql_clause
        except Exception as e:
            LOGGER.error("[%s] Failed: %s", "encode_operation", str(e))
            raise

    def _encode_not(self, query: TagQuery) -> str:
        """Encode a NOT expression with special-cases for certain variants."""
        inner = query.data
        if inner.variant == "Exist":
            names = cast(List[TagName], inner.data)
            sql_clause = self.encode_exist(names, negate=True)
        elif inner.variant == "In":
            name, values = cast(Tuple[TagName, List[str]], inner.data)
            sql_clause = self.encode_in(name, values, negate=True)
        elif not self.normalized and inner.variant in [
            "Eq",
            "Neq",
            "Gt",
            "Gte",
            "Lt",
            "Lte",
            "Like",
        ]:
            name, value = cast(Tuple[TagName, str], inner.data)
            sql_clause = self.encode_op(
                getattr(CompareOp, inner.variant), name, value, negate=True
            )
        else:
            subquery = self.encode_query(inner, False, top_level=False)
            if inner.variant not in ["And", "Or"]:
                sql_clause = f"NOT ({subquery})"
            else:
                sql_clause = f"NOT {subquery}"
        return sql_clause

    def encode_op_clause(
        self, op: CompareOp, enc_name: str, enc_value: str, negate: bool
    ) -> str:
        """Encode a comparison operation clause for PostgreSQL.

        In normalized mode, generates direct column comparisons (e.g., "t.column = %s").
        In non-normalized mode, generates subqueries using the configured tags
        table (e.g., "i.id IN (SELECT item_id FROM tags_table ...)").
        Uses %s placeholders for psycopg 3.2.9 compatibility.
        """
        if self.normalized:
            column = f"{self.table_alias}.{enc_name}" if self.table_alias else enc_name
            sql_op = op.as_sql_str()
            if negate:
                negate_map = {
                    "=": "!=",
                    "!=": "=",
                    ">": "<=",
                    ">=": "<",
                    "<": ">=",
                    "<=": ">",
                    "LIKE": "NOT LIKE",
                }
                sql_op = negate_map.get(sql_op, sql_op)
            self.arguments.append(enc_value)
            sql_clause = f"{column} {sql_op} %s"
            return sql_clause
        else:
            self.arguments.append(enc_name)
            self.arguments.append(enc_value)
            subquery_op = "NOT IN" if negate else "IN"
            sql_clause = (
                f"i.id {subquery_op} (SELECT item_id FROM {self.tags_table} "
                f"WHERE name = %s AND value {op.as_sql_str()} %s)"
            )
            return sql_clause

    def encode_in_clause(self, enc_name: str, enc_values: List[str], negate: bool) -> str:
        """Encode an 'IN' clause for multiple values in PostgreSQL.

        Uses %s placeholders for psycopg 3.2.9 compatibility.
        """
        if not enc_values:  # Handle empty value list
            sql_clause = "FALSE" if not negate else "TRUE"
            return sql_clause

        if self.normalized:
            column = f"{self.table_alias}.{enc_name}" if self.table_alias else enc_name
            self.arguments.extend(enc_values)
            placeholders = ", ".join(["%s" for _ in enc_values])
            sql_clause = f"{column} {'NOT IN' if negate else 'IN'} ({placeholders})"
            return sql_clause
        else:
            self.arguments.append(enc_name)
            self.arguments.extend(enc_values)
            value_placeholders = ", ".join(["%s" for _ in enc_values])
            sql_clause = (
                f"i.id IN (SELECT item_id FROM {self.tags_table} "
                f"WHERE name = %s AND value {'NOT IN' if negate else 'IN'} "
                f"({value_placeholders}))"
            )
            return sql_clause

    def encode_exist_clause(self, enc_name: str, negate: bool) -> str:
        """Encode an 'EXISTS' clause for tag or column existence in PostgreSQL.

        Uses %s placeholders for psycopg 3.2.9 compatibility.
        """
        if self.normalized:
            column = f"{self.table_alias}.{enc_name}" if self.table_alias else enc_name
            sql_clause = f"{column} {'IS NULL' if negate else 'IS NOT NULL'}"
            return sql_clause
        else:
            self.arguments.append(enc_name)
            subquery_op = "NOT IN" if negate else "IN"
            sql_clause = (
                f"i.id {subquery_op} (SELECT item_id FROM {self.tags_table} "
                f"WHERE name = %s)"
            )
            return sql_clause

    def encode_conj_clause(self, op: ConjunctionOp, clauses: List[str]) -> str:
        """Encode a conjunction clause (AND/OR) for PostgreSQL."""
        if not clauses:
            if op == ConjunctionOp.Or:
                return "FALSE"  # False for empty OR -- need to build a test for this
            return "TRUE"  # True for empty AND
        sql_clause = "(" + op.as_sql_str().join(clauses) + ")"
        return sql_clause

    def encode_op(self, op: CompareOp, name: TagName, value: str, negate: bool):
        """Encode a comparison operation."""
        enc_name = self.encode_name(name)
        enc_value = self.encode_value(value)
        return self.encode_op_clause(op, enc_name, enc_value, negate)

    def encode_in(self, name: TagName, values: List[str], negate: bool):
        """Encode an IN operation."""
        enc_name = self.encode_name(name)
        enc_values = [self.encode_value(v) for v in values]
        return self.encode_in_clause(enc_name, enc_values, negate)

    def encode_exist(self, names: List[TagName], negate: bool):
        """Encode an existence check."""
        if not names:
            return None
        elif len(names) == 1:
            enc_name = self.encode_name(names[0])
            return self.encode_exist_clause(enc_name, negate)
        else:
            clauses = [self.encode_exist([name], negate) for name in names]
            return self.encode_conj_clause(ConjunctionOp.And, [c for c in clauses if c])

    def encode_conj(self, op: ConjunctionOp, subqueries: List[TagQuery], negate: bool):
        """Encode a conjunction operation."""
        op = op.negate() if negate else op
        clauses = []
        for q in subqueries:
            clause = self.encode_query(q, negate, top_level=False)
            if clause is not None:
                clauses.append(
                    clause if isinstance(clause, str) else clause[0]
                )  # Extract string from tuple if needed
        return self.encode_conj_clause(op, clauses)
